from django.urls import path
from . import views

urlpatterns = [
    path('helplines-viewer/', views.helpline_finder, name='helpline_finder'),
]
