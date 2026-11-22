# RentEase — Luxury Property Rental Platform

> **Discover Your Future: Find The Perfect Property.**

RentEase is a full-stack Django web application for luxury property rentals. Property owners can list and manage residences, and tenants can search, multi-criteria filter, book stays, and leave verified ratings & reviews through a responsive, modern dark architectural interface.

---

## Key Features

- **Luxury Architectural UI** — High-contrast dark obsidian design system with warm bronze & gold accents, 3D building visual, and responsive layouts.
- **Search & Multi-Criteria Filtering** — Real-time filtering by city location, max rent budget, property type, and minimum bedroom count.
- **Property Portfolio Management** — High-resolution photo support, detailed room specifications, amenity chips, and verified owner info.
- **Role-Based Authentication** — Secure registration, login, and session-based access control with `@login_required`.
- **Cashfree Payment Gateway Integration** — Seamless Cashfree Sandbox integration via Cashfree Web Checkout JS SDK v3:
  - Supports UPI (GPay, PhonePe, Paytm), Credit & Debit Cards, Netbanking, and Wallets.
  - Generates secure backend order sessions via Cashfree PG REST API (`POST /orders`).
  - Verifies server-to-server transaction status on return callback (`GET /orders/{order_id}`).
  - Built-in graceful sandbox simulation fallback for offline local testing and automated tests.
- **Instant Booking Confirmation (No Manual Approval)** — Manual owner accept/reject has been replaced with modern instant booking confirmation immediately upon verified payment.
- **Date-Specific Stay Reservation** — Check-in & check-out date pickers with conflict prevention against double-booking, daily pricing (`rent/day`), and live dynamic price calculation.
- **Owner Dashboard** — Centralized hub for owners to monitor listings, total earnings/revenue, occupied units, active tenants, and mark checkouts when guests depart.
- **Verified Rating & Review System** — Relational booking verification ensures only guests who have booked a property can submit a 1–5 star rating and review. Automatic dynamic average rating calculations across property cards and detail views.
- **Security & Integrity** — CSRF tokens on every form, backend ownership authorization checks against IDOR attacks, and PBKDF2 password hashing.
- **Automated Test Suite** — **43 automated unit tests** covering URLs, views, models, forms, Cashfree payment workflow, callback verification, date conflict prevention, and access control with 100% pass rate.
- **Django Admin Panel** — Full operational backoffice for administrators.

## Technology Stack

| Technology       | Purpose                              |
|-----------------|--------------------------------------|
| Python 3        | Core backend programming language    |
| Django 6.x      | High-level web framework (MVT)       |
| SQLite           | Relational database engine           |
| Django ORM       | Parameterized queries & schema models|
| Django Templates | Server-side HTML rendering (DTL)     |
| Tailwind CSS     | Utility CSS framework (Play CDN)     |
| Custom Dark CSS  | Luxury design system (`style.css`)   |
| Vanilla JS       | Real-time alerts, DOM toggles        |
| Pillow           | High-res photo upload processing     |

## Prerequisites

- **Python 3.10+** (tested and verified on Python 3.14)
- **pip** (Python package manager)

## Installation & Setup

### 1. Navigate to Project Directory

```bash
cd RentEase
```

### 2. Create and Activate Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1

# Windows (Command Prompt)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Sample Data

```bash
python manage.py seed_data
```

This populates the database with:
- **1 Owner account**: `owner` (password: `Owner@1234`)
- **1 Tenant account**: `user` (password: `User@1234`)
- **10 Luxury properties** across Indian cities (all with architectural photography)
- **3 Sample bookings** (Approved and Pending)
- **Verified tenant 5★ review** with real-time average rating calculation

### 6. Create Superuser (Optional, for Django Admin)

```bash
python manage.py createsuperuser
```

### 7. Start the Development Server

```bash
python manage.py runserver
```

Open your browser at: **http://127.0.0.1:8000/**

---

## Demo Login Credentials

| Role | Username | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Property Owner** | `owner` | `Owner@1234` | Owns all 10 listings; manages requests on Owner Dashboard |
| **Tenant User** | `user` | `User@1234` | Has active bookings; can rate & review residences |
| **Administrator** | `rentease` | *(set via createsuperuser)* | Full platform control at `/admin/` |

---

## Important Routes

| URL | View / Purpose | Access Level |
|---|---|---|
| `/` | Homepage with hero search & featured properties | Public |
| `/properties/` | Explore properties catalog with multi-filters | Public |
| `/properties/<id>/` | Property specifications, photos & reviews | Public |
| `/properties/<id>/book/` | Select dates & guest details -> Proceed to Payment | Logged-in Tenant |
| `/bookings/<id>/checkout/` | Cashfree Sandbox Web Checkout (SDK v3) | Logged-in Tenant |
| `/bookings/payment/callback/` | Cashfree server return & instant confirmation | Authenticated |
| `/bookings/<id>/simulate-payment/` | Dev/test quick payment simulator | Logged-in Tenant |
| `/properties/<id>/review/`| Submit / update verified rating & review | Verified Booked Tenant |
| `/my-bookings/` | Tenant booking tracker & payment status | Logged-in Tenant |
| `/owner/dashboard/` | Portfolio statistics, revenue & checkout actions | Property Owner |
| `/owner/properties/add/` | Publish new property listing | Property Owner |
| `/owner/properties/<id>/edit/` | Edit property specifications | Property Owner |
| `/owner/properties/<id>/delete/` | Remove listing from platform | Property Owner |
| `/accounts/register/` | Create tenant / owner account | Public |
| `/accounts/login/` | Secure authentication | Public |
| `/accounts/logout/` | End user session (POST only) | Authenticated |
| `/about/` | Company information & milestones | Public |
| `/contact/` | Enquiry form (saves to database) | Public |
| `/admin/` | Django Administrative backoffice | Superuser |

## Project Structure

```
RentEase/
    manage.py                     # Django CLI entry point
    requirements.txt              # Python dependencies
    README.md                     # Project documentation
    VIVA_AND_PRESENTATION_GUIDE.html # Comprehensive Viva & Presentation Master Guide
    VIVA_AND_PRESENTATION_GUIDE.md   # Terminal/Markdown Viva & Presentation Guide
    .gitignore                    # Git exclusions
    db.sqlite3                    # SQLite database
    rentease/                     # Project configuration
        settings.py               # Django settings (apps, media, static, auth)
        urls.py                   # Master URL routing
        wsgi.py / asgi.py         # Web server gateway interfaces
    properties/                   # Core application
        models.py                 # Property, Booking, Review, ContactMessage
        views.py                  # All business logic (FBVs)
        forms.py                  # Django Forms & ModelForms
        urls.py                   # App URL patterns
        admin.py                  # Django Admin registrations
        tests.py                  # 39 automated unit tests
        management/commands/
            seed_data.py          # Sample data management command
    templates/                    # Server-rendered HTML templates
        base.html                 # Master layout (navbar, toast alerts, footer)
        home.html                 # Modern dark architectural homepage
        about.html                # About page
        contact.html              # Contact page
        properties/
            property_list.html    # Catalog with multi-filter bar
            property_detail.html  # High-res photo, specs, booking & reviews
            property_form.html    # Add / edit property form
            property_confirm_delete.html # Safe deletion confirmation
        accounts/
            login.html            # Authentication login
            register.html         # User registration
        bookings/
            my_bookings.html      # Tenant reservation status & rating button
            book_property.html    # Booking request form
        dashboard/
            owner_dashboard.html  # Owner portfolio overview & approvals
    static/
        css/style.css             # Luxury dark design system & color-scheme
        images/                   # 3D isometric building render & brand assets
        js/main.js                # Toast alert auto-dismiss & UI toggles
    media/
        properties/               # User-uploaded property photography
```

## Django Architecture & Concepts Demonstrated

### 1. Model-View-Template (MVT) Pattern
- **Model (`properties/models.py`):** Relational schema definition with field-level validators (`MinValueValidator`, `MaxValueValidator`), compound indexes (`unique_together = ('property', 'tenant')`), and dynamic calculations (`average_rating()`).
- **View (`properties/views.py`):** Function-Based Views (FBVs) managing request lifecycle, HTTP methods (GET/POST), server validation, error messages, and redirects.
- **Template (`templates/*.html`):** Server-side rendering with Django Template Language (DTL), layout inheritance (`base.html`), contextual variables, and filters.

### 2. Database & ORM Integrity
- **Relational Integrity:** ForeignKeys linking `Property` to `User` (owner), `Booking` to `Property` & `User` (tenant), and `Review` to `Property` & `User`.
- **Cascade Deletion:** `on_delete=models.CASCADE` ensures zero orphan records when a listing or user is deleted.
- **Dynamic Aggregation:** Star ratings are aggregated on the fly using `average_rating()` and `total_reviews()`, keeping records synchronized.

### 3. Security & Access Control
- **CSRF Protection:** Every POST form includes `{% csrf_token %}` validated by `CsrfViewMiddleware`.
- **IDOR / Ownership Protection:** Views explicitly verify `if property.owner != request.user:` before allowing edit or delete operations.
- **Review Integrity:** Strict validation ensures only tenants with existing bookings can submit reviews (`Booking.objects.filter(property=property, tenant=request.user).exists()`), and owners cannot review their own properties.
- **Password Security:** Salted PBKDF2 with SHA-256 password hashing.
- **SQL Injection Prevention:** Parameterized ORM queries.

## Automated Testing

RentEase features **39 automated unit tests** built with Django's test runner (`django.test.TestCase`):

```bash
python manage.py test
```

### Test Coverage Summary:
- **Public Views:** HTTP 200 checks on Home, About, Contact, and Explore.
- **Filter & Search:** Location keywords, budget max thresholds, bedroom counts.
- **Authentication:** Registration with password confirmation, valid/invalid logins.
- **Access Control:** Anonymous redirects to `/accounts/login/`, IDOR prevention on property edit/delete.
- **Booking State Machine:** Move-in date validation, duration range (1–36 months), owner approval/rejection, tenant cancellation.
- **Verified Reviews:** Anonymous rejection, unbooked user rejection, owner self-review rejection, verified submission, and review update without duplicate records.

---

## Presentation & Viva Preparation

Comprehensive documentation for academic evaluations, live demonstrations, and viva voce examinations:

- **[VIVA_AND_PRESENTATION_GUIDE.html](file:///c:/Users/kashy/OneDrive/Desktop/RentEase/VIVA_AND_PRESENTATION_GUIDE.html)** — An interactive, styled examination guide featuring:
  - 60-Second Elevator Pitch
  - 6-Slide Presentation Script with spoken notes
  - 5-Minute Live Demo walkthrough
  - System Architecture & ERD diagram
  - Top 30 Viva Questions & Detailed Answers
  - Quick-Reference Cheat Sheet
- **[VIVA_AND_PRESENTATION_GUIDE.md](file:///c:/Users/kashy/OneDrive/Desktop/RentEase/VIVA_AND_PRESENTATION_GUIDE.md)** — Markdown format for command-line and text reading.

---

## Security Notes

- `DEBUG = True` is for **local development only**. Set `DEBUG = False` and configure `ALLOWED_HOSTS` for production.
- Generate a new secret key for production deployments via `get_random_secret_key()`.
- Static and media files are configured for local serving via `django.conf.urls.static`. For production, configure an Nginx / AWS S3 reverse proxy.

---

**RentEase — Luxury Property Rental Web Platform**
