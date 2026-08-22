from django.urls import path
from . import views

urlpatterns = [
    path('news-viewer/', views.news_finder, name='news_finder'),
]
