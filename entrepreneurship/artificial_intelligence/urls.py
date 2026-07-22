from django.urls import path
from . import views

urlpatterns = [
    path('entrepreneurship/artificial-intelligence-viewer/', views.artificial_intelligence_finder, name='artificial_intelligence_finder'),
    path('entrepreneurship/artificial-intelligence-viewer/search/', views.artificial_intelligence_search_light, name='artificial_intelligence_search_light'),
]
