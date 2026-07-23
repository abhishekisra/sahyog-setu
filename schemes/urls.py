from django.urls import path
from . import views

urlpatterns = [
    path('central-schemes-viewer/', views.central_category_finder, name='central_category_finder'),
    path('state-schemes-viewer/', views.state_category_finder, name='state_category_finder'),
    path('state-schemes-viewer/photo-credits/', views.state_photo_credits, name='state_photo_credits'),
    path('scheme-viewer/', views.scheme_finder, name='scheme_finder'),
    path('scheme-viewer/search/', views.scheme_search_light, name='scheme_search_light'),
    path('entrepreneurship/business-related-schemes-viewer/', views.business_related_scheme_finder, name='business_related_scheme_finder'),
    path('entrepreneurship/business-related-schemes-viewer/search/', views.business_related_scheme_search_light, name='business_related_scheme_search_light'),
]
