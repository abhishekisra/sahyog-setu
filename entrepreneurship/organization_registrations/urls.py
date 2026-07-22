from django.urls import path
from . import views

urlpatterns = [
    path('entrepreneurship/organization-registrations-viewer/', views.organization_registration_finder, name='organization_registration_finder'),
    path('entrepreneurship/organization-registrations-viewer/search/', views.organization_registration_search_light, name='organization_registration_search_light'),
]
