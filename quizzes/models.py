from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class Quizzes(models.Model):

    title = models.CharField(max_length=255)
    # null=True (not just blank=True) for the same reason as QuizAttempt.certificate_id
    # below: a unique field can't have more than one row storing '' -- auto-generated
    # in save() the first time a quiz is saved, so this is only ever null in between
    # migration and the next save.
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
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

    # Certificate (Part I)
    certificate_enabled = models.BooleanField(default=True)
    certificate_background = models.ImageField(upload_to="quiz/certificate_bg", blank=True, null=True)

    # Certificate layout nudging (Part J) -- lets an admin reposition the
    # name/score text vertically to fit a specific background image,
    # without needing a code change or template edit.
    name_top_pct = models.FloatField(default=42.0)
    score_top_pct = models.FloatField(default=64.0)

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

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "quiz"
            candidate = base
            suffix = 1
            while Quizzes.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                suffix += 1
                candidate = f"{base}-{suffix}"
            self.slug = candidate

        # Normalise logos/signatures on upload (Part H, Layer 1) -- only
        # touches a field when a NEW file was just assigned to it
        # (FieldFile._committed is False for an unsaved upload, True once
        # persisted), so re-saving the quiz for unrelated reasons never
        # re-normalises an already-normalised image.
        from .imaging import LOGO_BOX, SIGN_BOX, normalized_file, normalized_certificate_background, normalized_banner

        for field_name, box, strip_white in (
            ("logo_1", LOGO_BOX, False),
            ("logo_2", LOGO_BOX, False),
            ("authority1_sign_image", SIGN_BOX, True),
            ("authority2_sign_image", SIGN_BOX, True),
        ):
            f = getattr(self, field_name)
            if f and not f._committed:
                normalized = normalized_file(f.file, box, strip_white=strip_white, name_hint=field_name)
                f.save(normalized.name, normalized, save=False)

        # certificate_background gets its own normalize path (Part J) --
        # no thumbnailing, just orientation/format cleanup, since it's a
        # full-bleed print backdrop, not a small logo.
        bg = self.certificate_background
        if bg and not bg._committed:
            normalized_bg = normalized_certificate_background(bg.file)
            bg.save(normalized_bg.name, normalized_bg, save=False)

        # Banner (Part K) -- exif_transpose + re-encode as WEBP only, no
        # resize/crop here; the 16:10 ratio is already enforced at upload
        # time in the view, so the file arriving here is already correct.
        img = self.image
        if img and not img._committed:
            normalized_img = normalized_banner(img.file)
            img.save(normalized_img.name, normalized_img, save=False)

        super().save(*args, **kwargs)


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

    @property
    def options_list(self):
        return [(1, self.option_1), (2, self.option_2), (3, self.option_3), (4, self.option_4)]


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

    # The randomly-sampled question set for THIS attempt, fixed at creation.
    # Never read the question set from request.session -- gunicorn restarts,
    # session expiry, and a second browser tab all destroy session state
    # mid-quiz, but this row survives all three.
    question_ids = models.JSONField(default=list)

    # Certificate (Part I). null=True (not just blank=True) is required here:
    # a CharField that's `unique=True` can't have more than one row storing
    # '' -- most attempts never get a certificate, so unset must be NULL,
    # since MySQL allows many NULLs but not many empty-string duplicates
    # under a unique constraint.
    certificate_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    certificate_issued_at = models.DateTimeField(null=True, blank=True)

    # Demo/seed data marker -- lets the analytics dashboard demo without
    # polluting real numbers. Every analytics query excludes these by
    # default; a demo row can never issue a certificate or count against
    # one_attempt_only (see CertificateView, QuizTakeView).
    is_demo = models.BooleanField(default=False, db_index=True)

    # Where the participant came from (whatsapp/sms/facebook/email/qr/direct).
    # Always whitelist-validated before it ever reaches this field (see
    # quizzes.views.clean_source) -- it gets rendered back in the admin
    # analytics dashboard, so an unvalidated value would be an XSS vector.
    source = models.CharField(max_length=20, default="direct", db_index=True)

    # Enforces "only one LIVE attempt per (user, quiz)" -- what actually
    # stops two simultaneous taps on "Start Quiz" (or two open tabs)
    # from racing into two in-progress attempts. This is deliberately NOT a
    # Meta.UniqueConstraint(condition=Q(completed_at__isnull=True)): Django
    # accepts that declaration, but MySQL does not support unique
    # constraints with a condition (models.W036) -- the migration applies
    # "successfully" while silently creating no constraint at all, which is
    # worse than an obvious failure. This column is the portable
    # workaround: set to "<user_id>_<quiz_id>" while the attempt is live,
    # set back to NULL the moment it completes (see quiz_submit). A plain
    # UniqueConstraint on this column is fully supported by MySQL, and
    # MySQL (like every mainstream RDBMS) allows unlimited rows with NULL
    # in a unique-constrained column, so completed attempts simply drop out
    # of the uniqueness check instead of needing a real partial index.
    live_lock = models.CharField(max_length=64, unique=True, null=True, blank=True)

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

    class Meta:
        constraints = [
            # Users change their answer -- autosave must update_or_create,
            # never create, or a changed answer leaves a duplicate row
            # behind and the "most-failed questions" analytics goes garbage.
            # question=NULL rows (after an admin deletes the question later)
            # are exempt from this -- MySQL treats each NULL as distinct.
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="one_response_per_question",
            ),
        ]

    def __str__(self):
        return f"attempt {self.attempt_id} - {self.question_text_snapshot[:40]}"

