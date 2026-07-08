from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

User = get_user_model()


class SignupForm(forms.Form):
    full_name = forms.CharField(label="पूरा नाम", max_length=150)
    mobile = forms.CharField(label="मोबाइल नंबर", max_length=10)
    password = forms.CharField(label="पासवर्ड", widget=forms.PasswordInput)
    email = forms.EmailField(label="ईमेल", required=False)

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile'].strip()
        if not mobile.isdigit() or len(mobile) != 10:
            raise ValidationError("कृपया 10 अंकों का सही मोबाइल नंबर दर्ज करें।")
        if User.objects.filter(username=mobile).exists():
            raise ValidationError("यह मोबाइल नंबर पहले से पंजीकृत है।")
        return mobile

    def clean_password(self):
        password = self.cleaned_data['password']
        password_validation.validate_password(password)
        return password

    def save(self):
        full_name = self.cleaned_data['full_name'].strip()
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
        )
        user.set_password(self.cleaned_data['password'])
        user.save()
        return user
