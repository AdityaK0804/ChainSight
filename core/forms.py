"""
ChainSight Forms
Django forms for user registration and data upload.
"""

from django import forms
from django.contrib.auth.models import User


class SignupStep1Form(forms.Form):
    """Step 1: Collect user credentials."""

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Alex Johnson'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'alex@company.com'})
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )
    confirm_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Passwords do not match.")
        email = cleaned.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return cleaned


class SignupStep2Form(forms.Form):
    """Step 2: Collect company / profile info."""

    ROLE_CHOICES = [
        ('', 'Select your role'),
        ('supply_chain_manager', 'Supply Chain Manager'),
        ('procurement', 'Procurement'),
        ('logistics', 'Logistics'),
        ('operations', 'Operations'),
        ('executive', 'Executive'),
        ('analyst', 'Analyst'),
        ('other', 'Other'),
    ]

    TEAM_SIZE_CHOICES = [
        ('', 'Select team size'),
        ('1-5', '1–5'),
        ('6-20', '6–20'),
        ('21-50', '21–50'),
        ('51-200', '51–200'),
        ('200+', '200+'),
    ]

    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Acme Logistics Inc.'})
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    team_size = forms.ChoiceField(choices=TEAM_SIZE_CHOICES)
    country = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'India'})
    )


class CSVUploadForm(forms.Form):
    """Form for validating CSV file upload."""

    file = forms.FileField()

    def clean_file(self):
        f = self.cleaned_data['file']
        if not f.name.endswith('.csv'):
            raise forms.ValidationError("Only .csv files are accepted.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File size must be under 10 MB.")
        return f
