"""
Models for RentEase — Property and Booking.

Demonstrates:
- Django ORM models
- ForeignKey relationships
- Field types, choices, validators
- Model methods and Meta options
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import calendar
import builtins


class Property(models.Model):
    """
    Represents a rental property listed by an owner.
    """

    PROPERTY_TYPE_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House / Villa'),
        ('studio', 'Studio'),
        ('pg', 'PG / Hostel'),
        ('commercial', 'Commercial Space'),
        ('farmhouse', 'Farmhouse'),
    ]

    # Basic info
    title = models.CharField(max_length=200, help_text="Short descriptive title for the property.")
    description = models.TextField(help_text="Full description of the property.")
    location = models.CharField(max_length=200, help_text="City or area, e.g. 'Sector 17, Chandigarh'.")

    # Pricing
    rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(100)],
        help_text="Daily rent in INR (₹)."
    )

    # Classification
    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES,
        default='apartment',
    )

    # Room details
    bedrooms = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    bathrooms = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )

    # Amenities — stored as comma-separated text for simplicity
    amenities = models.TextField(
        blank=True,
        help_text="Comma-separated amenities, e.g. 'WiFi, Parking, AC'."
    )

    # Image upload — stored in media/properties/
    image = models.ImageField(
        upload_to='properties/',
        blank=True,
        null=True,
        help_text="Main property photo."
    )

    # Ownership
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties',
        help_text="The user who owns / listed this property."
    )

    # Status
    is_available = models.BooleanField(
        default=True,
        help_text="Whether this property is currently available for rent."
    )

    # Room availability tracking
    total_rooms = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Total number of rentable rooms/units in this property."
    )
    available_rooms = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Number of rooms currently available for booking."
    )

    # Timestamps — auto-managed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Property'
        verbose_name_plural = 'Properties'

    def __str__(self):
        return f"{self.title} — {self.location}"

    def get_amenities_list(self):
        """Return amenities as a Python list (split on commas)."""
        if self.amenities:
            return [a.strip() for a in self.amenities.split(',') if a.strip()]
        return []

    def get_property_type_display_value(self):
        """Convenience wrapper around Django's get_FOO_display()."""
        return self.get_property_type_display()

    def average_rating(self):
        """Return average star rating (1-5), or None if no reviews."""
        from django.db.models import Avg
        res = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(res, 1) if res is not None else None

    def total_reviews(self):
        """Return total review count."""
        return self.reviews.count()

    def is_available_for_dates(self, check_in, check_out, exclude_booking_id=None):
        """
        Check if property has available units for the specified date range.
        Overlaps when: booking.start_date < check_out and booking.end_date > check_in.
        Only approved active bookings count against availability.
        """
        if not self.is_available:
            return False
        overlapping = self.bookings.filter(
            status='approved',
            start_date__lt=check_out,
            end_date__gt=check_in,
        )
        if exclude_booking_id:
            overlapping = overlapping.exclude(pk=exclude_booking_id)
        return overlapping.count() < self.total_rooms

    def get_currently_occupied_count(self):
        """
        Number of units occupied by approved active or upcoming reservations that have not checked out.
        Counts all approved bookings where checked_out=False and end_date >= today.
        """
        today = timezone.now().date()
        return self.bookings.filter(
            status='approved',
            checked_out=False,
            end_date__gte=today
        ).count()

    def get_current_available_rooms(self):
        """Dynamically calculated available units."""
        occupied = self.get_currently_occupied_count()
        return max(0, self.total_rooms - occupied)

    @builtins.property
    def is_booked(self):
        """
        Check if property is currently booked/reserved.
        - For a single-unit property (total_rooms <= 1): Any approved booking with
          checked_out=False and end_date >= today means the property is booked.
        - For multi-unit properties (total_rooms > 1): True if all units are occupied.
        """
        today = timezone.now().date()
        active_count = self.bookings.filter(
            status='approved',
            checked_out=False,
            end_date__gte=today
        ).count()
        return active_count >= max(1, self.total_rooms)

    @builtins.property
    def is_currently_available(self):
        """
        Dynamically determine if the property is open and can be booked right now.
        Returns True only if:
        1. Owner marked listing as available (is_available == True)
        2. Property is not currently booked (not self.is_booked)
        3. Available rooms count > 0
        """
        if not self.is_available:
            return False
        if self.is_booked:
            return False
        return self.get_current_available_rooms() > 0

    def save(self, *args, **kwargs):
        """Auto-set is_available to False when no rooms are left."""
        if self.available_rooms <= 0:
            self.is_available = False
        super().save(*args, **kwargs)


class Booking(models.Model):
    """
    Represents a tenant's booking request for a property.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    # Relationships
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
    )

    # Booking dates & duration
    start_date = models.DateField(help_text="Check-in date.")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Check-out date."
    )
    total_days = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Total duration of stay in days."
    )
    guests = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Number of guests."
    )

    # Legacy fields kept for backward compatibility
    duration_type = models.CharField(
        max_length=6,
        default='days',
        blank=True,
        null=True,
        help_text="Rental duration type (days)."
    )
    duration_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(36)],
        help_text="Legacy duration in months."
    )
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Rental duration in days."
    )

    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total payment amount in INR (₹)."
    )
    message = models.TextField(
        blank=True,
        help_text="Optional message to the owner."
    )

    # Tenant contact information
    tenant_contact = models.CharField(
        max_length=20,
        blank=True,
        help_text="Tenant's contact phone number."
    )
    tenant_full_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Tenant's full name as provided at booking time."
    )

    # Status — defaults to Pending
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
    )

    # Cashfree Payment Gateway Fields
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid / Confirmed'),
        ('FAILED', 'Payment Failed'),
        ('CANCELLED', 'Payment Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Unique Cashfree order identifier."
    )
    cf_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cashfree internal order reference."
    )
    payment_session_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Cashfree payment session ID for SDK checkout."
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Payment status from Cashfree gateway."
    )
    cf_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cashfree transaction/payment ID upon success."
    )
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Payment method used (e.g. UPI, CARD, NETBANKING)."
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when payment was successfully completed."
    )

    # Checkout tracking
    checked_out = models.BooleanField(
        default=False,
        help_text="Set to True when the tenant checks out and vacates the room."
    )
    checkout_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual checkout date recorded by the owner."
    )

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Booking Request'
        verbose_name_plural = 'Booking Requests'

    def __str__(self):
        return f"Booking by {self.tenant.username} for '{self.property.title}' — {self.status}"

    def calculate_total_price(self):
        """Calculate total booking cost: total_days * property daily rent."""
        days = self.total_days or 1
        if self.property and self.property.rent:
            from decimal import Decimal
            return round(Decimal(str(self.property.rent)) * days, 2)
        return Decimal('0.00')

    def duration_display(self):
        """Human-readable duration string."""
        days = self.total_days or (self.duration_days if self.duration_days else 1)
        return f"{days} day{'s' if days != 1 else ''}"

    @builtins.property
    def is_paid(self):
        """Check if booking payment was completed successfully."""
        return self.payment_status == 'PAID'

    def save(self, *args, **kwargs):
        """Auto-calculate total_days, end_date, and payment_amount on save."""
        from datetime import timedelta
        if self.start_date and self.end_date:
            diff = (self.end_date - self.start_date).days
            self.total_days = max(diff, 1)
            self.duration_days = self.total_days
        elif self.start_date and self.duration_days:
            self.total_days = self.duration_days
            self.end_date = self.start_date + timedelta(days=self.total_days)
        elif self.start_date and self.duration_months:
            self.total_days = self.duration_months * 30
            self.duration_days = self.total_days
            self.end_date = self.start_date + timedelta(days=self.total_days)

        if self.property_id:
            self.payment_amount = self.calculate_total_price()
        super().save(*args, **kwargs)

    def get_tenant_display_name(self):
        """Return the name provided at booking, falling back to User profile."""
        return self.tenant_full_name or self.tenant.get_full_name() or self.tenant.username


class ContactMessage(models.Model):
    """
    Stores messages submitted via the Contact page form.
    (Demonstration only — no email delivery configured.)
    """
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f"Message from {self.name} <{self.email}> — {self.subject[:50]}"


class Review(models.Model):
    """
    Represents a tenant's rating and review for a property they have booked.
    Enforces that only verified tenants with a booking can review.
    """
    RATING_CHOICES = [
        (5, '★★★★★ (5/5) — Exceptional'),
        (4, '★★★★☆ (4/5) — Very Good'),
        (3, '★★★☆☆ (3/5) — Good'),
        (2, '★★☆☆☆ (2/5) — Fair'),
        (1, '★☆☆☆☆ (1/5) — Poor'),
    ]

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The property being reviewed."
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The tenant who booked and reviewed this property."
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Star rating from 1 to 5."
    )
    comment = models.TextField(
        blank=True,
        help_text="Written review feedback."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('property', 'tenant')
        verbose_name = 'Property Review'
        verbose_name_plural = 'Property Reviews'

    def __str__(self):
        return f"{self.rating}★ review by {self.tenant.username} for '{self.property.title}'"


# =========================================================================== #
#  AI Recommendation & Behavioral Learning Models
# =========================================================================== #

class PropertyInteraction(models.Model):
    """
    Tracks tenant actions on properties for behavioral AI learning:
    - 'saved': User favorited/bookmarked a property (positive signal: +weight on traits).
    - 'dismissed': User rejected/'Not Interested' (negative signal: penalty / auto-exclude).
    - 'viewed': User inspected the property details.
    Supports both logged-in users and anonymous sessions via session_key.
    """
    INTERACTION_CHOICES = [
        ('saved', 'Saved / Favorited'),
        ('dismissed', 'Dismissed / Rejected'),
        ('viewed', 'Viewed Details'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='property_interactions',
        help_text="Authenticated user (optional if guest)."
    )
    session_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Session identifier for anonymous guest learning."
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='interactions',
        help_text="Target property."
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_CHOICES,
        help_text="Action performed by the tenant."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'interaction_type']),
            models.Index(fields=['session_key', 'interaction_type']),
        ]
        verbose_name = 'Property Interaction'
        verbose_name_plural = 'Property Interactions'

    def __str__(self):
        actor = self.user.username if self.user else f"Guest ({self.session_key[:8]}...)"
        return f"{actor} -> {self.interaction_type} '{self.property.title}'"


class UserSearchPreference(models.Model):
    """
    Records search queries to establish user taste profiles over time.
    AI engine learns recurring budgets, locations, and desired amenities.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='search_preferences'
    )
    session_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True
    )
    target_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="User's preferred daily budget in INR."
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Preferred city, area, or landmark."
    )
    property_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Desired property category (apartment, house, pg, studio)."
    )
    amenities = models.CharField(
        max_length=300,
        blank=True,
        help_text="Comma-separated requested amenities (e.g. WiFi, AC, Parking)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Search Preference'
        verbose_name_plural = 'User Search Preferences'

    def __str__(self):
        actor = self.user.username if self.user else f"Guest ({self.session_key[:8]}...)"
        return f"Search by {actor} — {self.location or 'Any location'} (₹{self.target_budget or 'Any'})"

