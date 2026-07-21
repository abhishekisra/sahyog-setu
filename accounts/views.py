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
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.urls import reverse
from .models import User
from .forms import SignupForm, ForgotPasswordForm, SetNewPasswordForm
from states.models import States, District
from occupations.models import Occupations


@staff_member_required(login_url="adminLogin")
def visitors(request):
    # Was request.user.is_authenticated only -- any logged-in QUIZ USER
    # (not just admin/staff) could reach this page and see every other
    # user's name/email/mobile/state/district, a real privacy gap. Now
    # gated the same way every other admin-only page in this codebase is.
    visitors = User.objects.filter(user_type=2).select_related('state', 'district', 'occupation').order_by('-id')
    return render(request, 'custom_admin/visitors.html', {'visitors': visitors})


LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 15 * 60  # seconds


class SignupView(View):

    def _context(self, form):
        return {
            'form': form,
            'states': States.objects.all().order_by('state'),
            'occupations': Occupations.objects.filter(status=1).order_by('title'),
        }

    def get(self, request):
        return render(request, 'custom_admin/accounts/signup.html', self._context(SignupForm()))

    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, 'custom_admin/accounts/signup.html', self._context(form))


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


class ForgotPasswordView(View):
    """Always renders the same generic "if that email is registered..."
    result regardless of whether the email actually matched a user --
    otherwise this endpoint would let anyone enumerate which emails have
    accounts here just by watching which ones get a different response."""

    def get(self, request):
        return render(request, 'custom_admin/accounts/forgot_password.html', {'form': ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse('reset_password_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                subject = "Reset your Sahyog Setu password"
                body = (
                    f"Hi {user.get_full_name() or user.username},\n\n"
                    f"Click the link below to reset your Sahyog Setu password. "
                    f"This link works only once.\n\n{reset_url}\n\n"
                    f"If you didn't request this, you can safely ignore this email "
                    f"— your password will stay unchanged.\n\n— Sahyog Setu Team"
                )
                try:
                    EmailMessage(subject=subject, body=body, to=[user.email]).send(fail_silently=False)
                except Exception:
                    pass  # send failure stays invisible -- same generic response either way
            return render(request, 'custom_admin/accounts/forgot_password.html', {
                'form': ForgotPasswordForm(), 'sent': True,
            })
        return render(request, 'custom_admin/accounts/forgot_password.html', {'form': form})


class ResetPasswordConfirmView(View):
    """uidb64/token pair follows Django's own PasswordResetConfirmView
    convention (same encode/decode + default_token_generator), just with
    templates matching this app's own design instead of the admin-styled
    built-in ones."""

    def _get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)
        valid = user is not None and default_token_generator.check_token(user, token)
        return render(request, 'custom_admin/accounts/reset_password_confirm.html', {
            'form': SetNewPasswordForm() if valid else None,
            'valid': valid,
        })

    def post(self, request, uidb64, token):
        user = self._get_user(uidb64)
        valid = user is not None and default_token_generator.check_token(user, token)
        if not valid:
            return render(request, 'custom_admin/accounts/reset_password_confirm.html', {'form': None, 'valid': False})

        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Your password has been reset. Please login with your new password.")
            return redirect('login')
        return render(request, 'custom_admin/accounts/reset_password_confirm.html', {'form': form, 'valid': True})


def auth_status(request):
    """GET-only, read-only JSON check of the current session's auth state.
    Used by the home page's injected Login/Register header links (no
    source access to that React SPA, so it can't read request.user
    server-side) to swap themselves for the logged-in user's name +
    a Logout link once authenticated, instead of always showing
    Login/Register even to someone who's already signed in."""
    if request.user.is_authenticated:
        # get_full_name() first: SignupForm.save() splits "Full Name" into
        # first_name/last_name (Django's built-in fields) but never touches
        # the separate .name field, so checking .name before mobile was
        # always empty for a mobile+password signup and fell straight
        # through to showing the mobile number instead of the name the
        # user actually typed in. Some older/admin-created accounts have
        # .name set with no first/last name instead, hence still checking
        # both rather than just switching which one to prefer.
        display_name = request.user.get_full_name() or request.user.name or request.user.mobile or "Account"
        return JsonResponse({
            "authenticated": True,
            "name": display_name,
        })
    return JsonResponse({"authenticated": False})


def check_availability(request):
    """GET ?field=mobile|email&value=<...> -- read-only lookup backing the
    signup form's live "an account already exists" hint. Deliberately
    reuses the exact same matching rules as SignupForm.clean_mobile /
    clean_email (see forms.py) so this can never say "available" for
    something that would actually fail at submit time, or vice versa.
    Empty/invalid input always reports not-taken rather than erroring --
    there's nothing to warn about yet while the user is still typing."""
    field = request.GET.get('field', '')
    value = request.GET.get('value', '').strip()

    if field == 'mobile':
        if not (value.isdigit() and len(value) == 10):
            return JsonResponse({"taken": False})
        taken = User.objects.filter(username=value).exists()
    elif field == 'email':
        if not value:
            return JsonResponse({"taken": False})
        taken = User.objects.filter(email__iexact=value).exclude(email='').exists()
    else:
        return JsonResponse({"taken": False})

    return JsonResponse({"taken": taken})


def districts_for_state(request):
    """GET ?state_id=<id> -- read-only lookup backing the signup form's
    State->District cascade. Returns [] (not an error) for a missing or
    non-numeric state_id so the frontend can treat every response the
    same way regardless of dropdown state."""
    state_id = request.GET.get('state_id', '')
    if not state_id.isdigit():
        return JsonResponse({"districts": []})
    rows = District.objects.filter(state_id=int(state_id)).order_by('name').values('id', 'name')
    return JsonResponse({"districts": list(rows)})

