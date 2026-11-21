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

    def test_tenant_can_submit_booking(self):
        """A valid booking request is saved to the database."""
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'start_date': self.future_date,
                'duration_months': 6,
                'message': 'Hello owner!',
            }
        )
        self.assertTrue(
            Booking.objects.filter(tenant=self.tenant, property=self.prop).exists()
        )

    def test_owner_cannot_book_own_property(self):
        """An owner booking their own property must be rejected."""
        self.client.login(username='testowner', password='TestPass@123')
        self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'start_date': self.future_date,
                'duration_months': 3,
            }
        )
        # No booking should be created
        self.assertFalse(
            Booking.objects.filter(tenant=self.owner, property=self.prop).exists()
        )

    def test_past_date_rejected(self):
        """A booking with a past start date must be rejected."""
        self.client.login(username='testtenant', password='TestPass@123')
        past_date = (date.today() - timedelta(days=5)).isoformat()
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'start_date': past_date,
                'duration_months': 3,
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
            duration_months=2,
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
                'start_date': self.future_date,
                'duration_months': 2,
            }
        )
        self.assertFalse(
            Booking.objects.filter(tenant=self.tenant, property=unavailable).exists()
        )

    def test_owner_can_approve_booking(self):
        """Owner can approve a pending booking via POST."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            duration_months=3,
        )
        self.client.login(username='testowner', password='TestPass@123')
        self.client.post(
            reverse('manage_booking', args=[booking.pk]),
            {'action': 'approve'}
        )
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'approved')

    def test_other_owner_cannot_manage_booking(self):
        """A different owner cannot approve/reject another owner's booking."""
        other_owner = make_owner(username='stranger_owner')
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            duration_months=3,
        )
        self.client.login(username='stranger_owner', password='TestPass@123')
        self.client.post(
            reverse('manage_booking', args=[booking.pk]),
            {'action': 'approve'}
        )
        booking.refresh_from_db()
        # Status should remain 'pending' — unauthorized change rejected
        self.assertEqual(booking.status, 'pending')

    def test_tenant_can_cancel_pending_booking(self):
        """Tenant can cancel their own pending booking."""
        booking = Booking.objects.create(
            property=self.prop,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            duration_months=3,
        )
        self.client.login(username='testtenant', password='TestPass@123')
        self.client.post(reverse('cancel_booking', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_form_validation_duration_zero_rejected(self):
        """Duration of 0 months must be rejected by the form."""
        self.client.login(username='testtenant', password='TestPass@123')
        response = self.client.post(
            reverse('book_property', args=[self.prop.pk]),
            {
                'start_date': self.future_date,
                'duration_months': 0,
            }
        )
        self.assertFalse(
            Booking.objects.filter(tenant=self.tenant, property=self.prop).exists()
        )


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
