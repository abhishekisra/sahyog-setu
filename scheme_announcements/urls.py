from django.urls import path
from . import views

urlpatterns = [
    path('scheme-announcements-viewer/', views.scheme_announcement_finder, name='scheme_announcement_finder'),
    path('scheme-announcements-viewer/search/', views.scheme_announcement_search_light, name='scheme_announcement_search_light'),
]
