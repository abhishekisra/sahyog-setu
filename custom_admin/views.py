
import random
import secrets
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from accounts.EmailBackEnd import EmailBackEnd
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
import hmac
import time
from rest_framework import status
from accounts.models import User
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.templatetags.static import static
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.decorators import method_decorator
from django.db.models import Exists, OuterRef, Sum, Q, F, Subquery, Case, When, Value, FloatField, CharField

from occupations.models import Occupations
from schemes.models import Categories, Schemes
from important_documents.models import Important_Documents
from important_portals.models import Important_Portals
from scheme_announcements.models import Scheme_Announcements
from testimonials.models import Testimonials

from entrepreneurship.artificial_intelligence.models import Artificial_Intelligence
from entrepreneurship.business_plans.models import Business_Plans
from entrepreneurship.legal_registrations.models import Legal_Registrations
from entrepreneurship.marketing.models import Marketing
from entrepreneurship.organization_registrations.models import Organization_Registration
from helplines.models import Helplines

# 2026-10-19 (security audit): the admin login and the forgot-password OTP
# check had no attempt limit at all, so the admin password (or the 6-digit
# OTP, which also never expired) could be brute-forced. Same cache-counter
# pattern as accounts.views.LoginView uses for the public login.
ADMIN_LOGIN_ATTEMPT_LIMIT = 5
ADMIN_LOGIN_ATTEMPT_WINDOW = 15 * 60  # seconds
OTP_ATTEMPT_LIMIT = 5
OTP_TTL = 15 * 60  # seconds

@method_decorator(csrf_exempt, name='post')
class LoginView(View):
    def get(self, request):
         return render(request, 'custom_admin/login.html')


    def post(self, request):
        emailId = request.POST['emailId']
        password = request.POST['password']
        cache_key = f"admin_login_attempts_{emailId.strip().lower()}"
        attempts = cache.get(cache_key, 0)
        if attempts >= ADMIN_LOGIN_ATTEMPT_LIMIT:
            return render(request, 'custom_admin/login.html', {'error' : "Too many failed attempts. Please try again after 15 minutes."})
        user = EmailBackEnd().authenticate(request, username = emailId, password =password)
        if user is not None and user.user_type == 1:
            cache.delete(cache_key)
            login(request, user)
            return redirect('adminDashboard')
        cache.set(cache_key, attempts + 1, ADMIN_LOGIN_ATTEMPT_WINDOW)
        return render(request, 'custom_admin/login.html', {'error' : "Invalid email Id or password"})




def dashboard(request):
    # 2026-08-29 (full audit): every other admin view in this codebase checks
    # request.user.is_authenticated before rendering -- this one, the actual
    # /admin/dashboard landing page, never did. Anyone who knew or guessed
    # the URL could see the admin's aggregate content counts (schemes,
    # documents, testimonials, visitor count, etc.) with no login at all.
    if not request.user.is_authenticated:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
    occupations = len(Occupations.objects.all())
    categories = len(Categories.objects.all())
    state_schemes = len(Schemes.objects.filter(scheme_type = 1))
    central_schemes = len(Schemes.objects.filter(scheme_type = 0))
    important_documents = len(Important_Documents.objects.all())
    important_portals = len(Important_Portals.objects.all())
    scheme_announcements = len(Scheme_Announcements.objects.all())
    testimonials = len(Testimonials.objects.all())
    visitors = len(User.objects.filter(user_type = 2))
    artificial_intelligence = len(Artificial_Intelligence.objects.all())
    business_plans = len(Business_Plans.objects.all())
    legal_registrations = len(Legal_Registrations.objects.all())
    marketing = len(Marketing.objects.all())
    organization_registration = len(Organization_Registration.objects.all())
    helplines = len(Helplines.objects.all())
    return render(request, 'custom_admin/dashboard.html', {'organization_registration' : organization_registration, 'marketing' : marketing, 'legal_registrations': legal_registrations, 'business_plans' : business_plans, 'artificial_intelligence' : artificial_intelligence, 'occupations' : occupations, 'categories' : categories, 'state_schemes' : state_schemes, 'central_schemes' : central_schemes, 'important_documents' : important_documents, 'important_portals' : important_portals, 'scheme_announcements' : scheme_announcements, 'testimonials' : testimonials, 'visitors' : visitors, 'helplines' : helplines})





def resetPassword(request):
    # Admin-only "forgot password" entry page (unauthenticated -- if they
    # could log in they wouldn't need this). Was never reachable at all
    # before 2026-10-15: this view existed but had no urls.py path, and the
    # 3 AJAX endpoints below it (requestOtp/verifyOtp/changePassword) were
    # similarly unwired -- login.html's own "Forgot password? Reset" link
    # has 404'd since whenever that link was written.
    return render(request, 'custom_admin/reset-password/reset_password.html')


@csrf_exempt
def requestOtp(request):
    try:
        # user_type=1 -- this is the ADMIN forgot-password flow specifically
        # (resetPassword/login.html live under /admin/), so only an actual
        # admin account's email should be able to trigger a reset here, not
        # any citizen/trainer account that happens to share this endpoint's
        # code path. Without this a non-admin's email would also work,
        # which is harmless to THEM (resets only their own password) but is
        # the wrong flow for them to land in.
        user = User.objects.get(email=request.POST.get('email'), user_type=1)
        # secrets.choice (not random.choice) -- this OTP gates a real
        # password reset, so it needs a cryptographically secure source,
        # not Python's default Mersenne Twister PRNG (bandit B311, found
        # in the 2026-10-19 security scan).
        otp = ''.join((secrets.choice('1234567890') for i in range(6)))
        request.session['otp'] = otp
        request.session['otp_user_id'] = user.id
        request.session['otp_created'] = time.time()
        request.session['otp_fails'] = 0
        # otp_verified intentionally NOT set here -- verifyOtp is the only
        # place that may set it, and changePassword below now requires it.
        request.session.pop('otp_verified', None)
        subject = "Sahyog Setu Admin — Password Reset OTP"
        to_email = [user.email]
        logo_url = request.build_absolute_uri(static('custom_admin/images/logo-dark.png'))
        html_template = render_to_string("custom_admin/reset-password/otp-template.html",
            {'logo': logo_url, 'name': user.name or user.username, 'otp': otp})
        text_content = strip_tags(html_template)
        email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, to_email)
        email.attach_alternative(html_template, "text/html")
        email.send()
        return JsonResponse({'message': "OTP sent to registered Email", 'status': status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return JsonResponse({'message': "No admin account found with this email.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse({'message': "Something went wrong. Please try again later.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def verifyOtp(request):
    # .get() (not ['otp']) -- a visitor who opens step-2 directly (bookmarked
    # URL, back button after the session already expired, etc.) with no OTP
    # ever requested in THIS session used to raise an uncaught KeyError here
    # (500, not the "OTP Not Matched" message this flow is supposed to show).
    session_otp = request.session.get('otp')
    otp = request.POST.get('otp') or ''
    if session_otp and time.time() - request.session.get('otp_created', 0) > OTP_TTL:
        for k in ('otp', 'otp_user_id', 'otp_created', 'otp_fails'):
            request.session.pop(k, None)
        session_otp = None
    if session_otp and hmac.compare_digest(otp, session_otp):
        request.session.pop('otp_fails', None)
        request.session['otp_verified'] = True
        return JsonResponse({'message': "OTP Matched", 'status': status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    else:
        if session_otp:
            fails = request.session.get('otp_fails', 0) + 1
            request.session['otp_fails'] = fails
            if fails >= OTP_ATTEMPT_LIMIT:
                for k in ('otp', 'otp_user_id', 'otp_created', 'otp_fails'):
                    request.session.pop(k, None)
                return JsonResponse({'message': "Too many wrong attempts. Please request a new OTP.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({'message': "OTP Not Matched", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def changePassword(request):
    # Must come through verifyOtp first in THIS session -- previously a
    # request straight to this endpoint (e.g. replaying it from browser dev
    # tools) would succeed as long as a stale otp_user_id sat in the
    # session, with no check that the OTP step actually passed.
    if not request.session.get('otp_verified'):
        return JsonResponse({'message': "Please verify the OTP first.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    password = request.POST.get('password', '')
    confirm_password = request.POST.get('confirm_password', '')
    if len(password) < 6:
        return JsonResponse({'message': "Password must be at least 6 characters.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    if password != confirm_password:
        return JsonResponse({'message': "Passwords do not match.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(id=request.session.get('otp_user_id'), user_type=1)
        user.set_password(password)
        user.save()
        # One-time use -- clear so the same verified session can't silently
        # change the password again later without a fresh OTP.
        for k in ('otp', 'otp_user_id', 'otp_verified'):
            request.session.pop(k, None)
        return JsonResponse({'message': "Password changed successfully.", 'status': status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return JsonResponse({'message': "User doesn't exist", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        return JsonResponse({'message': "Something went wrong. Please try again later.", 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='post')
class ChangePasswordView(View):
    """Self-service 'Change Password' for an ALREADY logged-in admin --
    distinct from resetPassword/requestOtp/verifyOtp/changePassword above
    (that whole flow is for someone who is logged OUT and forgot their
    password, OTP-based). This one requires knowing the CURRENT password,
    same as any normal account-settings change-password page, and never
    logs the admin out of their current session (update_session_auth_hash --
    without it, Django's session auth hash check fails on the very next
    request after set_password() changes the password hash, silently
    bouncing the admin back to the login page right after they successfully
    changed their own password)."""

    def get(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        return render(request, 'custom_admin/change-password.html')

    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return render(request, 'custom_admin/change-password.html')
        if len(new_password) < 6:
            messages.error(request, "New password must be at least 6 characters.")
            return render(request, 'custom_admin/change-password.html')
        if new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
            return render(request, 'custom_admin/change-password.html')
        request.user.set_password(new_password)
        request.user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        messages.success(request, "Password changed successfully.")
        return render(request, 'custom_admin/change-password.html')


class LogoutView(View):

    def get(self, request):
        logout(request)
        return redirect('adminLogin')