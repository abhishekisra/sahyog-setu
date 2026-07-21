from django.urls import path
from . import views

urlpatterns = [
    path('yojana-khoj/', views.scheme_finder, name='scheme_finder'),
]
