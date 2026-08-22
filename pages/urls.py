from django.urls import path
from . import views

urlpatterns = [
    path('pages-viewer/', views.page_finder, name='page_finder'),
    path('pages-viewer/<int:id>/', views.page_detail, name='page_detail'),
]
