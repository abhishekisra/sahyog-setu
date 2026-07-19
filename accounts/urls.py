from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('google-login/', views.GoogleLoginView.as_view(), name='google_login'),
    path('complete-profile/', views.CompleteProfileView.as_view(), name='complete_profile'),
    path('status/', views.auth_status, name='auth_status'),
    path('districts/', views.districts_for_state, name='districts_for_state'),
    path('check-availability/', views.check_availability, name='check_availability'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.ResetPasswordConfirmView.as_view(), name='reset_password_confirm'),
]
