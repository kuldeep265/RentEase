# -*- coding: utf-8 -*-
"""
Management command to populate the database with sample property data.

Run with:
    python manage.py seed_data

Creates:
- 2 sample owner users (owner1 / owner2)
- 1 sample tenant user (tenant1)
- 10 realistic properties in Indian cities
- 3 sample booking requests

All passwords are set to 'RentEase@123' -- change in production!
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from properties.models import Property, Booking, Review
from datetime import date, timedelta


SAMPLE_PROPERTIES = [
    {
        'title': 'Spacious 3BHK Apartment Near Sukhna Lake',
        'description': (
            'A beautifully furnished 3-bedroom apartment in the heart of Chandigarh. '
            'Walking distance from Sukhna Lake, with stunning views of the Shivalik Hills. '
            'The apartment features modern interiors, a well-equipped kitchen, and a large balcony. '
            'Ideal for families or working professionals.'
        ),
        'location': 'Sector 17, Chandigarh',
        'rent': 35000,
        'property_type': 'apartment',
        'bedrooms': 3,
        'bathrooms': 2,
        'amenities': 'WiFi, Parking, AC, Lift, Security, Power Backup, Modular Kitchen',
        'owner_index': 0,
    },
    {
        'title': 'Cozy Studio Apartment for Students',
        'description': (
            'A compact and affordable studio apartment perfect for students at LPU or GNDU. '
            'Fully furnished with a study desk, wardrobe, and a small kitchenette. '
            'Located just 2 km from Lovely Professional University campus.'
        ),
        'location': 'GT Road, Phagwara',
        'rent': 8500,
        'property_type': 'studio',
        'bedrooms': 0,
        'bathrooms': 1,
        'amenities': 'WiFi, Hot Water, Washing Machine, 24/7 Security',
        'owner_index': 0,
    },
    {
        'title': 'Modern 2BHK Flat in Jalandhar Cantt',
        'description': (
            'A well-maintained 2-bedroom flat on the 3rd floor of a gated society in Jalandhar. '
            'The flat is semi-furnished with a split AC, fully tiled bathrooms, and ample storage. '
            'Close to schools, hospitals, and the railway station.'
        ),
        'location': 'Cantt Area, Jalandhar',
        'rent': 15000,
        'property_type': 'apartment',
        'bedrooms': 2,
        'bathrooms': 2,
        'amenities': 'Parking, AC, Security, Children Play Area, Power Backup',
        'owner_index': 0,
    },
    {
        'title': 'Premium PG Accommodation for Working Professionals',
        'description': (
            'Fully-furnished PG with meals included, located in the heart of Delhi IT hub. '
            'Single and double-sharing options available. '
            'Amenities include housekeeping, laundry, WiFi, and a common lounge area.'
        ),
        'location': 'Laxmi Nagar, Delhi',
        'rent': 12000,
        'property_type': 'pg',
        'bedrooms': 1,
        'bathrooms': 1,
        'amenities': 'WiFi, Meals Included, Laundry, Housekeeping, Lounge',
        'owner_index': 1,
    },
    {
        'title': 'Elegant 4BHK Villa with Private Garden',
        'description': (
            'A stunning independent villa in one of Delhi most sought-after colonies. '
            'Spread over 2500 sq ft with 4 spacious bedrooms, 3 bathrooms, a private garden, '
            'a dedicated car parking space, and a terrace with a panoramic city view. '
            'Perfect for large families.'
        ),
        'location': 'Vasant Kunj, Delhi',
        'rent': 85000,
        'property_type': 'house',
        'bedrooms': 4,
        'bathrooms': 3,
        'amenities': 'Private Garden, Terrace, Parking x2, AC, Security Camera, Inverter, Modular Kitchen',
        'owner_index': 1,
    },
    {
        'title': 'Tech Hub Studio in Koramangala',
        'description': (
            'A sleek studio apartment right in the middle of Bengaluru startup capital, Koramangala. '
            'Ideal for solo tech professionals. High-speed WiFi, ergonomic workspace, and walking '
            'distance from cafes, restaurants, and co-working spaces.'
        ),
        'location': 'Koramangala, Bengaluru',
        'rent': 22000,
        'property_type': 'studio',
        'bedrooms': 0,
        'bathrooms': 1,
        'amenities': 'High-Speed WiFi, AC, Furnished, Housekeeping, CCTV',
        'owner_index': 1,
    },
    {
        'title': 'Luxury 3BHK with Clubhouse Access',
        'description': (
            'Experience premium living in this 3-bedroom apartment in one of Bengaluru finest '
            'residential societies. Residents enjoy access to a swimming pool, gymnasium, and '
            'fully-equipped clubhouse. The apartment is tastefully furnished and ready to move in.'
        ),
        'location': 'Whitefield, Bengaluru',
        'rent': 55000,
        'property_type': 'apartment',
        'bedrooms': 3,
        'bathrooms': 3,
        'amenities': 'Swimming Pool, Gym, Clubhouse, Parking, AC, Security, Power Backup, Garden',
        'owner_index': 0,
    },
    {
        'title': 'Budget-Friendly 1BHK Near Hinjewadi IT Park',
        'description': (
            'An affordable and comfortable 1-bedroom apartment just 10 minutes from the '
            'Hinjewadi IT Park, perfect for IT professionals. The apartment has a modular '
            'kitchen, regular water supply, and a parking spot.'
        ),
        'location': 'Hinjewadi, Pune',
        'rent': 14000,
        'property_type': 'apartment',
        'bedrooms': 1,
        'bathrooms': 1,
        'amenities': 'Parking, Modular Kitchen, 24/7 Water, Security',
        'owner_index': 1,
    },
    {
        'title': 'Charming Farmhouse Weekend Retreat',
        'description': (
            'Escape the city in this sprawling farmhouse on the outskirts of Pune. '
            'Set on 1.5 acres of lush land with fruit trees, an open-air barbecue area, '
            'and a private borewell. The farmhouse has 5 bedrooms and can accommodate up to 12 guests.'
        ),
        'location': 'Mulshi, Pune',
        'rent': 75000,
        'property_type': 'farmhouse',
        'bedrooms': 5,
        'bathrooms': 4,
        'amenities': 'Open-Air BBQ, Fruit Orchard, Borewell, Caretaker, Parking, Bonfire Area',
        'owner_index': 0,
    },
    {
        'title': 'Commercial Shop Space in Market Area',
        'description': (
            'A well-positioned commercial space suitable for a retail shop, salon, cafe, or office. '
            'Ground floor with direct street access, separate loading area, and 3-phase power supply. '
            'Located in a busy market area with high foot traffic.'
        ),
        'location': 'Sector 22, Chandigarh',
        'rent': 45000,
        'property_type': 'commercial',
        'bedrooms': 0,
        'bathrooms': 1,
        'amenities': '3-Phase Power, Street Frontage, Loading Bay, CCTV, 24/7 Access',
        'owner_index': 1,
    },
]


class Command(BaseCommand):
    help = 'Seeds the database with sample users and property listings for demonstration.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('RentEase -- Seeding sample data...'))

        # --- Create owner user ---
        owner, created = User.objects.get_or_create(
            username='owner',
            defaults={
                'first_name': 'Vikram',
                'last_name': 'Singhania',
                'email': 'owner@rentease.com',
            }
        )
        owner.set_password('Owner@1234')
        owner.save()
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Created owner: owner'))
        else:
            self.stdout.write('  [--] Updated owner credentials: owner')

        # --- Create tenant/user ---
        user, created = User.objects.get_or_create(
            username='user',
            defaults={
                'first_name': 'Aarav',
                'last_name': 'Patel',
                'email': 'user@rentease.com',
            }
        )
        user.set_password('User@1234')
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Created tenant user: user'))
        else:
            self.stdout.write('  [--] Updated user credentials: user')

        # --- Create properties ---
        created_properties = []
        for data in SAMPLE_PROPERTIES:
            prop, created = Property.objects.get_or_create(
                title=data['title'],
                owner=owner,
                defaults={
                    'description': data['description'],
                    'location': data['location'],
                    'rent': data['rent'],
                    'property_type': data['property_type'],
                    'bedrooms': data['bedrooms'],
                    'bathrooms': data['bathrooms'],
                    'amenities': data['amenities'],
                    'image': 'properties/image.png',
                    'is_available': True,
                }
            )
            if not created and not prop.image:
                prop.image = 'properties/image.png'
                prop.save()

            if created:
                self.stdout.write(self.style.SUCCESS('  [OK] Created property: ' + prop.title[:60]))
            else:
                self.stdout.write('  [--] Property already exists: ' + prop.title[:60])
            created_properties.append(prop)

        # --- Create sample bookings for user ---
        booking_data = [
            (created_properties[0], user, date.today() + timedelta(days=15), 6,
             'Looking forward to moving in!', 'approved'),
            (created_properties[2], user, date.today() + timedelta(days=30), 12,
             'Will be moving with family next month.', 'pending'),
            (created_properties[6], user, date.today() + timedelta(days=7), 3,
             'Need short-term corporate stay near clubhouse.', 'pending'),
        ]
        for prop, ten, start, duration, msg, status in booking_data:
            booking, created = Booking.objects.get_or_create(
                property=prop,
                tenant=ten,
                defaults={
                    'start_date': start,
                    'duration_months': duration,
                    'message': msg,
                    'status': status,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    '  [OK] Created booking: ' + ten.username + ' -> ' + prop.title[:40]
                ))
            else:
                self.stdout.write(
                    '  [--] Booking already exists for ' + ten.username + ' -> ' + prop.title[:40]
                )

        # --- Create sample reviews for booked properties ---
        if created_properties:
            sample_reviews = [
                (created_properties[0], user, 5, 'Spectacular residence with pristine hill views and exceptional finish. Responsive owner and flawless move-in experience!'),
            ]
            for prop, ten, rating, comment in sample_reviews:
                rev, created = Review.objects.get_or_create(
                    property=prop,
                    tenant=ten,
                    defaults={'rating': rating, 'comment': comment}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f'  [OK] Created {rating}★ review: {ten.username} -> {prop.title[:40]}'
                    ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
        self.stdout.write('')
        self.stdout.write('  Sample login credentials:')
        self.stdout.write('  Owner  : username=owner   password=Owner@1234')
        self.stdout.write('  Tenant : username=user    password=User@1234')
        self.stdout.write('')
