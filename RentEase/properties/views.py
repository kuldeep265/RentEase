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
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import Property, Booking, Review
from .forms import (
    RegisterForm, LoginForm,
    PropertyForm, BookingForm, ContactForm, ReviewForm
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
    """
    properties = Property.objects.filter(is_available=True)

    # --- Filters ---
    location = request.GET.get('location', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    property_type = request.GET.get('property_type', '').strip()
    min_bedrooms = request.GET.get('min_bedrooms', '').strip()

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
        'property_type_choices': property_type_choices,
        'page_title': 'Explore Properties — RentEase',
        'has_filters': any([location, max_rent, property_type, min_bedrooms]),
    }
    return render(request, 'properties/property_list.html', context)


def property_detail(request, pk):
    """
    Shows full details of a single property, reviews, and booking form.
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
    # Show booking form only to authenticated non-owners
    if request.user.is_authenticated and request.user != property_obj.owner:
        form = BookingForm()

    reviews = property_obj.reviews.select_related('tenant').all()

    context = {
        'property': property_obj,
        'amenities': property_obj.get_amenities_list(),
        'form': form,
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
    Submit a booking request for a property.
    Validates: not own property, property available, no duplicate active booking.
    Collects tenant contact info, duration (months or days), payment amount,
    and renders a UPI QR code for payment before submission.
    """
    property_obj = get_object_or_404(Property, pk=pk)

    # Owners cannot book their own property
    if request.user == property_obj.owner:
        messages.error(request, "You cannot book your own property.")
        return redirect('property_detail', pk=pk)

    # Property must be available
    if not property_obj.is_available:
        messages.error(request, "This property is currently not available for booking.")
        return redirect('property_detail', pk=pk)

    # Prevent duplicate pending/approved bookings
    existing = Booking.objects.filter(
        property=property_obj,
        tenant=request.user,
        status__in=['pending', 'approved']
    ).exists()
    if existing:
        messages.warning(
            request,
            "You already have a pending or approved booking for this property."
        )
        return redirect('property_detail', pk=pk)

    # Build UPI QR string for the owner
    # Format: upi://pay?pa=<vpa>&pn=<name>&am=<amount>&cu=INR&tn=<note>
    # We use the owner's email as UPI VPA placeholder (owner can update it)
    owner_name = property_obj.owner.get_full_name() or property_obj.owner.username
    owner_upi  = property_obj.owner.email or f"{property_obj.owner.username}@upi"
    rent       = float(property_obj.rent)
    # Daily rate = monthly rent / 30
    daily_rate = round(rent / 30, 2)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.property = property_obj
            booking.tenant   = request.user
            booking.status   = 'pending'
            if not booking.tenant_full_name:
                booking.tenant_full_name = request.user.get_full_name() or request.user.username

            # Compute and enforce payment_amount server-side
            dtype = form.cleaned_data['duration_type']
            if dtype == 'months':
                months = form.cleaned_data.get('duration_months') or 1
                computed = round(rent * months, 2)
            else:
                days = form.cleaned_data.get('duration_days') or 1
                computed = round(daily_rate * days, 2)

            booking.payment_amount = max(computed, 1000)
            booking.save()

            messages.success(
                request,
                f"Booking request sent for '{property_obj.title}'! "
                "The owner will review it shortly."
            )
            return redirect('my_bookings')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        initial = {
            'tenant_full_name': request.user.get_full_name() or request.user.username,
            'duration_type': 'months',
        }
        form = BookingForm(initial=initial)

    return render(request, 'bookings/book_property.html', {
        'form': form,
        'property': property_obj,
        'owner_upi': owner_upi,
        'owner_name': owner_name,
        'monthly_rent': rent,
        'daily_rate': daily_rate,
        'page_title': f"Book {property_obj.title} — RentEase",
    })


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
    Allow a tenant to cancel their own PENDING booking.
    Uses POST for the state change.
    """
    booking = get_object_or_404(Booking, pk=pk, tenant=request.user)

    if request.method == 'POST':
        if booking.status == 'pending':
            booking.status = 'cancelled'
            booking.save()
            messages.success(request, "Your booking request has been cancelled.")
        elif booking.status == 'approved':
            # Tenant checks out early / cancels an approved booking — free up the room
            booking.status = 'cancelled'
            booking.save()
            prop = booking.property
            prop.available_rooms = min(prop.available_rooms + 1, prop.total_rooms)
            prop.save()
            messages.success(
                request,
                "Your booking has been cancelled and the room is now available again."
            )
        else:
            messages.error(request, "Only pending or approved bookings can be cancelled.")
        return redirect('my_bookings')

    return redirect('my_bookings')


# =========================================================================== #
#  OWNER DASHBOARD
# =========================================================================== #

@login_required
def owner_dashboard(request):
    """
    Dashboard for property owners — shows owned properties and booking stats.
    Only shows data belonging to the logged-in user.
    """
    my_properties = Property.objects.filter(owner=request.user)

    # Calculate summary stats from actual database records
    total_properties = my_properties.count()
    total_bookings = Booking.objects.filter(property__owner=request.user).count()
    pending_bookings = Booking.objects.filter(
        property__owner=request.user,
        status='pending'
    ).count()

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

    context = {
        'my_properties': my_properties,
        'total_properties': total_properties,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
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
    Allow an owner to approve or reject a booking for their property.
    - Approve: decrements available_rooms (auto-marks unavailable at 0).
    - Reject: no room change (room was never allocated).
    Tenants cannot change booking status through this view.
    """
    booking = get_object_or_404(Booking, pk=pk)

    # Only the owner of the property may act on this booking
    if booking.property.owner != request.user:
        messages.error(request, "You are not authorized to manage this booking.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        prop = booking.property

        if action == 'approve':
            if prop.available_rooms <= 0:
                messages.error(
                    request,
                    "Cannot approve — no rooms are currently available for this property."
                )
                return redirect('owner_dashboard')
            booking.status = 'approved'
            booking.save()
            # Decrement available rooms; Property.save() auto-sets is_available
            prop.available_rooms = max(prop.available_rooms - 1, 0)
            prop.save()
            messages.success(
                request,
                f"Booking by {booking.get_tenant_display_name()} approved. "
                f"{prop.available_rooms} room(s) remaining."
            )
        elif action == 'reject':
            booking.status = 'rejected'
            booking.save()
            messages.info(
                request,
                f"Booking by {booking.get_tenant_display_name()} rejected."
            )
        else:
            messages.error(request, "Invalid action.")

    return redirect('owner_dashboard')


@login_required
def checkout_booking(request, pk):
    """
    Owner marks a tenant as checked out.
    - Sets booking.checked_out = True and records checkout_date.
    - Increments available_rooms on the property (auto-marks available again if > 0).
    """
    booking = get_object_or_404(Booking, pk=pk)

    if booking.property.owner != request.user:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        if booking.status == 'approved' and not booking.checked_out:
            from django.utils.timezone import now
            booking.checked_out = True
            booking.checkout_date = now().date()
            booking.status = 'cancelled'   # Treat as vacated/completed
            booking.save()

            prop = booking.property
            prop.available_rooms = min(prop.available_rooms + 1, prop.total_rooms)
            prop.save()

            messages.success(
                request,
                f"{booking.get_tenant_display_name()} has been checked out. "
                f"Room is now available ({prop.available_rooms} of {prop.total_rooms} free)."
            )
        else:
            messages.error(request, "Only active approved bookings can be checked out.")

    return redirect('owner_dashboard')
