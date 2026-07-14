from django.shortcuts import render

# Create your views here.
import json
from django.conf import settings
from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from .models import User
from .forms import SignupForm


def visitors(request):
    if request.user.is_authenticated:
        visitors = User.objects.filter(user_type = 2)
        return render(request, 'custom_admin/visitors.html', {'visitors': visitors})
    else:
        messages.error(request, "you have to login first")
        return redirect('adminLogin')


LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 15 * 60  # seconds


class SignupView(View):

    def get(self, request):
        return render(request, 'custom_admin/accounts/signup.html', {'form': SignupForm()})

    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, 'custom_admin/accounts/signup.html', {'form': form})


class LoginView(View):

    def get(self, request):
        return render(request, 'custom_admin/accounts/login.html', {'next': request.GET.get('next', '')})

    def post(self, request):
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next') or settings.LOGIN_REDIRECT_URL

        cache_key = f'login_attempts_{mobile}'
        attempts = cache.get(cache_key, 0)

        if attempts >= LOGIN_ATTEMPT_LIMIT:
            return render(request, 'custom_admin/accounts/login.html', {
                'error': "Too many failed attempts. Please try again after 15 minutes.",
                'next': next_url,
            })

        user = authenticate(request, username=mobile, password=password)
        if user is not None:
            cache.delete(cache_key)
            login(request, user)
            return redirect(next_url)

        cache.set(cache_key, attempts + 1, LOGIN_ATTEMPT_WINDOW)
        return render(request, 'custom_admin/accounts/login.html', {
            'error': "Incorrect mobile number or password.",
            'next': next_url,
        })


@method_decorator(csrf_exempt, name='dispatch')
class GoogleLoginView(View):
    """POST body: {"credential": "<Google ID token JWT>", "next": "<url>"}.

    Unlike apis.user() (the older React-SPA sync endpoint, which trusts
    client-submitted name/email/client_id as-is and never establishes a
    Django session), this verifies the ID token itself against Google's
    public keys server-side -- the client can't forge someone else's
    identity here, since only a token actually signed by Google for our
    GOOGLE_CLIENT_ID will pass verify_oauth2_token. That's what makes it
    safe to log the user in directly from this one call.
    """

    def post(self, request):
        try:
            body = json.loads(request.body or b'{}')
            token = body.get('credential', '')
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except Exception:
            return JsonResponse({'ok': False, 'error': 'invalid_token'}, status=400)

        sub = idinfo.get('sub', '')
        email = idinfo.get('email', '') if idinfo.get('email_verified') else ''
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        if not sub:
            return JsonResponse({'ok': False, 'error': 'invalid_token'}, status=400)

        user = User.objects.filter(google_sub=sub).first()
        if not user and email:
            # Same person already has a mobile+password account under this
            # (Google-verified) email -- link rather than create a duplicate.
            user = User.objects.filter(email=email).exclude(email='').first()
        if not user:
            parts = name.split(None, 1) if name else []
            user = User(
                username=f'google-{sub[:24]}',
                first_name=parts[0] if parts else '',
                last_name=parts[1] if len(parts) > 1 else '',
                user_type=2,
            )
            user.set_unusable_password()

        user.google_sub = sub
        user.name = user.name or name
        user.email = user.email or email
        user.profile_pic = picture or user.profile_pic
        user.save()

        login(request, user)
        return JsonResponse({
            'ok': True,
            'needsProfile': not bool(user.mobile),
            'next': body.get('next') or settings.LOGIN_REDIRECT_URL,
        })


class CompleteProfileView(View):
    """One short form shown only right after a FIRST Google sign-in with no
    mobile number on file yet -- collects the one field the mobile+password
    flow requires that Google never provides (mobile), plus optional DOB and
    a one-time geolocation capture. Existing accounts (mobile already set)
    never see this."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.mobile:
            return redirect(request.GET.get('next') or settings.LOGIN_REDIRECT_URL)
        return render(request, 'custom_admin/accounts/complete_profile.html', {
            'next': request.GET.get('next', ''),
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        mobile = request.POST.get('mobile', '').strip()
        dob = request.POST.get('date_of_birth', '').strip()
        lat = request.POST.get('latitude', '').strip()
        lng = request.POST.get('longitude', '').strip()
        next_url = request.POST.get('next') or settings.LOGIN_REDIRECT_URL

        errors = {}
        if not mobile.isdigit() or len(mobile) != 10:
            errors['mobile'] = "Please enter a valid 10-digit mobile number."
        elif User.objects.filter(mobile=mobile).exclude(id=request.user.id).exists():
            errors['mobile'] = "This mobile number is already registered."

        if errors:
            return render(request, 'custom_admin/accounts/complete_profile.html', {
                'errors': errors, 'next': next_url,
            })

        user = request.user
        user.mobile = mobile
        # Mobile becomes the canonical username once known, matching the
        # mobile+password signup convention -- but only if free (a
        # google-<sub> placeholder never collides with a real 10-digit one).
        if not User.objects.filter(username=mobile).exclude(id=user.id).exists():
            user.username = mobile
        if dob:
            user.date_of_birth = dob
        if lat and lng:
            try:
                user.latitude = float(lat)
                user.longitude = float(lng)
            except ValueError:
                pass
        user.save()
        return redirect(next_url)


class LogoutView(View):

    def get(self, request):
        logout(request)
        return redirect('login')

