from django.urls import path
from . import views

urlpatterns = [
    path('important-portals-viewer/', views.portal_finder, name='portal_finder'),
    path('important-portals-viewer/search/', views.portal_search_light, name='portal_search_light'),
]
