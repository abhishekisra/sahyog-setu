from django.urls import path
from . import views

urlpatterns = [
    path('quiz/<int:quiz_id>/take/', views.QuizTakeView.as_view(), name='quiz_take'),
    path('quiz/<int:quiz_id>/submit/', views.quiz_submit, name='quiz_submit'),
    path('quiz/result/<int:pk>/', views.QuizResultView.as_view(), name='quiz_result'),
    path('quiz/<int:quiz_id>/leaderboard/', views.QuizLeaderboardView.as_view(), name='quiz_leaderboard'),
    path('quiz/certificate/<int:pk>/', views.CertificateView.as_view(), name='quiz_certificate'),
    path('certificate/verify/<str:cert_id>/', views.verify_certificate, name='verify_certificate'),
    path('quiz-analytics/', views.QuizAnalyticsView.as_view(), name='quiz_analytics'),
    path('quiz-analytics/export/', views.quiz_analytics_export, name='quiz_analytics_export'),
    path('my-results/', views.MyResultsView.as_view(), name='my_results'),
    # slug routes last -- quiz/<slug>/ is a single path segment, so it can't
    # structurally collide with the multi-segment routes above (quiz/<id>/take/,
    # quiz/certificate/<pk>/, etc), but keeping it last is the clearest order.
    path('quiz/<slug:slug>/qr/', views.quiz_qr_code, name='quiz_qr'),
    path('quiz/<slug:slug>/', views.QuizLandingView.as_view(), name='quiz_landing'),
]
