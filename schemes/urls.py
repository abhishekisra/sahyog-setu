from django.urls import path
from . import views
from . import my_schemes_views

urlpatterns = [
    path('central-schemes-viewer/', views.central_category_finder, name='central_category_finder'),
    path('state-schemes-viewer/', views.state_category_finder, name='state_category_finder'),
    path('state-schemes-viewer/photo-credits/', views.state_photo_credits, name='state_photo_credits'),
    path('scheme-viewer/', views.scheme_finder, name='scheme_finder'),
    path('scheme-viewer/search/', views.scheme_search_light, name='scheme_search_light'),
    path('entrepreneurship/business-related-schemes-viewer/', views.business_related_scheme_finder, name='business_related_scheme_finder'),
    path('entrepreneurship/business-related-schemes-viewer/search/', views.business_related_scheme_search_light, name='business_related_scheme_search_light'),
    # "Mere liye yojanayein" (2026-11-06)
    path('my-schemes/', my_schemes_views.my_schemes, name='my_schemes'),
    path('my-schemes/profile/', my_schemes_views.my_schemes_profile, name='my_schemes_profile'),
    path('my-schemes/save/<int:scheme_id>/', my_schemes_views.toggle_saved, name='my_schemes_toggle_saved'),
    path('my-schemes/saved-ids/', my_schemes_views.saved_ids, name='my_schemes_saved_ids'),
]
