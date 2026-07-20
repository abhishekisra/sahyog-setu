from django.urls import path

from . import views

# Included at the project root with NO prefix (see SAHYOG_SETU_ADMIN/urls.py)
# specifically so /partner-login and /partner-logout exist as exact,
# unprefixed routes -- every other route here is explicitly given its own
# partner/... prefix instead, since a bare quiz/<id>/... here would
# otherwise collide with quizzes.urls' own /quiz/<id>/... routes (both
# included at the project root).
urlpatterns = [
    path("partner-login/", views.PartnerLoginView.as_view(), name="partner_login"),
    path("partner-logout/", views.PartnerLogoutView.as_view(), name="partner_logout"),
    path("partner/", views.partner_quiz_select, name="partner_quiz_select"),

    path("partner/quiz/<int:quiz_id>/", views.partner_overview, name="partner_overview"),
    path("partner/quiz/<int:quiz_id>/participants/", views.partner_participants, name="partner_participants"),
    path("partner/quiz/<int:quiz_id>/participants/export/", views.partner_participants_export, name="partner_participants_export"),
    path("partner/quiz/<int:quiz_id>/participants/<int:attempt_id>/", views.partner_attempt_detail, name="partner_attempt_detail"),
    path("partner/quiz/<int:quiz_id>/regions/", views.partner_regions, name="partner_regions"),
    path("partner/quiz/<int:quiz_id>/questions/", views.partner_questions, name="partner_questions"),
]
