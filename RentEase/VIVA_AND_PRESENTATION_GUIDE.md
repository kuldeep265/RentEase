# RentEase — Viva & Presentation Master Guide

> **A comprehensive preparation resource for presentation, live demonstration, and viva voce examination.**

---

## Table of Contents
1. [60-Second Elevator Pitch](#1-60-second-elevator-pitch)
2. [Slide-by-Slide Presentation Script](#2-slide-by-slide-presentation-script)
3. [5-Minute Live Demo Flowchart & Script](#3-5-minute-live-demo-flowchart--script)
4. [System Architecture & Database Design](#4-system-architecture--database-design)
5. [Top 31 Viva Questions & Answers](#5-top-31-viva-questions--answers)
6. [Last-Minute Cheat Sheet](#6-last-minute-cheat-sheet)

---

## 1. 60-Second Elevator Pitch
*Use this when the examiner asks: "Introduce your project in 1 minute."*

> "Good morning/afternoon, Sir/Ma'am. Our project is **RentEase**, a full-stack property rental web platform built using **Python, Django, SQLite, and modern responsive CSS**.
>
> In the traditional rental housing market, tenants face non-transparent broker fees, misleading photos, and fragmented communication. RentEase solves this by providing a direct, verified bridge between property owners and tenants.
>
> **Key technical highlights:**
> - **Architecture:** Developed following Django's **MVT (Model-View-Template)** pattern with complete server-side rendering.
> - **Core Workflows:** Tenants search and filter listings across cities, budget tiers, and property types, submit date-specific booking requests, and post verified star ratings & reviews for properties they have booked. Property owners manage their portfolio, publish listings with photography, and approve or reject tenant requests from an Owner Dashboard.
> - **Security:** Robust defenses including CSRF tokens on every form, backend ownership authorization checks against IDOR attacks, verified review authorization checks, and PBKDF2 password hashing.
> - **Quality Assurance:** Backed by an automated test suite containing **39 unit tests** with 100% pass rate."

---

## 2. Slide-by-Slide Presentation Script

### Slide 1: Title & Problem Statement
- **Slide Points:** Project Name: RentEase | Problem: High broker charges, unverified properties, lack of transparent booking status.
- **Spoken Script:** *"In metropolitan cities, finding rental housing often involves unverified middleman fees and non-transparent agreements. RentEase was engineered as a streamlined platform where property owners list residences directly and tenants submit booking requests with clear terms."*

### Slide 2: Architectural Overview & Tech Stack
- **Slide Points:** Architecture: Django MVT | Backend: Python 3 & Django 6 | Database: SQLite & Django ORM | Frontend: HTML5, Tailwind CSS, Custom Luxury CSS, Vanilla JS.
- **Spoken Script:** *"We selected the Django MVT architecture. The **Model** handles relational database schema and validation through the Django ORM. The **View** executes business logic, security checks, and database queries. The **Template** renders dynamic HTML templates on the server for speed, security, and SEO."*

### Slide 3: User Roles & Capabilities
- **Slide Points:**
  - **Tenants:** Browse listings, filter by location/budget/BHK, submit booking requests (start date, duration), monitor request status in real-time, and submit verified ratings & reviews.
  - **Property Owners:** Dedicated dashboard, manage property listings with photo uploads, review pending tenant requests, approve or reject applications with 1 click.
  - **Administrators:** Full operational management via Django Admin.
- **Spoken Script:** *"Our platform cleanly separates capabilities between tenants and property owners while giving administrators centralized control through the Django Admin panel. Tenants who book properties can also rate and review their stays to foster community trust."*

### Slide 4: Database Design & Relationships
- **Slide Points:** 
  - `User` (Django built-in auth)
  - `Property` (1-to-many with User as owner; dynamic average rating calculations)
  - `Booking` (ForeignKeys to User as tenant & Property, with status state-machine: Pending, Approved, Rejected, Cancelled)
  - `Review` (ForeignKeys to User as tenant & Property, 1–5 star rating with `unique_together` constraint)
  - `ContactMessage` (Enquiry records)
- **Spoken Script:** *"Our relational schema enforces data integrity. If a property is deleted, all associated booking requests and verified reviews cascade delete automatically via `on_delete=models.CASCADE`."*

### Slide 5: Security Implementation
- **Slide Points:**
  - CSRF protection on all POST forms (`{% csrf_token %}`)
  - SQL Injection prevention via ORM parameterized queries
  - Backend ownership checks in views (preventing IDOR vulnerabilities)
  - Verified review integrity (backend check ensures only booked tenants can rate, and owners cannot rate their own listings)
  - Cryptographic password hashing (PBKDF2 SHA-256)
  - Session-based authentication with `@login_required`
- **Spoken Script:** *"Security was built into the backend from day one. We never rely only on hiding buttons in HTML; our views verify that `property.owner == request.user` before allowing edits, and strictly verify active bookings before allowing review submissions."*

### Slide 6: Testing & Quality Assurance
- **Slide Points:** 39 automated unit tests in `properties/tests.py` covering URLs, views, models, form validations, access control, booking state transitions, and review verification. 100% pass rate.
- **Spoken Script:** *"We wrote 39 automated unit tests that verify HTTP status codes, form validations, unauthorized access prevention, booking workflow state transitions, and verified rating permissions."*

---

## 3. 5-Minute Live Demo Flowchart & Script

1. **Homepage & Hero Search (1 min):**
   - Open `http://127.0.0.1:8000/`.
   - Show the modern dark luxury interface with the 3D isometric building visual.
   - Enter `Chandigarh` or `25000` in the search bar and click Search.
   - *Say:* "Here on the homepage, tenants can search by city or budget. The search form submits GET parameters directly to our property list view."
2. **Explore Properties & Filters (1 min):**
   - Show the dynamic filter bar (Location, Max Rent, Type, Bedrooms).
   - *Say:* "The Explore view chains Django ORM querysets dynamically based on parameters and paginates results seamlessly."
3. **Property Details (1 min):**
   - Click on any property.
   - Show high-resolution photo, room specifications, amenity chips, and verified owner info.
   - *Say:* "Here the tenant sees complete verified specs. If unauthenticated, the system prompts them to log in before requesting a booking."
4. **Tenant Booking Request (1 min):**
   - Sign in as a tenant.
   - Fill in preferred move-in date and rental duration (e.g., 6 months).
   - Submit form and view the booking under `My Bookings` with status `Pending`.
   - *Say:* "The booking request is stored with a 'Pending' status and the tenant can monitor updates in real-time."
5. **Owner Dashboard & Action (45 sec):**
   - Sign in as the property owner.
   - Open `Dashboard`. Show listing counts, total bookings, and pending requests.
   - Click **Approve** on the tenant's booking request.
   - *Say:* "The owner reviews the tenant's move-in timeline and approves the request with one click, updating the status across the platform."
6. **Verified Tenant Rating & Review (45 sec):**
   - Switch to the tenant account and visit `My Bookings`.
   - Click **Rate & Review Property** next to the booked residence.
   - On the property detail page's `#reviews` section, submit a 5-star rating with feedback.
   - *Say:* "Because this tenant has a verified booking, they can rate the property. The system instantly recalculates the average rating and displays the verified tenant review badge."

---

## 4. System Architecture & Database Design

### MVT Architecture Breakdown
- **Model (`properties/models.py`):** Defines the database structure. Interacts with SQLite using the Django ORM.
- **View (`properties/views.py`):** Receives HTTP requests, performs business logic and permission checks, queries models, and renders templates.
- **Template (`templates/*.html`):** Uses Django Template Language (DTL) for server-side HTML rendering with template inheritance (`base.html`).

### Key Models & Fields
```python
# Property Model
class Property(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    rent = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1000)])
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    amenities = models.TextField(blank=True)
    image = models.ImageField(upload_to='properties/', blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def average_rating(self):
        reviews = self.reviews.all()
        return round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews.exists() else None

    def total_reviews(self):
        return self.reviews.count()

# Booking Model
class Booking(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    duration_months = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(36)])
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

# Review Model (Verified Tenant Reviews)
class Review(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('property', 'tenant')
```

---

## 5. Top 31 Viva Questions & Answers

### A. Django Fundamentals & Architecture
1. **What is Django?**
   *A high-level, batteries-included Python web framework designed for rapid, secure, and maintainable web development.*
2. **Explain the difference between MVC and MVT.**
   *In MVC, the Controller routes requests. In Django's MVT, the framework acts as Controller, the View executes business logic, the Model manages data schemas, and the Template handles presentation.*
3. **What is the role of `settings.py`?**
   *Contains project configurations including `INSTALLED_APPS`, `DATABASES`, `MIDDLEWARE`, `TEMPLATES`, authentication redirects, and static/media directories.*
4. **What is the difference between a project and an app?**
   *A project is the entire website setup (`rentease`). An app is a self-contained module representing a specific functional domain (`properties`).*
5. **How does URL routing work in Django?**
   *When a request arrives, Django traverses `urlpatterns` in `urls.py` sequentially using `path()` and matches the URL string to execute the associated view function.*

### B. Database & Django ORM
6. **What is Django ORM?**
   *An Object-Relational Mapper that maps Python classes to database tables, allowing developers to query, insert, update, and delete records without writing raw SQL.*
7. **What is `makemigrations` vs `migrate`?**
   *`makemigrations` creates migration instruction files based on changes in `models.py`. `migrate` applies those migration files to the database schema.*
8. **What is `on_delete=models.CASCADE`?**
   *A referential integrity rule specifying that if the parent record (e.g. User) is deleted, all associated child records (e.g. Properties) are automatically deleted.*
9. **How do you filter records with ORM?**
   *Using `Property.objects.filter()`. Lookups like `location__icontains` do case-insensitive substring matches, and `rent__lte` filters values less than or equal to.*
10. **What is the difference between `auto_now` and `auto_now_add`?**
    *`auto_now_add=True` records the timestamp once upon creation. `auto_now=True` updates the timestamp on every record save.*

### C. Views & Forms
11. **Why did you use Function-Based Views (FBVs)?**
    *FBVs offer explicit, readable control over HTTP methods, form validations, session messages, and permission checks.*
12. **What is the POST-Redirect-GET (PRG) pattern?**
    *After a successful POST request, the server returns an HTTP 302 Redirect to a GET URL. This prevents duplicate form submissions if the user refreshes the page.*
13. **What is the difference between `forms.Form` and `forms.ModelForm`?**
    *`Form` is a generic input form. `ModelForm` automatically creates form fields and validations directly from a Django model schema.*
14. **How does `get_object_or_404()` work?**
    *Retrieves an object by primary key; if the object doesn't exist, it cleanly raises an `Http404` exception instead of an unhandled 500 error.*
15. **How does form validation work in Django?**
    *Calling `form.is_valid()` executes built-in field validators, model validators, and custom `clean_<field>()` methods, populating `form.cleaned_data` or `form.errors`.*

### D. Security & Authentication
16. **How does CSRF protection work?**
    *Django sets a secret token in a cookie and requires forms to send it back via `{% csrf_token %}`. `CsrfViewMiddleware` verifies matching tokens on all POST requests.*
17. **What does `@login_required` do?**
    *Protects views by checking if the user is logged in. If anonymous, it redirects them to `/accounts/login/?next=<path>`.*
18. **How did you prevent unauthorized property edits?**
    *In `edit_property` and `delete_property`, the view explicitly checks `if property.owner != request.user: return redirect(...)`.*
19. **How does Django store user passwords?**
    *Passwords are hashed using PBKDF2 with SHA-256 and unique cryptographic salts. Plaintext passwords are never stored.*
20. **How does Django protect against SQL Injection?**
    *The ORM uses parameterized queries where input values are escaped and passed separately from the SQL statement.*
21. **How does Django prevent XSS attacks?**
    *The Django Template Language automatically HTML-escapes all dynamic variables by default.*

### E. Frontend & Media Files
22. **What is the difference between STATIC and MEDIA files?**
    *Static files are developer assets (CSS, JS, site logos). Media files are user-uploaded files (property photos uploaded via forms).*
23. **How does template inheritance work?**
    *`base.html` defines common layout with `{% block %}` tags. Child templates extend `base.html` and override specific blocks.*
24. **How is pagination handled?**
    *Using Django's `Paginator` class: `paginator = Paginator(properties, 6)` slices the queryset and passes page objects to the template.*

### F. Testing & Quality
25. **How did you test your Django application?**
    *By creating test classes inheriting from `django.test.TestCase` in `properties/tests.py`, covering 39 test cases across views, forms, authentication, permissions, booking workflows, and verified review permissions.*
26. **How do you run tests?**
    *`python manage.py test`. Django creates a temporary test database, runs all test methods, and outputs `OK` upon success.*

### G. Reviews & Trust Architecture
27. **How does the Rating & Review feature prevent fake reviews?**
    *RentEase enforces a strict backend booking-verification check: `Booking.objects.filter(property=property, tenant=request.user).exists()`. Only tenants who have actually submitted a booking for that property can submit reviews. Furthermore, owners cannot review their own properties (`property.owner == request.user`), and the `unique_together = ('property', 'tenant')` constraint ensures each tenant can leave only one review per property (updating it if resubmitted).*
28. **How is the average property rating calculated?**
    *As a dynamic model method `property.average_rating()` that queries `self.reviews.all()`, averages the star values rounded to 1 decimal place, and returns `None` if no reviews exist yet. This avoids redundant database columns while ensuring instant reactivity across property cards and details pages.*
29. **How did you implement review updates without duplicate entries?**
    *In `properties/models.py`, `Review.Meta` specifies `unique_together = ('property', 'tenant')`. In `add_review()`, the view checks if an existing review exists for that user and property. If so, it updates the existing record (`review.rating = form.cleaned_data['rating']; review.save()`); otherwise, it creates a new review. This prevents review spam while allowing tenants to revise their feedback.*
30. **What automated unit tests verify the review workflow?**
    *We created `ReviewTest` with 5 specific test cases: (1) anonymous users are redirected to login, (2) users who never booked cannot review, (3) owners cannot review their own properties, (4) booked tenants can submit 1–5 star reviews and the average rating recalculates, and (5) resubmission successfully updates the existing review.*
31. **How did you fix the dropdown `<select>` option visibility issue on Windows in dark mode?**
    *In Chromium/Edge on Windows, `<option>` tags inherit `color: #ffffff` from the parent select but render against the browser's default white popup surface. We resolved this by adding `color-scheme: dark;` to `:root` and applying `select option { background-color: #12121a !important; color: #ffffff !important; }` in `static/css/style.css`, ensuring dark surfaces and high-contrast readable options across all browsers.*

---

## 6. Last-Minute Cheat Sheet

| Task | Command |
|------|---------|
| Start Dev Server | `python manage.py runserver` |
| Run Test Suite | `python manage.py test` |
| Make Migrations | `python manage.py makemigrations` |
| Apply Migrations | `python manage.py migrate` |
| Create Superuser | `python manage.py createsuperuser` |
| Load Sample Data | `python manage.py seed_data` |

### Key URLs to Demo
- **Home:** `http://127.0.0.1:8000/`
- **Explore Properties:** `http://127.0.0.1:8000/properties/`
- **Owner Dashboard:** `http://127.0.0.1:8000/owner/dashboard/`
- **My Bookings:** `http://127.0.0.1:8000/my-bookings/`
- **Django Admin:** `http://127.0.0.1:8000/admin/`

### Demo Login Credentials
| Role | Username | Password | Notes |
|------|----------|----------|-------|
| **Property Owner** | `owner` | `Owner@1234` | Owns all 10 listings; manages bookings on Owner Dashboard |
| **Tenant User** | `user` | `User@1234` | Has active bookings; can rate & review properties |
