from django.urls import path
from . import views

urlpatterns = [
    path('scheme-eligibility/', views.scheme_finder, name='scheme_finder'),
]
