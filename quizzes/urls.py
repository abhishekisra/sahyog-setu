from django.urls import path
from . import views

urlpatterns = [
    path('quiz/<int:quiz_id>/take/', views.QuizTakeView.as_view(), name='quiz_take'),
    path('quiz/<int:quiz_id>/submit/', views.quiz_submit, name='quiz_submit'),
    path('quiz/result/<int:pk>/', views.QuizResultView.as_view(), name='quiz_result'),
    path('quiz/<int:quiz_id>/leaderboard/', views.QuizLeaderboardView.as_view(), name='quiz_leaderboard'),
]
