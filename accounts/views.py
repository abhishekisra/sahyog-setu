from django.shortcuts import render

# Create your views here.
from django.conf import settings
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
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


class LogoutView(View):

    def get(self, request):
        logout(request)
        return redirect('login')

