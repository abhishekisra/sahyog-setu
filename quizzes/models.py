from django.db import models
from django.conf import settings
from django.utils import timezone


class Quizzes(models.Model):

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    certificate_text = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="quiz/images", blank=True, null=True)
    logo_1 = models.ImageField(upload_to="quiz/authorities/logos")
    logo_2 = models.ImageField(upload_to="quiz/authorities/logos")
    # Authority 1
    authority1_name = models.CharField(max_length=255)
    authority1_designation = models.CharField(max_length=255)
    authority1_sign_image = models.ImageField(upload_to="quiz/authorities/signatures")
    authority2_name = models.CharField(max_length=255)
    authority2_designation = models.CharField(max_length=255)
    authority2_sign_image = models.ImageField(upload_to="quiz/authorities/signatures")
    quiz_time = models.IntegerField(default=0, blank=False, null=False)  # minutes
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # MyGov-style scheduling & attempt rules
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    questions_per_attempt = models.IntegerField(default=10)
    pass_threshold = models.IntegerField(default=60)
    one_attempt_only = models.BooleanField(default=True)
    leaderboard_public = models.BooleanField(default=False)

    @property
    def is_live(self):
        if not self.status:
            return False
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class Questions(models.Model):
    quiz = models.ForeignKey(Quizzes, on_delete=models.CASCADE, related_name="questions")
    question = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    OPTION_CHOICES = ((1, "Option 1"),(2, "Option 2"), (3, "Option 3"),(4, "Option 4"))
    correct_option = models.IntegerField(choices=OPTION_CHOICES)
    explanation = models.TextField(blank=True, default="")


class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quizzes, on_delete=models.CASCADE, related_name="attempts")
    # Populated at submit time; default 0 because the attempt row is now created
    # when the participant starts the quiz (see QuizTakeView), before a score exists.
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.quiz} ({self.score}/{self.total_questions})"


class QuestionResponse(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Questions, on_delete=models.SET_NULL, null=True)
    question_text_snapshot = models.TextField()
    selected_option = models.CharField(max_length=10)
    correct_option = models.CharField(max_length=10)
    is_correct = models.BooleanField(default=False)
    # Snapshotted for the same reason as question_text_snapshot: EditQuizView
    # deletes and recreates all Questions rows, which would otherwise orphan
    # this FK (on_delete=SET_NULL) and silently blank the explanation shown
    # in a past attempt's review.
    explanation_snapshot = models.TextField(blank=True, default="")

    def __str__(self):
        return f"attempt {self.attempt_id} - {self.question_text_snapshot[:40]}"

