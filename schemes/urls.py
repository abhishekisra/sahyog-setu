from django.urls import path
from . import views

urlpatterns = [
    path('scheme-viewer/', views.scheme_finder, name='scheme_finder'),
    path('scheme-viewer/search/', views.scheme_search_light, name='scheme_search_light'),
]
