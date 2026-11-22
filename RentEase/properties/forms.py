"""
Django Forms for RentEase.

Demonstrates:
- Django ModelForms
- Custom validation (clean methods)
- Form widgets and placeholders
- Field-level and cross-field validation
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Property, Booking, ContactMessage, Review


# --------------------------------------------------------------------------- #
#  Authentication Forms
# --------------------------------------------------------------------------- #

class RegisterForm(UserCreationForm):
    """
    Extended registration form.
    Adds first name, last name, and email on top of Django's built-in fields.
    """
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name',
            'class': 'form-input',
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name',
            'class': 'form-input',
            'autocomplete': 'family-name',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email address',
            'class': 'form-input',
            'autocomplete': 'email',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind/custom classes to the default username and password fields
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Choose a username',
            'class': 'form-input',
            'autocomplete': 'username',
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Create a password (min. 8 characters)',
            'class': 'form-input',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm your password',
            'class': 'form-input',
            'autocomplete': 'new-password',
        })

    def clean_email(self):
        """Ensure no two users share the same email address."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """
    Simple login form using Django's built-in authenticate().
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'class': 'form-input',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-input',
            'autocomplete': 'current-password',
        })
    )


# --------------------------------------------------------------------------- #
#  Property Form
# --------------------------------------------------------------------------- #

class PropertyForm(forms.ModelForm):
    """
    ModelForm for creating and editing a Property listing.
    The owner field is NOT included — it is set in the view from request.user.
    """

    class Meta:
        model = Property
        fields = [
            'title', 'description', 'location', 'rent',
            'property_type', 'bedrooms', 'bathrooms',
            'total_rooms', 'available_rooms',
            'amenities', 'image', 'is_available',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Spacious 3BHK Apartment in Chandigarh',
                'class': 'form-input',
            }),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe the property — surroundings, features, nearby amenities…',
                'class': 'form-input',
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'e.g. Sector 22, Chandigarh',
                'class': 'form-input',
            }),
            'rent': forms.NumberInput(attrs={
                'placeholder': 'Daily rent in ₹ (e.g. 2500)',
                'class': 'form-input',
                'min': '100',
            }),
            'property_type': forms.Select(attrs={'class': 'form-input'}),
            'bedrooms': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'max': '20',
            }),
            'bathrooms': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '20',
            }),
            'total_rooms': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '100',
                'placeholder': 'Total rentable rooms/units',
            }),
            'available_rooms': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'max': '100',
                'placeholder': 'Currently available rooms',
            }),
            'amenities': forms.TextInput(attrs={
                'placeholder': 'e.g. WiFi, Parking, AC, Lift, Security',
                'class': 'form-input',
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-file-input'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'rent': 'Rent per Day (₹)',
            'total_rooms': 'Total Rooms / Units',
            'available_rooms': 'Available Rooms',
        }
        help_texts = {
            'total_rooms': 'Total number of rentable rooms or units in this property.',
            'available_rooms': 'Rooms currently open for new bookings. Updates automatically on approve/checkout.',
        }

    def clean_rent(self):
        rent = self.cleaned_data.get('rent')
        if rent is not None and rent < 100:
            raise forms.ValidationError("Daily rent must be at least ₹100.")
        return rent

    def clean_bedrooms(self):
        bedrooms = self.cleaned_data.get('bedrooms')
        if bedrooms is not None and bedrooms > 20:
            raise forms.ValidationError("Bedroom count cannot exceed 20.")
        return bedrooms

    def clean_bathrooms(self):
        bathrooms = self.cleaned_data.get('bathrooms')
        if bathrooms is not None and bathrooms > 20:
            raise forms.ValidationError("Bathroom count cannot exceed 20.")
        return bathrooms

    def clean_available_rooms(self):
        available = self.cleaned_data.get('available_rooms')
        total = self.cleaned_data.get('total_rooms')
        if available is not None and total is not None:
            if available > total:
                raise forms.ValidationError("Available rooms cannot exceed total rooms.")
        return available

    def clean_image(self):
        """
        Validate that uploaded image is of an allowed type and within 5 MB.
        """
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if image.content_type not in allowed_types:
                raise forms.ValidationError(
                    "Only JPEG, PNG, and WebP images are accepted."
                )
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    "Image file size must not exceed 5 MB."
                )
        return image


# --------------------------------------------------------------------------- #
#  Booking Form
# --------------------------------------------------------------------------- #

class BookingForm(forms.ModelForm):
    """
    ModelForm for submitting a daily booking request.
    property and tenant are set in the view.
    Collects tenant contact, check-in, check-out dates, guest count, and message.
    """

    class Meta:
        model = Booking
        fields = [
            'tenant_full_name', 'tenant_contact',
            'start_date', 'end_date', 'guests',
            'message',
        ]
        widgets = {
            'tenant_full_name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'form-input',
                'autocomplete': 'name',
            }),
            'tenant_contact': forms.TextInput(attrs={
                'placeholder': 'e.g. +91 98765 43210',
                'class': 'form-input',
                'autocomplete': 'tel',
                'type': 'tel',
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
                'id': 'id_start_date',
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
                'id': 'id_end_date',
            }),
            'guests': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '50',
                'id': 'id_guests',
                'value': '1',
            }),
            'message': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional: tell the host about yourself or special requests.',
                'class': 'form-input',
            }),
        }
        labels = {
            'tenant_full_name': 'Your Full Name',
            'tenant_contact': 'Contact Number',
            'start_date': 'Check-in Date',
            'end_date': 'Check-out Date',
            'guests': 'Number of Guests',
            'message': 'Message to Host (optional)',
        }

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.property_obj = property_obj
        self.fields['tenant_full_name'].required = True
        self.fields['tenant_contact'].required = True
        self.fields['start_date'].required = True
        self.fields['end_date'].required = True
        self.fields['guests'].required = True

    def clean_tenant_contact(self):
        contact = self.cleaned_data.get('tenant_contact', '').strip()
        import re
        digits_only = re.sub(r'\D', '', contact)
        if len(digits_only) < 7:
            raise forms.ValidationError("Please enter a valid contact number (at least 7 digits).")
        if len(digits_only) > 15:
            raise forms.ValidationError("Contact number is too long (max 15 digits).")
        return contact

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < timezone.now().date():
            raise forms.ValidationError("Check-in date cannot be in the past.")
        return start_date

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')

        if self.property_obj and not self.property_obj.is_currently_available:
            self.add_error(None, "This property is currently booked and unavailable for new reservations.")

        if start_date and end_date:
            if end_date <= start_date:
                self.add_error('end_date', "Check-out date must be after check-in date.")
            elif self.property_obj:
                exclude_id = self.instance.pk if self.instance else None
                if not self.property_obj.is_available_for_dates(start_date, end_date, exclude_booking_id=exclude_id):
                    self.add_error(None, "The selected dates are already booked for this property. Please choose different dates.")

        return cleaned


# --------------------------------------------------------------------------- #
#  Contact Form
# --------------------------------------------------------------------------- #

class ContactForm(forms.ModelForm):
    """Simple contact form stored in the database."""

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'form-input',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'your@email.com',
                'class': 'form-input',
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': 'Subject',
                'class': 'form-input',
            }),
            'message': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Your message…',
                'class': 'form-input',
            }),
        }


# --------------------------------------------------------------------------- #
#  Review & Rating Form
# --------------------------------------------------------------------------- #

class ReviewForm(forms.ModelForm):
    """
    Form for verified tenants to submit or edit a rating and review.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={
                'class': 'form-input',
            }),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share your experience with the property, amenities, neighborhood, and host…',
                'class': 'form-input',
            }),
        }
        labels = {
            'rating': 'Your Rating',
            'comment': 'Review Comments (Optional)',
        }

