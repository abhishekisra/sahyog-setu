from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils import timezone

from states.models import States, District
from occupations.models import Occupations

User = get_user_model()


class SignupForm(forms.Form):
    full_name = forms.CharField(label="Full Name", max_length=150)
    mobile = forms.CharField(label="Mobile Number", max_length=10)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    email = forms.EmailField(label="Email", required=False)

    # Analytics-only demographic/location fields -- see accounts.models.User
    # for the field-level rationale (FKs so the state->district cascade and
    # occupation list stay backed by real, queryable data).
    gender = forms.ChoiceField(label="Gender", choices=User.GENDER_CHOICES)
    age = forms.IntegerField(label="Age", min_value=1, max_value=120)
    state = forms.ModelChoiceField(label="State", queryset=States.objects.all().order_by('state'))
    # queryset is narrowed to the posted state in __init__ below (mirrors
    # the client-side cascade) so a tampered/stale district_id from a
    # different state can never validate through.
    district = forms.ModelChoiceField(label="District", queryset=District.objects.none())
    occupation = forms.ModelChoiceField(
        label="Occupation", queryset=Occupations.objects.filter(status=1).order_by('title')
    )
    # Optional -- most registrants aren't affiliated with an NGO/SHG.
    ngo_shg_name = forms.CharField(label="NGO / SHG Name", max_length=255, required=False)

    # Required: rejected at the form level (not just hidden by the
    # `required` HTML attribute, which a direct POST could skip) so consent
    # is genuinely enforced server-side, not just a UI nicety.
    consent = forms.BooleanField(
        label="I agree to the Privacy Policy and Terms & Conditions",
        error_messages={"required": "Please agree to the Privacy Policy and Terms & Conditions to continue."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bind the District queryset to whatever state was actually posted
        # (falls back to an empty queryset -- and therefore a clean
        # validation error -- if state wasn't posted or isn't parseable,
        # rather than silently accepting any district id from any state).
        state_id = self.data.get('state') if self.is_bound else None
        if state_id:
            try:
                self.fields['district'].queryset = District.objects.filter(state_id=int(state_id)).order_by('name')
            except (TypeError, ValueError):
                pass

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile'].strip()
        if not mobile.isdigit() or len(mobile) != 10:
            raise ValidationError("Please enter a valid 10-digit mobile number.")
        if User.objects.filter(username=mobile).exists():
            raise ValidationError("This mobile number is already registered.")
        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exclude(email='').exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        password_validation.validate_password(password)
        return password

    def save(self):
        # .title() -- signup never normalized casing at all, so a name
        # typed "abhishek agrawal" or "RAVI KUMAR" was stored and shown
        # exactly as typed everywhere downstream (certificate, my-results,
        # Partner Portal, the injected home-page header). Certificates are
        # the one place this is genuinely visible/embarrassing, so it's
        # worth fixing at the source rather than only patching the
        # certificate renderer.
        full_name = self.cleaned_data['full_name'].strip().title()
        parts = full_name.split(None, 1)
        first_name = parts[0] if parts else ''
        last_name = parts[1] if len(parts) > 1 else ''
        mobile = self.cleaned_data['mobile']

        user = User(
            username=mobile,
            mobile=mobile,
            first_name=first_name,
            last_name=last_name,
            email=self.cleaned_data.get('email') or '',
            gender=self.cleaned_data['gender'],
            age=self.cleaned_data['age'],
            state=self.cleaned_data['state'],
            district=self.cleaned_data['district'],
            occupation=self.cleaned_data['occupation'],
            ngo_shg_name=self.cleaned_data.get('ngo_shg_name') or '',
            consent_accepted_at=timezone.now(),
        )
        user.set_password(self.cleaned_data['password'])
        user.save()
        return user


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="Email")

    def get_user(self):
        """Returns the matching active user, or None. Deliberately never
        raises/exposes whether the email is registered -- the view always
        shows the same generic "if that email exists..." message either
        way, so this isn't a form-level validation error (that would leak
        registration status through the error message itself)."""
        email = self.cleaned_data.get('email', '').strip()
        return User.objects.filter(email__iexact=email).exclude(email='').first()


class SetNewPasswordForm(forms.Form):
    password = forms.CharField(label="New Password", widget=forms.PasswordInput)
    password_confirm = forms.CharField(label="Confirm New Password", widget=forms.PasswordInput)

    def clean_password(self):
        password = self.cleaned_data['password']
        password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') and cleaned.get('password_confirm') and cleaned['password'] != cleaned['password_confirm']:
            raise ValidationError("Passwords do not match.")
        return cleaned
