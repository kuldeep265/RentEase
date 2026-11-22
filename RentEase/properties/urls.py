"""
URL routing for the RentEase properties app.

All routes live here — the root urls.py simply includes this file.
Demonstrates named URL patterns for use with {% url %} in templates.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ---- Public Pages ----
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # ---- AI Recommendation System ----
    path('recommendations/', views.ai_recommendations, name='ai_recommendations'),
    path('recommendations/saved/', views.saved_properties, name='saved_properties'),
    path('recommendations/toggle-save/<int:pk>/', views.toggle_save_property, name='toggle_save_property'),
    path('recommendations/dismiss/<int:pk>/', views.dismiss_property, name='dismiss_property'),
    path('recommendations/reset/', views.reset_recommendations, name='reset_recommendations'),

    # ---- Property Listing & Detail ----
    path('properties/', views.property_list, name='property_list'),
    path('properties/<int:pk>/', views.property_detail, name='property_detail'),
    path('properties/<int:pk>/review/', views.add_review, name='add_review'),

    # ---- Authentication ----
    path('accounts/register/', views.register_view, name='register'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),

    # ---- Bookings & Cashfree Payments ----
    path('properties/<int:pk>/book/', views.book_property, name='book_property'),
    path('bookings/<int:booking_id>/checkout/', views.cashfree_checkout, name='cashfree_checkout'),
    path('bookings/payment/callback/', views.payment_callback, name='payment_callback'),
    path('bookings/<int:booking_id>/simulate-payment/', views.simulate_payment, name='simulate_payment'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('my-bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),

    # ---- Owner Dashboard ----
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/properties/add/', views.add_property, name='add_property'),
    path('owner/properties/<int:pk>/edit/', views.edit_property, name='edit_property'),
    path('owner/properties/<int:pk>/delete/', views.delete_property, name='delete_property'),
    path('owner/bookings/<int:pk>/manage/', views.manage_booking, name='manage_booking'),
    path('owner/bookings/<int:pk>/checkout/', views.checkout_booking, name='checkout_booking'),
]
