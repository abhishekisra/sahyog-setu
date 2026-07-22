from django.urls import path
from . import views

urlpatterns = [
    path('important-documents-viewer/', views.document_finder, name='document_finder'),
    path('important-documents-viewer/search/', views.document_search_light, name='document_search_light'),
]
