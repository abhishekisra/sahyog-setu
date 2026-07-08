from django.contrib import admin

from .models import QuizAttempt, QuestionResponse


class ReadOnlyAdminMixin:

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("user", "quiz", "score", "total_questions", "percentage", "passed", "time_taken_seconds", "started_at", "completed_at")
    list_filter = ("quiz", "passed", "started_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__mobile")


@admin.register(QuestionResponse)
class QuestionResponseAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("attempt", "question_text_snapshot", "selected_option", "correct_option", "is_correct")
    list_filter = ("is_correct", "attempt__quiz")
    search_fields = ("question_text_snapshot", "attempt__user__username")
