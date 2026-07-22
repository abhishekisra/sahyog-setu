from django.urls import path
from . import views

urlpatterns = [
    path('entrepreneurship-viewer/', views.entrepreneurship_finder, name='entrepreneurship_finder'),
]
