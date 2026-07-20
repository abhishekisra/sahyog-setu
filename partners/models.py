from django.db import models
from django.contrib.auth.hashers import make_password, check_password

from quizzes.models import Quizzes


class Partner(models.Model):
    """An external organization given read-only access to one or more
    quizzes' analytics. Deliberately NOT built on Django's User/AbstractUser
    (see PartnerLoginView) -- a partner must never be able to authenticate
    against the admin/team login, or vice versa, and the two systems
    sharing django.contrib.auth's session would make that guarantee much
    harder to keep than two independent session keys."""
    name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, default="")
    username = models.CharField(max_length=150, unique=True)
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return f"{self.name} ({self.organization})" if self.organization else self.name


class PartnerQuizAccess(models.Model):
    """Many-to-many: which quiz(zes) a partner is allowed to see analytics
    for. Every partner-facing view must filter through this table -- never
    trust a quiz_id from the URL alone (see partners.views.get_partner_quiz)."""
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name="quiz_access")
    quiz = models.ForeignKey(Quizzes, on_delete=models.CASCADE, related_name="partner_access")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("partner", "quiz")]

    def __str__(self):
        return f"{self.partner} -> {self.quiz}"
