"""
Views for RentEase — all function-based views.

Demonstrates:
- Rendering templates
- GET (search/filter) vs POST (create/update/delete) patterns
- login_required decorator
- Django messages framework
- POST-Redirect-GET pattern
- Ownership checks in views (not just template hiding)
- get_object_or_404 for clean 404 handling
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal
import time

from .models import Property, Booking, Review
from .forms import (
    RegisterForm, LoginForm,
    PropertyForm, BookingForm, ContactForm, ReviewForm
)
from .cashfree_service import (
    create_cashfree_order,
    verify_cashfree_order,
    get_cashfree_sdk_mode,
    get_cashfree_checkout_url,
    is_cashfree_configured,
)


# =========================================================================== #
#  PUBLIC PAGES
# =========================================================================== #

def home(request):
    """
    Homepage — shows hero, featured properties (last 6 added), and info sections.
    Also handles the hero search form (GET parameters forwarded to /properties/).
    """
    featured = Property.objects.filter(is_available=True).order_by('-created_at')[:6]
    context = {
        'featured_properties': featured,
        'page_title': 'RentEase — Find a place that feels like home',
    }
    return render(request, 'home.html', context)


def about(request):
    """About page — static information about the project."""
    return render(request, 'about.html', {'page_title': 'About RentEase'})


def contact(request):
    """
    Contact page with a form that saves to the database.
    Demonstrates POST-Redirect-GET and Django messages.
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your message has been received! We'll get back to you soon."
            )
            return redirect('contact')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ContactForm()

    return render(request, 'contact.html', {
        'form': form,
        'page_title': 'Contact Us — RentEase',
    })


# =========================================================================== #
#  PROPERTY LISTING & DETAIL
# =========================================================================== #

def property_list(request):
    """
    Shows all available properties with optional filters.
    Filters are applied via GET parameters to keep URLs bookmarkable.
    Supports filtering by location, max daily rent, type, bedrooms, and stay dates.
    """
    properties = Property.objects.filter(is_available=True)

    # --- Filters ---
    location = request.GET.get('location', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    property_type = request.GET.get('property_type', '').strip()
    min_bedrooms = request.GET.get('min_bedrooms', '').strip()
    check_in = request.GET.get('check_in', '').strip()
    check_out = request.GET.get('check_out', '').strip()

    if location:
        properties = properties.filter(location__icontains=location)

    if max_rent:
        try:
            properties = properties.filter(rent__lte=float(max_rent))
        except ValueError:
            pass  # Ignore invalid numeric input

    if property_type:
        properties = properties.filter(property_type=property_type)

    if min_bedrooms:
        try:
            properties = properties.filter(bedrooms__gte=int(min_bedrooms))
        except ValueError:
            pass

    # Date range availability filter
    if check_in and check_out:
        try:
            cin_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            cout_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            if cout_date > cin_date:
                available_ids = [p.id for p in properties if p.is_available_for_dates(cin_date, cout_date)]
                properties = properties.filter(id__in=available_ids)
        except (ValueError, TypeError):
            pass

    total_count = properties.count()

    # Pagination — 9 properties per page
    paginator = Paginator(properties, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    property_type_choices = Property.PROPERTY_TYPE_CHOICES

    context = {
        'page_obj': page_obj,
        'total_count': total_count,
        'location': location,
        'max_rent': max_rent,
        'property_type': property_type,
        'min_bedrooms': min_bedrooms,
        'check_in': check_in,
        'check_out': check_out,
        'property_type_choices': property_type_choices,
        'page_title': 'Explore Properties — RentEase',
        'has_filters': any([location, max_rent, property_type, min_bedrooms, check_in, check_out]),
    }
    return render(request, 'properties/property_list.html', context)


def property_detail(request, pk):
    """
    Shows full details of a single property, reviews, and daily booking form.
    Anonymous users see a 'Login to Book' prompt instead of the form.
    Verified tenants who have booked the property can rate and review.
    """
    property_obj = get_object_or_404(Property, pk=pk)

    # Determine if the current user has an existing pending/approved booking
    existing_booking = None
    has_booked = False
    can_review = False
    user_review = None
    review_form = None

    if request.user.is_authenticated:
        existing_booking = Booking.objects.filter(
            property=property_obj,
            tenant=request.user,
            status__in=['pending', 'approved']
        ).first()

        # Check if user has booked this property (any booking recorded)
        has_booked = Booking.objects.filter(
            property=property_obj,
            tenant=request.user
        ).exists()

        if has_booked and request.user != property_obj.owner:
            can_review = True
            user_review = Review.objects.filter(
                property=property_obj,
                tenant=request.user
            ).first()
            review_form = ReviewForm(instance=user_review)

    form = None
    default_check_in = timezone.now().date() + timedelta(days=1)
    default_check_out = timezone.now().date() + timedelta(days=3)

    # Show booking form only to authenticated non-owners when property is available
    if request.user.is_authenticated and request.user != property_obj.owner and property_obj.is_currently_available:
        form = BookingForm(
            property_obj=property_obj,
            initial={
                'tenant_full_name': request.user.get_full_name() or request.user.username,
                'start_date': default_check_in,
                'end_date': default_check_out,
                'guests': 1,
            }
        )

    reviews = property_obj.reviews.select_related('tenant').all()

    context = {
        'property': property_obj,
        'amenities': property_obj.get_amenities_list(),
        'form': form,
        'default_check_in': default_check_in.strftime('%Y-%m-%d'),
        'default_check_out': default_check_out.strftime('%Y-%m-%d'),
        'existing_booking': existing_booking,
        'has_booked': has_booked,
        'can_review': can_review,
        'user_review': user_review,
        'review_form': review_form,
        'reviews': reviews,
        'total_reviews': reviews.count(),
        'average_rating': property_obj.average_rating(),
        'page_title': f"{property_obj.title} — RentEase",
    }
    return render(request, 'properties/property_detail.html', context)


@login_required
def add_review(request, pk):
    """
    Allows a tenant who has booked the property to submit or update a rating & review.
    Enforces security:
    - User must be authenticated.
    - Owner cannot review own property.
    - User must have a booking record for this property.
    """
    property_obj = get_object_or_404(Property, pk=pk)

    if request.user == property_obj.owner:
        messages.error(request, "Property owners cannot rate their own listings.")
        return redirect('property_detail', pk=pk)

    has_booked = Booking.objects.filter(property=property_obj, tenant=request.user).exists()
    if not has_booked:
        messages.error(request, "Only tenants who have booked this property can submit a rating.")
        return redirect('property_detail', pk=pk)

    existing_review = Review.objects.filter(property=property_obj, tenant=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.property = property_obj
            review.tenant = request.user
            review.save()
            if existing_review:
                messages.success(request, "Your rating and review have been updated!")
            else:
                messages.success(request, "Thank you! Your rating and review have been published.")
        else:
            messages.error(request, "Please select a valid rating between 1 and 5 stars.")

    return redirect(f"{reverse('property_detail', kwargs={'pk': pk})}#reviews")



# =========================================================================== #
#  AUTHENTICATION
# =========================================================================== #

def register_view(request):
    """
    User registration using the extended RegisterForm.
    After successful registration the user is automatically logged in.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to RentEase, {user.first_name or user.username}! "
                "Your account has been created."
            )
            return redirect('home')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'page_title': 'Create Account — RentEase',
    })


def login_view(request):
    """
    Custom login view using Django's authenticate() and login().
    """
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next', '/')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                # Safe redirect — only use next if it is a relative path
                next_page = request.POST.get('next', next_url)
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': next_url,
        'page_title': 'Sign In — RentEase',
    })


def logout_view(request):
    """
    Logout requires POST (with CSRF token) to prevent CSRF-based logouts.
    """
    if request.method == 'POST':
        logout(request)
        messages.info(request, "You have been signed out. See you soon!")
        return redirect('home')
    # If accessed by GET, redirect home (don't log out silently)
    return redirect('home')


# =========================================================================== #
#  BOOKING
# =========================================================================== #

@login_required
def book_property(request, pk):
    """
    Submit a daily booking request for a property.
    Validates: not own property, property available, dates availability.
    Collects tenant contact, check-in, check-out dates, guest count,
    and displays dynamic UPI QR code with live calculated amount.
    """
    property_obj = get_object_or_404(Property, pk=pk)

    # Owners cannot book their own property
    if request.user == property_obj.owner:
        messages.error(request, "You cannot book your own property.")
        return redirect('property_detail', pk=pk)

    # Property must be available and not currently booked
    if not property_obj.is_currently_available:
        messages.error(request, "This property is currently booked and unavailable for new reservations.")
        return redirect('property_detail', pk=pk)

    # Build UPI QR string for the owner
    owner_name = property_obj.owner.get_full_name() or property_obj.owner.username
    owner_upi = property_obj.owner.email or f"{property_obj.owner.username}@upi"
    daily_rate = float(property_obj.rent)

    cin = None
    cout = None

    if request.method == 'POST':
        form = BookingForm(request.POST, property_obj=property_obj)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.property = property_obj
            booking.tenant = request.user
            booking.status = 'pending'
            booking.payment_status = 'PENDING'
            if not booking.tenant_full_name:
                booking.tenant_full_name = request.user.get_full_name() or request.user.username
            booking.save()

            # Create Cashfree Payment Order
            return_url = request.build_absolute_uri(reverse('payment_callback')) + "?order_id={order_id}"
            cf_result = create_cashfree_order(booking, return_url)

            if cf_result.get('success'):
                booking.order_id = cf_result.get('order_id')
                booking.cf_order_id = cf_result.get('cf_order_id')
                booking.payment_session_id = cf_result.get('payment_session_id')
                booking.save()

                # Seamless direct redirect to Cashfree checkout without intermediate page
                if not cf_result.get('is_mock'):
                    checkout_url = get_cashfree_checkout_url()
                    return render(request, 'bookings/cashfree_direct_redirect.html', {
                        'checkout_url': checkout_url,
                        'payment_session_id': booking.payment_session_id,
                    })
                return redirect('cashfree_checkout', booking_id=booking.pk)
            else:
                messages.error(
                    request,
                    f"Unable to initialize Cashfree payment gateway: {cf_result.get('error', 'Unknown error')}."
                )
                return redirect('book_property', pk=pk)
        else:
            messages.error(request, "Please correct the form errors.")
            raw_s = request.POST.get('start_date')
            raw_e = request.POST.get('end_date')
            if raw_s:
                try: cin = datetime.strptime(raw_s, '%Y-%m-%d').date()
                except (ValueError, TypeError): pass
            if raw_e:
                try: cout = datetime.strptime(raw_e, '%Y-%m-%d').date()
                except (ValueError, TypeError): pass
    else:
        req_start = request.GET.get('start_date')
        req_end = request.GET.get('end_date')
        req_guests = request.GET.get('guests', '1')

        if req_start and req_end:
            try:
                cin = datetime.strptime(req_start, '%Y-%m-%d').date()
                cout = datetime.strptime(req_end, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                cin = None
                cout = None

        if not cin or not cout or cout <= cin:
            cin = timezone.now().date() + timedelta(days=1)
            cout = timezone.now().date() + timedelta(days=3)

        try:
            guests_val = max(1, int(req_guests))
        except (ValueError, TypeError):
            guests_val = 1

        initial = {
            'tenant_full_name': request.user.get_full_name() or request.user.username,
            'start_date': cin,
            'end_date': cout,
            'guests': guests_val,
        }
        form = BookingForm(property_obj=property_obj, initial=initial)

    if cin and cout and cout > cin:
        initial_days = (cout - cin).days
    else:
        initial_days = 2
    initial_amount = round(daily_rate * initial_days, 2)

    return render(request, 'bookings/book_property.html', {
        'form': form,
        'property': property_obj,
        'owner_upi': owner_upi,
        'owner_name': owner_name,
        'daily_rate': daily_rate,
        'initial_days': initial_days,
        'initial_amount': initial_amount,
        'page_title': f"Book {property_obj.title} — RentEase",
    })


@login_required
def cashfree_checkout(request, booking_id):
    """
    Renders the Cashfree Sandbox checkout page with Cashfree JS SDK v3.
    Loads the payment session and redirects/opens Cashfree sandbox checkout.
    """
    booking = get_object_or_404(Booking, pk=booking_id, tenant=request.user)

    if booking.payment_status == 'PAID':
        messages.info(request, "This booking has already been paid and confirmed.")
        return redirect('my_bookings')

    # Ensure an order and session exist
    if not booking.payment_session_id or not booking.order_id:
        return_url = request.build_absolute_uri(reverse('payment_callback')) + "?order_id={order_id}"
        cf_result = create_cashfree_order(booking, return_url=return_url)
        if cf_result.get('success'):
            booking.order_id = cf_result.get('order_id')
            booking.cf_order_id = cf_result.get('cf_order_id')
            booking.payment_session_id = cf_result.get('payment_session_id')
            booking.save()
        else:
            messages.error(request, f"Could not create Cashfree payment session: {cf_result.get('error')}")
            return redirect('my_bookings')

    # Seamless direct auto-post to Cashfree without intermediate page
    if not booking.payment_session_id.startswith('session_mock_'):
        checkout_url = get_cashfree_checkout_url()
        return render(request, 'bookings/cashfree_direct_redirect.html', {
            'checkout_url': checkout_url,
            'payment_session_id': booking.payment_session_id,
        })

    callback_url = request.build_absolute_uri(reverse('payment_callback')) + f"?order_id={booking.order_id}"

    return render(request, 'bookings/cashfree_checkout.html', {
        'booking': booking,
        'property': booking.property,
        'payment_session_id': booking.payment_session_id,
        'order_id': booking.order_id,
        'cashfree_mode': get_cashfree_sdk_mode(),
        'callback_url': callback_url,
        'is_configured': is_cashfree_configured(),
        'page_title': f"Cashfree Checkout — {booking.property.title}",
    })


@login_required
def payment_callback(request):
    """
    Handles redirect return from Cashfree PG with ?order_id={order_id}.
    Verifies payment with Cashfree API and auto-confirms the booking (removes manual approval).
    """
    order_id = request.GET.get('order_id')
    if not order_id:
        messages.error(request, "Payment callback received without order reference.")
        return redirect('my_bookings')

    booking = Booking.objects.filter(order_id=order_id).select_related('property', 'tenant').first()
    if not booking:
        messages.error(request, f"Booking with Order ID '{order_id}' was not found.")
        return redirect('my_bookings')

    # Access control
    if booking.tenant != request.user and booking.property.owner != request.user:
        messages.error(request, "You are not authorized to view this booking.")
        return redirect('my_bookings')

    # If already marked as paid
    if booking.payment_status == 'PAID':
        messages.success(request, f"Payment already confirmed! Your stay at '{booking.property.title}' is confirmed.")
        return redirect('my_bookings')

    # Verify order with Cashfree
    verify_res = verify_cashfree_order(order_id)
    order_status = verify_res.get('order_status')

    if order_status == 'PAID':
        # Ensure dates are still available before final confirmation
        prop = booking.property
        if not prop.is_available_for_dates(booking.start_date, booking.end_date, exclude_booking_id=booking.pk):
            booking.payment_status = 'REFUNDED'
            booking.status = 'cancelled'
            booking.save()
            messages.warning(
                request,
                "These dates became unavailable while payment was processing. A full refund has been initiated."
            )
            return redirect('my_bookings')

        booking.payment_status = 'PAID'
        booking.status = 'approved'  # Instantly confirmed booking!
        booking.cf_payment_id = verify_res.get('cf_payment_id') or f"cf_{order_id}"
        booking.payment_method = verify_res.get('payment_method') or 'ONLINE'
        booking.paid_at = timezone.now()
        booking.save()

        messages.success(
            request,
            f"🎉 Payment of ₹{booking.payment_amount:,.0f} successful! "
            f"Your reservation for '{booking.property.title}' ({booking.start_date.strftime('%d %b %Y')} to {booking.end_date.strftime('%d %b %Y')}) is confirmed!"
        )
        return redirect('my_bookings')

    elif order_status in ['FAILED', 'CANCELLED', 'USER_DROPPED']:
        booking.payment_status = 'FAILED'
        booking.save()
        messages.error(
            request,
            f"Payment was not completed ({order_status.lower().replace('_', ' ')}). Your reservation was not confirmed."
        )
        return redirect('my_bookings')
    else:
        messages.info(
            request,
            f"Payment status is currently {order_status}. We will confirm your reservation once processed."
        )
        return redirect('my_bookings')


@login_required
def simulate_payment(request, booking_id):
    """
    Test helper for sandbox development:
    Simulates successful Cashfree payment without completing external payment UI.
    Auto-confirms the booking immediately.
    """
    booking = get_object_or_404(Booking, pk=booking_id, tenant=request.user)

    if booking.payment_status == 'PAID':
        messages.info(request, "This booking has already been paid and confirmed.")
        return redirect('my_bookings')

    booking.payment_status = 'PAID'
    booking.status = 'approved'
    booking.cf_payment_id = f"sim_pay_{int(time.time())}"
    booking.payment_method = 'UPI (Cashfree Sandbox)'
    booking.paid_at = timezone.now()
    booking.save()

    messages.success(
        request,
        f"🎉 Sandbox payment simulated successfully! Booking for '{booking.property.title}' is confirmed."
    )
    return redirect('my_bookings')


@login_required
def my_bookings(request):
    """
    Shows all booking requests made by the currently logged-in tenant.
    Tenants only see their own bookings.
    """
    bookings = Booking.objects.filter(tenant=request.user).select_related('property')
    return render(request, 'bookings/my_bookings.html', {
        'bookings': bookings,
        'page_title': 'My Bookings — RentEase',
    })


@login_required
def cancel_booking(request, pk):
    """
    Allow a tenant to cancel their own pending or approved booking.
    Handles refund tracking if the booking was already paid online.
    """
    booking = get_object_or_404(Booking, pk=pk, tenant=request.user)

    if request.method == 'POST':
        if booking.status in ['pending', 'approved'] and not booking.checked_out:
            booking.status = 'cancelled'
            if booking.payment_status == 'PAID':
                booking.payment_status = 'REFUNDED'
                booking.save()
                messages.success(
                    request,
                    f"Your booking for '{booking.property.title}' has been cancelled. "
                    f"A refund of ₹{booking.payment_amount:,.0f} has been processed via Cashfree."
                )
            else:
                booking.payment_status = 'CANCELLED'
                booking.save()
                messages.success(request, f"Your reservation for '{booking.property.title}' has been cancelled.")
        else:
            messages.error(request, "Only pending or active bookings can be cancelled.")
        return redirect('my_bookings')

    return redirect('my_bookings')


# =========================================================================== #
#  OWNER DASHBOARD
# =========================================================================== #

@login_required
def owner_dashboard(request):
    """
    Dashboard for property owners — shows owned properties, confirmed bookings, and earnings.
    Only shows data belonging to the logged-in user.
    """
    my_properties = Property.objects.filter(owner=request.user)

    # Calculate summary stats from actual database records
    total_properties = my_properties.count()
    total_bookings = Booking.objects.filter(property__owner=request.user).count()
    confirmed_bookings = Booking.objects.filter(
        property__owner=request.user,
        status='approved'
    ).count()
    total_revenue = Booking.objects.filter(
        property__owner=request.user,
        payment_status='PAID'
    ).aggregate(Sum('payment_amount'))['payment_amount__sum'] or Decimal('0.00')

    # Recent booking requests for owner's properties (all statuses)
    recent_bookings = Booking.objects.filter(
        property__owner=request.user
    ).select_related('property', 'tenant').order_by('-created_at')[:20]

    # Active (approved, not checked out) bookings for checkout management
    active_bookings = Booking.objects.filter(
        property__owner=request.user,
        status='approved',
        checked_out=False,
    ).select_related('property', 'tenant')
    active_count = active_bookings.count()

    context = {
        'my_properties': my_properties,
        'total_properties': total_properties,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'active_count': active_count,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'active_bookings': active_bookings,
        'page_title': 'Owner Dashboard — RentEase',
    }
    return render(request, 'dashboard/owner_dashboard.html', context)


@login_required
def add_property(request):
    """Add a new property listing. The owner is set from request.user."""
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.owner = request.user   # Set owner server-side — never trust form input
            prop.save()
            messages.success(request, f"'{prop.title}' has been listed successfully!")
            return redirect('owner_dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PropertyForm()

    return render(request, 'properties/property_form.html', {
        'form': form,
        'action': 'Add',
        'page_title': 'Add Property — RentEase',
    })


@login_required
def edit_property(request, pk):
    """Edit an existing property. Only the owner may edit."""
    prop = get_object_or_404(Property, pk=pk)

    # Authorization check — backend enforced, not just UI
    if prop.owner != request.user:
        messages.error(request, "You are not authorized to edit this property.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=prop)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{prop.title}' has been updated.")
            return redirect('owner_dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PropertyForm(instance=prop)

    return render(request, 'properties/property_form.html', {
        'form': form,
        'action': 'Edit',
        'property': prop,
        'page_title': f"Edit {prop.title} — RentEase",
    })


@login_required
def delete_property(request, pk):
    """Delete a property after confirmation. Only the owner may delete."""
    prop = get_object_or_404(Property, pk=pk)

    # Backend authorization
    if prop.owner != request.user:
        messages.error(request, "You are not authorized to delete this property.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        title = prop.title
        prop.delete()
        messages.success(request, f"'{title}' has been deleted.")
        return redirect('owner_dashboard')

    return render(request, 'properties/property_confirm_delete.html', {
        'property': prop,
        'page_title': f"Delete {prop.title} — RentEase",
    })


@login_required
def manage_booking(request, pk):
    """
    Manual accept/reject has been removed. Bookings are instantly confirmed
    upon online payment via Cashfree.
    """
    messages.info(
        request,
        "Manual approval is no longer required. Bookings are automatically confirmed upon online payment via Cashfree."
    )
    return redirect('owner_dashboard')


@login_required
def checkout_booking(request, pk):
    """
    Owner marks a tenant as checked out.
    - Sets booking.checked_out = True and records checkout_date.
    - Sets booking.status = 'completed' (professionally completes the stay).
    """
    booking = get_object_or_404(Booking, pk=pk)

    if booking.property.owner != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        if booking.status == 'approved' and not booking.checked_out:
            booking.checked_out = True
            booking.checkout_date = timezone.now().date()
            booking.status = 'completed'
            booking.save()

            messages.success(
                request,
                f"{booking.get_tenant_display_name()}'s stay is marked as completed."
            )
        else:
            messages.error(request, "Only active approved bookings can be checked out.")

    return redirect('owner_dashboard')
