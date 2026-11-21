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
        validators=[MinValueValidator(1000)],
        help_text="Monthly rent in INR (₹)."
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

    def save(self, *args, **kwargs):
        """Auto-set is_available to False when no rooms are left."""
        if self.available_rooms <= 0:
            self.is_available = False
        else:
            self.is_available = True
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

    # Request details
    DURATION_TYPE_CHOICES = [
        ('months', 'Months'),
        ('days', 'Days'),
    ]

    start_date = models.DateField(help_text="Preferred move-in date.")
    duration_type = models.CharField(
        max_length=6,
        choices=DURATION_TYPE_CHOICES,
        default='months',
        help_text="Whether the rental duration is specified in months or days."
    )
    duration_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(36)],
        help_text="Rental duration in months (1–36). Used when duration_type is 'months'."
    )
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Rental duration in days (1–365). Used when duration_type is 'days'."
    )
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1000)],
        help_text="Total payment amount collected at booking time (min ₹1,000)."
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

    @builtins.property
    def end_date(self):
        """Calculate the expected checkout date based on duration_type."""
        if not self.start_date:
            return None
        from datetime import date, timedelta
        if self.duration_type == 'days' and self.duration_days:
            return self.start_date + timedelta(days=self.duration_days)
        if self.duration_months:
            month = self.start_date.month - 1 + self.duration_months
            year = self.start_date.year + month // 12
            month = month % 12 + 1
            day = min(self.start_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
        return None

    def duration_display(self):
        """Human-readable duration string."""
        if self.duration_type == 'days' and self.duration_days:
            return f"{self.duration_days} day{'s' if self.duration_days != 1 else ''}"
        if self.duration_months:
            return f"{self.duration_months} month{'s' if self.duration_months != 1 else ''}"
        return "—"

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

