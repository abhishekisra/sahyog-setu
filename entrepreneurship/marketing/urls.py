from django.urls import path
from . import views

urlpatterns = [
    path('entrepreneurship/marketing-viewer/', views.marketing_finder, name='marketing_finder'),
    path('entrepreneurship/marketing-viewer/search/', views.marketing_search_light, name='marketing_search_light'),
]
