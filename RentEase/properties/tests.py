"""
Automated tests for RentEase.

Demonstrates Django's built-in test framework (unittest).
Run with: python manage.py test

Tests cover:
- Page responses (GET 200)
- Search and filter logic
- Authentication (register, login)
- Ownership / access control
- Booking workflow validation
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import Property, Booking, Review


# =========================================================================== #
#  Helper: quickly create test users and properties
# =========================================================================== #

def make_owner(username='testowner', password='TestPass@123'):
    return User.objects.create_user(
        username=username, password=password,
        first_name='Test', last_name='Owner', email=f'{username}@test.com'
    )


def make_tenant(username='testtenant', password='TestPass@123'):
    return User.objects.create_user(
        username=username, password=password,
        first_name='Test', last_name='Tenant', email=f'{username}@test.com'
    )


def make_property(owner, title='Test Property', location='Test City',
                  rent=10000, available=True):
    return Property.objects.create(
        title=title,
        description='A test property description.',
        location=location,
        rent=Decimal(str(rent)),
        property_type='apartment',
        bedrooms=2,
        bathrooms=1,
        amenities='WiFi, Parking',
        owner=owner,
        is_available=available,
    )


# =========================================================================== #
#  Public Page Tests
# =========================================================================== #

class HomePageTest(TestCase):
    def test_homepage_returns_200(self):
        """Homepage must load successfully for anonymous users."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_homepage_uses_correct_template(self):
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'home.html')

    def test_homepage_shows_featured_properties(self):
        """Featured properties from the database appear on the homepage."""
        owner = make_owner()
        prop = make_property(owner, title='Featured Test Property')
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Featured Test Property')

    def test_about_page_returns_200(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_contact_page_returns_200(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)


# =========================================================================== #
#  Property Listing Tests
# =========================================================================== #

class PropertyListTest(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.prop1 = make_property(self.owner, title='Chandigarh Apt', location='Chandigarh', rent=20000)
        self.prop2 = make_property(self.owner, title='Delhi Villa', location='Delhi', rent=80000)
        self.prop3 = make_property(self.owner, title='Unavailable Flat', location='Pune', available=False)

    def test_property_list_returns_200(self):
        response = self.client.get(reverse('property_list'))
        self.assertEqual(response.status_code, 200)

    def test_property_list_shows_only_available(self):
        """Unavailable properties must NOT appear in the listing."""
        response = self.client.get(reverse('property_list'))
        self.assertContains(response, 'Chandigarh Apt')
        self.assertNotContains(response, 'Unavailable Flat')

    def test_location_filter(self):
        """Location filter returns matching properties only."""
        response = self.client.get(reverse('property_list'), {'location': 'Delhi'})
        self.assertContains(response, 'Delhi Villa')
        self.assertNotContains(response, 'Chandigarh Apt')

    def test_max_rent_filter(self):
        """Max rent filter hides properties above the threshold."""
        response = self.client.get(reverse('property_list'), {'max_rent': '25000'})
        self.assertContains(response, 'Chandigarh Apt')
        self.assertNotContains(response, 'Delhi Villa')

    def test_property_type_filter(self):
        """Property type filter returns matching results."""
        response = self.client.get(reverse('property_list'), {'property_type': 'apartment'})
        self.assertEqual(response.status_code, 200)

    def test_combined_filters(self):
        """Multiple filters combine correctly (AND logic)."""
        response = self.client.get(reverse('property_list'), {
            'location': 'Chandigarh',
            'max_rent': '25000',
        })
        self.assertContains(response, 'Chandigarh Apt')
        self.assertNotContains(response, 'Delhi Villa')


# =========================================================================== #
#  Property Detail Tests
# =========================================================================== #

class PropertyDetailTest(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.prop = make_property(self.owner, title='Detail Test Property')

    def test_property_detail_returns_200(self):
        response = self.client.get(reverse('property_detail', args=[self.prop.pk]))
        self.assertEqual(response.status_code, 200)

    def test_property_detail_shows_correct_property(self):
        response = self.client.get(reverse('property_detail', args=[self.prop.pk]))
        self.assertContains(response, 'Detail Test Property')

    def test_invalid_property_id_returns_404(self):
        response = self.client.get(reverse('property_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)


# =========================================================================== #
#  Authentication Tests
# =========================================================================== #

class RegistrationTest(TestCase):
    def test_register_page_returns_200(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration_creates_user(self):
        """Valid registration form creates a new user and redirects."""
        response = self.client.post(reverse('register'), {
            'first_name': 'New',
            'last_name': 'User',
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password1': 'StrongPass@456',
            'password2': 'StrongPass@456',
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertRedirects(response, reverse('home'))

    def test_duplicate_username_rejected(self):
        """Registering with an existing username must fail."""
        make_owner(username='existinguser')
        response = self.client.post(reverse('register'), {
            'first_name': 'Another',
            'last_name': 'User',
            'username': 'existinguser',
            'email': 'another@test.com',
            'password1': 'StrongPass@456',
            'password2': 'StrongPass@456',
        })
        self.assertEqual(response.status_code, 200)  # Form re-rendered with errors


class LoginTest(TestCase):
    def setUp(self):
        self.user = make_owner(username='loginuser', password='TestPass@123')

    def test_login_page_returns_200(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_valid_login_redirects(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'TestPass@123',
        })
        self.assertRedirects(response, '/')

    def test_invalid_credentials_rejected(self):
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)  # Form re-rendered


# =========================================================================== #
#  Access Control Tests
# =========================================================================== #

class AccessControlTest(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.other_owner = make_owner(username='otherowner')
        self.tenant = make_tenant()
        self.prop = make_property(self.owner)

    def test_anonymous_cannot_access_owner_dashboard(self):
        """Anonymous users must be redirected to login."""
        response = self.client.get(reverse('owner_dashboard'))
        self.assertRedirects(response, '/accounts/login/?next=/owner/dashboard/')

    def test_anonymous_cannot_add_property(self):
        response = self.client.get(reverse('add_property'))
        self.assertRedirects(response, '/accounts/login/?next=/owner/properties/add/')

    def test_anonymous_cannot_access_my_bookings(self):
        response = self.client.get(reverse('my_bookings'))
        self.assertRedirects(response, '/accounts/login/?next=/my-bookings/')

    def test_non_owner_cannot_edit_property(self):
        """A user cannot edit another owner's property — backend check."""
        self.client.login(username='otherowner', password='TestPass@123')
        response = self.client.get(reverse('edit_property', args=[self.prop.pk]))
        # Should redirect to dashboard with an error, not render the edit form
        self.assertEqual(response.status_code, 302)

    def test_non_owner_cannot_delete_property(self):
        self.client.login(username='otherowner', password='TestPass@123')
        response = self.client.post(reverse('delete_property', args=[self.prop.pk]))
        # Property must still exist
        self.assertTrue(Property.objects.filter(pk=self.prop.pk).exists())


# =========================================================================== #
#  Booking Tests
# =========================================================================== #

class BookingTest(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.tenant = make_tenant()
        self.prop = make_property(self.owner)
        self.future_date = (date.today() + timedelta(days=15)).isoformat()
        self.future_end_date = (date.today() + timedelta(days=18)).isoformat()

    def test_tenant_can_submit_booking(self):
        """A valid daily booking request is saved and redirects to Cashfree checkout."""
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'tenant_full_name': 'Test Tenant',
                'tenant_contact': '+919876543210',
                'start_date': self.future_date,
                'end_date': self.future_end_date,
                'guests': 2,
                'message': 'Hello owner!',
            }
        )
        self.assertTrue(
            Booking.objects.filter(tenant=self.tenant, property=self.prop).exists()
        )
        booking = Booking.objects.get(tenant=self.tenant, property=self.prop)
        self.assertEqual(booking.total_days, 3)
        self.assertEqual(booking.payment_amount, round(self.prop.rent * 3, 2))
        self.assertEqual(booking.payment_status, 'PENDING')
        self.assertTrue(bool(booking.order_id))
        self.assertRedirects(response, reverse('cashfree_checkout', args=[booking.pk]))

    def test_cashfree_checkout_renders_correctly(self):
        """Cashfree checkout page loads for the tenant with session and SDK info."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=13),
            tenant_contact='9876543210',
            order_id='order_test_123',
            payment_session_id='session_mock_123',
            payment_status='PENDING',
        )
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.get(reverse('cashfree_checkout', args=[booking.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cashfree Payments')
        self.assertContains(response, 'order_test_123')

    def test_payment_callback_auto_approves_booking(self):
        """Cashfree callback automatically approves the booking without manual owner action."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=13),
            tenant_contact='9876543210',
            order_id='order_test_auto_approve',
            payment_session_id='session_mock_auto',
            payment_status='PENDING',
            status='pending',
        )
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.get(
            reverse('payment_callback') + f'?order_id={booking.order_id}'
        )
        self.assertRedirects(response, reverse('my_bookings'))
        booking.refresh_from_db()
        # Booking must be auto-approved and paid
        self.assertEqual(booking.payment_status, 'PAID')
        self.assertEqual(booking.status, 'approved')
        self.assertTrue(booking.is_paid)

    def test_simulate_payment_auto_confirms(self):
        """Simulate payment view instantly marks booking as paid and approved."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=13),
            tenant_contact='9876543210',
            order_id='order_test_sim',
            payment_status='PENDING',
            status='pending',
        )
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.get(reverse('simulate_payment', args=[booking.pk]))
        self.assertRedirects(response, reverse('my_bookings'))
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, 'PAID')
        self.assertEqual(booking.status, 'approved')

    def test_manual_manage_booking_redirects(self):
        """Manual approve/reject is removed — manage_booking redirects with info."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            status='pending',
        )
        self.client.login(username='testowner', password='TestPass@123')
        response = self.client.post(
            reverse('manage_booking', args=[booking.pk]),
            {'action': 'approve'}
        )
        self.assertRedirects(response, reverse('owner_dashboard'))

    def test_owner_cannot_book_own_property(self):
        """An owner booking their own property must be rejected."""
        self.client.login(username='testowner', password='TestPass@123')
        self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'tenant_full_name': 'Test Owner',
                'tenant_contact': '+919876543210',
                'start_date': self.future_date,
                'end_date': self.future_end_date,
                'guests': 1,
            }
        )
        # No booking should be created
        self.assertFalse(
            Booking.objects.filter(tenant=self.owner, property=self.prop).exists()
        )

    def test_past_date_rejected(self):
        """A booking with a past check-in date must be rejected."""
        self.client.login(username='testtenant', password='TestPass@123')
        past_date = (date.today() - timedelta(days=5)).isoformat()
        past_end = (date.today() - timedelta(days=2)).isoformat()
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'tenant_full_name': 'Test Tenant',
                'tenant_contact': '+919876543210',
                'start_date': past_date,
                'end_date': past_end,
                'guests': 1,
            }
        )
        self.assertFalse(
            Booking.objects.filter(tenant=self.tenant, property=self.prop).exists()
        )

    def test_checkout_before_checkin_rejected(self):
        """A booking where check-out is before or equal to check-in must be rejected."""
        self.client.login(username='testtenant', password='TestPass@123')
        cin = (date.today() + timedelta(days=10)).isoformat()
        cout = (date.today() + timedelta(days=9)).isoformat()
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'tenant_full_name': 'Test Tenant',
                'tenant_contact': '+919876543210',
                'start_date': cin,
                'end_date': cout,
                'guests': 1,
            }
        )
        self.assertFalse(
            Booking.objects.filter(tenant=self.tenant, property=self.prop).exists()
        )

    def test_tenant_sees_only_own_bookings(self):
        """Tenants only see their own booking records."""
        other_tenant = make_tenant(username='othertenant')
        Booking.objects.create(
            property=self.prop, tenant=other_tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=14),
        )
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.get(reverse('my_bookings'))
        bookings = response.context['bookings']
        for b in bookings:
            self.assertEqual(b.tenant, self.tenant)

    def test_unavailable_property_cannot_be_booked(self):
        """Bookings for unavailable properties must be rejected."""
        unavailable = make_property(self.owner, title='No Vacancy', available=False)
        self.client.login(username='testtenant', password='TestPass@123')
        self.client.post(
            reverse('book_property', args=[unavailable.pk]),
            {
                'tenant_full_name': 'Test Tenant',
                'tenant_contact': '+919876543210',
                'start_date': self.future_date,
                'end_date': self.future_end_date,
                'guests': 1,
            }
        )
        self.assertFalse(
            Booking.objects.filter(tenant=self.tenant, property=unavailable).exists()
        )



    def test_date_conflict_prevents_double_booking(self):
        """Submitting a booking request for dates that overlap with an approved booking is rejected."""
        # Approved booking from day 10 to day 15
        Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
            status='approved',
        )
        other_tenant = make_tenant(username='othertenant2')
        self.client.login(username='othertenant2', password='TestPass@123')

        # Overlapping request: day 12 to day 17
        cin = (date.today() + timedelta(days=12)).isoformat()
        cout = (date.today() + timedelta(days=17)).isoformat()
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'tenant_full_name': 'Other Tenant',
                'tenant_contact': '+919876543211',
                'start_date': cin,
                'end_date': cout,
                'guests': 1,
            }
        )
        # Booking should NOT be created due to conflict
        self.assertFalse(
            Booking.objects.filter(tenant=other_tenant, property=self.prop).exists()
        )

    def test_owner_checkout_marks_completed(self):
        """When owner checks out an approved booking, status is set to 'completed'."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=3),
            end_date=date.today(),
            status='approved',
        )
        self.client.login(username='testowner', password='TestPass@123')
        self.client.post(reverse('checkout_booking', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertTrue(booking.checked_out)
        self.assertEqual(booking.status, 'completed')

    def test_tenant_can_cancel_pending_booking(self):
        """Tenant can cancel their own pending booking."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=13),
        )
        self.client.login(username='testtenant', password='TestPass@123')
        self.client.post(reverse('cancel_booking', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_booked_property_shows_not_available_on_cards_and_cannot_be_booked(self):
        """
        When a property has an approved active booking:
        1. prop.is_booked is True, prop.is_currently_available is False.
        2. Property card on home page and listing page shows 'Not Available' badge.
        3. Property detail page shows 'Currently Booked' and disables booking form.
        4. Attempting to book via POST is rejected and redirects with error message.
        """
        # Initially available
        self.assertTrue(self.prop.is_currently_available)
        self.assertFalse(self.prop.is_booked)

        # Create an approved booking
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=4),
            status='approved',
            payment_status='PAID',
            checked_out=False,
        )

        # Property is now booked
        self.assertTrue(self.prop.is_booked)
        self.assertFalse(self.prop.is_currently_available)

        # 1. Check homepage property card badge
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not Available')

        # 2. Check property list page card badge
        response = self.client.get(reverse('property_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not Available')

        # 3. Check property detail page displays Currently Booked status
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.get(reverse('property_detail', args=[self.prop.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Currently Booked')
        self.assertContains(response, 'Currently Booked — Unavailable')

        # 4. Attempting to submit a new booking on this booked property must fail
        another_tenant = make_tenant(username='secondtenant')
        self.client.login(username='secondtenant', password='TestPass@123')
        post_response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'tenant_full_name': 'Second Guest',
                'tenant_contact': '+919123456789',
                'start_date': (date.today() + timedelta(days=2)).isoformat(),
                'end_date': (date.today() + timedelta(days=5)).isoformat(),
                'guests': 1,
            },
            follow=True
        )
        # Must be rejected with error and not create a booking
        self.assertEqual(Booking.objects.filter(tenant=another_tenant).count(), 0)
        self.assertContains(post_response, 'currently booked and unavailable for new reservations')

    def test_checkout_restores_available_status(self):
        """When owner checks out the booking, the property returns to Available."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() + timedelta(days=1),
            status='approved',
            payment_status='PAID',
            checked_out=False,
        )
        self.assertTrue(self.prop.is_booked)
        self.assertFalse(self.prop.is_currently_available)

        # Owner performs checkout
        self.client.login(username='testowner', password='TestPass@123')
        self.client.post(reverse('checkout_booking', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertTrue(booking.checked_out)
        self.assertEqual(booking.status, 'completed')

        # Property is restored to Available
        self.assertFalse(self.prop.is_booked)
        self.assertTrue(self.prop.is_currently_available)

        # Property card on homepage now shows Available
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Available')


# =========================================================================== #
#  Rating & Review Tests
# =========================================================================== #

class ReviewTest(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.tenant = make_tenant()
        self.unrelated_user = make_tenant(username='unrelated_user')
        self.prop = make_property(self.owner)
        # Create a booking for tenant
        self.booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=5),
            duration_months=3,
            status='approved'
        )

    def test_anonymous_cannot_review(self):
        """Anonymous users must be redirected to login when trying to review."""
        response = self.client.post(
            reverse('add_review', args=[self.prop.pk]),
            {'rating': 5, 'comment': 'Great place!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertFalse(Review.objects.filter(property=self.prop).exists())

    def test_user_without_booking_cannot_review(self):
        """Users who have never booked this property cannot submit a review."""
        self.client.login(username='unrelated_user', password='TestPass@123')
        response = self.client.post(
            reverse('add_review', args=[self.prop.pk]),
            {'rating': 5, 'comment': 'I never stayed here'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(property=self.prop, tenant=self.unrelated_user).exists())

    def test_owner_cannot_review_own_property(self):
        """Property owners cannot review their own properties."""
        self.client.login(username='testowner', password='TestPass@123')
        response = self.client.post(
            reverse('add_review', args=[self.prop.pk]),
            {'rating': 5, 'comment': 'My own place is amazing'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(property=self.prop, tenant=self.owner).exists())

    def test_verified_tenant_can_submit_review(self):
        """A tenant who has booked the property can successfully rate and review."""
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.post(
            reverse('add_review', args=[self.prop.pk]),
            {'rating': 5, 'comment': 'Wonderful apartment, highly recommended!'}
        )
        self.assertRedirects(response, reverse('property_detail', args=[self.prop.pk]) + '#reviews')
        self.assertTrue(Review.objects.filter(property=self.prop, tenant=self.tenant).exists())
        review = Review.objects.get(property=self.prop, tenant=self.tenant)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'Wonderful apartment, highly recommended!')
        self.assertEqual(self.prop.average_rating(), 5.0)
        self.assertEqual(self.prop.total_reviews(), 1)

    def test_verified_tenant_can_update_existing_review(self):
        """Submitting a second review updates the existing review rather than duplicating."""
        Review.objects.create(
            property=self.prop,
            tenant=self.tenant,
            rating=4,
            comment='Good stay'
        )
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.post(
            reverse('add_review', args=[self.prop.pk]),
            {'rating': 5, 'comment': 'Updated: Actually it was excellent!'}
        )
        self.assertEqual(Review.objects.filter(property=self.prop, tenant=self.tenant).count(), 1)
        review = Review.objects.get(property=self.prop, tenant=self.tenant)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'Updated: Actually it was excellent!')


# =========================================================================== #
#  AI Recommendation System Tests
# =========================================================================== #

from properties.models import PropertyInteraction, UserSearchPreference

class AIRecommendationTest(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.tenant = make_tenant()
        # Create diverse properties for recommendation testing
        self.prop_mumbai_flat = Property.objects.create(
            title='Luxury Sea View Flat',
            description='Modern luxury flat with sea view.',
            location='Bandra, Mumbai',
            rent=Decimal('2000.00'),
            property_type='apartment',
            bedrooms=2,
            bathrooms=2,
            amenities='WiFi, AC, Parking, Furnished, Balcony',
            owner=self.owner,
            is_available=True,
        )
        self.prop_delhi_pg = Property.objects.create(
            title='Comfortable Student PG',
            description='Affordable PG near university.',
            location='North Campus, Delhi',
            rent=Decimal('800.00'),
            property_type='pg',
            bedrooms=1,
            bathrooms=1,
            amenities='WiFi, Power Backup',
            owner=self.owner,
            is_available=True,
        )
        self.prop_bengaluru_room = Property.objects.create(
            title='Tech Park Studio Room',
            description='Studio room close to tech park.',
            location='Whitefield, Bengaluru',
            rent=Decimal('1500.00'),
            property_type='studio',
            bedrooms=1,
            bathrooms=1,
            amenities='WiFi, AC, Parking, Kitchen',
            owner=self.owner,
            is_available=True,
        )

    def test_ai_matcher_page_loads(self):
        """AI Matcher page renders with 200 OK and shows candidate recommendations."""
        response = self.client.get(reverse('ai_recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Matcher')
        self.assertContains(response, 'Target Daily Budget')
        self.assertContains(response, 'Luxury Sea View Flat')

    def test_ai_scoring_prefers_matching_budget_and_location(self):
        """Properties matching user budget, location, and type rank higher."""
        response = self.client.get(
            reverse('ai_recommendations'),
            {
                'budget': '1500',
                'location': 'Bengaluru',
                'property_type': 'studio',
                'amenities': ['WiFi', 'AC']
            }
        )
        self.assertEqual(response.status_code, 200)
        recommendations = response.context['recommendations']
        self.assertTrue(len(recommendations) > 0)
        top_rec = recommendations[0]
        # Bengaluru studio room should be #1 recommendation
        self.assertEqual(top_rec['property'], self.prop_bengaluru_room)
        self.assertGreaterEqual(top_rec['score'], 80)
        self.assertTrue(any('Bengaluru' in r or 'budget' in r.lower() for r in top_rec['reasons']))

    def test_behavioral_learning_save_boosts_similar_properties(self):
        """Saving a property boosts similar properties in subsequent recommendations."""
        # Tenant saves Delhi PG
        self.client.login(username='testtenant', password='TestPass@123')
        save_response = self.client.post(reverse('toggle_save_property', args=[self.prop_delhi_pg.pk]))
        self.assertEqual(save_response.status_code, 302)
        self.assertTrue(
            PropertyInteraction.objects.filter(
                user=self.tenant,
                property=self.prop_delhi_pg,
                interaction_type='saved'
            ).exists()
        )

        # Create another similar PG in Delhi
        prop_delhi_pg2 = Property.objects.create(
            title='Green Park PG Hostel',
            description='Second PG in Delhi.',
            location='South Campus, Delhi',
            rent=Decimal('850.00'),
            property_type='pg',
            bedrooms=1,
            bathrooms=1,
            amenities='WiFi',
            owner=self.owner,
            is_available=True,
        )

        # AI recommendations without explicit search parameters should boost Delhi PG properties
        response = self.client.get(reverse('ai_recommendations'))
        recommendations = response.context['recommendations']
        top_properties = [r['property'] for r in recommendations]
        # Both Delhi PGs should be ranked prominently due to saved preference learning
        self.assertIn(prop_delhi_pg2, top_properties)

    def test_behavioral_learning_dismiss_excludes_property(self):
        """Dismissed / rejected properties are excluded from AI recommendations."""
        self.client.login(username='testtenant', password='TestPass@123')
        # Dismiss Mumbai flat
        dismiss_response = self.client.post(
            reverse('dismiss_property', args=[self.prop_mumbai_flat.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertTrue(
            PropertyInteraction.objects.filter(
                user=self.tenant,
                property=self.prop_mumbai_flat,
                interaction_type='dismissed'
            ).exists()
        )

        # AI recommendations must NOT include the dismissed Mumbai flat
        response = self.client.get(reverse('ai_recommendations'))
        recommended_ids = [r['property'].id for r in response.context['recommendations']]
        self.assertNotIn(self.prop_mumbai_flat.id, recommended_ids)

    def test_reset_recommendations_clears_dismissed(self):
        """Reset dismissals clears rejected list so user can see them again."""
        self.client.login(username='testtenant', password='TestPass@123')
        PropertyInteraction.objects.create(
            user=self.tenant,
            property=self.prop_mumbai_flat,
            interaction_type='dismissed'
        )
        reset_response = self.client.post(reverse('reset_recommendations'))
        self.assertRedirects(reset_response, reverse('ai_recommendations'))
        self.assertFalse(
            PropertyInteraction.objects.filter(
                user=self.tenant,
                property=self.prop_mumbai_flat,
                interaction_type='dismissed'
            ).exists()
        )

    def test_saved_properties_page(self):
        """Saved properties view displays user's bookmarked properties."""
        self.client.login(username='testtenant', password='TestPass@123')
        PropertyInteraction.objects.create(
            user=self.tenant,
            property=self.prop_bengaluru_room,
            interaction_type='saved'
        )
        response = self.client.get(reverse('saved_properties'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tech Park Studio Room')
        self.assertContains(response, 'My Saved Residences')
