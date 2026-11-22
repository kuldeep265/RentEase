"""
Admin configuration for RentEase models.

Registers Property, Booking, and ContactMessage with the Django Admin.
Demonstrates:
- list_display for quick overview
- list_filter for sidebar filtering
- search_fields for text search
- readonly_fields for auto-generated timestamps
- fieldsets for organized editing
"""

from django.contrib import admin
from .models import Property, Booking, ContactMessage, Review


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'location', 'property_type',
        'rent', 'bedrooms', 'bathrooms',
        'owner', 'is_available', 'created_at'
    ]
    list_filter = ['property_type', 'is_available', 'created_at']
    search_fields = ['title', 'location', 'owner__username', 'owner__email']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        ('Basic Information', {
            'fields': ['title', 'description', 'location', 'property_type']
        }),
        ('Pricing & Details', {
            'fields': ['rent', 'bedrooms', 'bathrooms', 'amenities']
        }),
        ('Media', {
            'fields': ['image']
        }),
        ('Ownership & Status', {
            'fields': ['owner', 'is_available']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'property', 'tenant', 'start_date',
        'end_date', 'total_days', 'payment_amount', 'payment_status', 'status', 'created_at'
    ]
    list_filter = ['payment_status', 'status', 'created_at', 'start_date']
    search_fields = [
        'property__title', 'tenant__username',
        'tenant__email', 'tenant__first_name', 'tenant_full_name',
        'order_id', 'cf_order_id', 'cf_payment_id'
    ]
    readonly_fields = ['created_at', 'paid_at']

    fieldsets = [
        ('Booking Details', {
            'fields': ['property', 'tenant', 'start_date', 'end_date', 'total_days', 'guests', 'payment_amount', 'tenant_full_name', 'tenant_contact', 'message']
        }),
        ('Cashfree Payment Gateway', {
            'fields': ['payment_status', 'order_id', 'cf_order_id', 'payment_session_id', 'cf_payment_id', 'payment_method', 'paid_at']
        }),
        ('Status & Checkout', {
            'fields': ['status', 'checked_out', 'checkout_date']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'submitted_at']
    list_filter = ['submitted_at']
    search_fields = ['name', 'email', 'subject']
    readonly_fields = ['submitted_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'property', 'tenant', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['property__title', 'tenant__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']


# Customize admin site headers
admin.site.site_header = "RentEase Administration"
admin.site.site_title = "RentEase Admin"
admin.site.index_title = "Welcome to RentEase Admin Panel"
