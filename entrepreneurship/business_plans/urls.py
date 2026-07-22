from django.urls import path
from . import views

urlpatterns = [
    path('entrepreneurship/business-plans-viewer/', views.business_plan_finder, name='business_plan_finder'),
    path('entrepreneurship/business-plans-viewer/search/', views.business_plan_search_light, name='business_plan_search_light'),
]
