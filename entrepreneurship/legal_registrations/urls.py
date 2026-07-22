from django.urls import path
from . import views

urlpatterns = [
    path('entrepreneurship/legal-registrations-viewer/', views.legal_registration_finder, name='legal_registration_finder'),
    path('entrepreneurship/legal-registrations-viewer/search/', views.legal_registration_search_light, name='legal_registration_search_light'),
]
