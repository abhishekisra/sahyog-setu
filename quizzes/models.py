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

    # Certificate design (Part K) -- color/texture/logo-position controls
    # for the built-in background (ignored when certificate_background is
    # uploaded, same as name_top_pct/score_top_pct above). Defaults match
    # the values that were hardcoded in quizzes/cert_image.py and this
    # page's own SVG before this field existed, so an existing quiz's
    # certificate doesn't change unless an admin actually edits these.
    certificate_accent_color = models.CharField(max_length=7, default="#C8A951")
    certificate_name_color = models.CharField(max_length=7, default="#1B4332")
    certificate_paper_color = models.CharField(max_length=7, default="#FAF8EF")
    CERTIFICATE_PATTERN_CHOICES = [("classic", "Classic (guilloche + medallion)"), ("plain", "Plain (solid color, no pattern)")]
    certificate_pattern = models.CharField(max_length=10, choices=CERTIFICATE_PATTERN_CHOICES, default="classic")
    logo1_x_pct = models.FloatField(default=14.0)
    logo1_y_pct = models.FloatField(default=11.0)
    logo2_x_pct = models.FloatField(default=86.0)
    logo2_y_pct = models.FloatField(default=11.0)

    # Certificate design (Part L) -- border style, title color, corner
    # decoration on/off (previously tied to certificate_pattern, now its
    # own independent toggle), and a name-font choice. certificate_pattern
    # still controls the guilloche texture/medallion wash; corners no
    # longer ride along with it.
    CERTIFICATE_BORDER_CHOICES = [
        ("triple", "Triple line (classic)"),
        ("double", "Double line"),
        ("single", "Single line"),
    ]
    certificate_border_style = models.CharField(max_length=10, choices=CERTIFICATE_BORDER_CHOICES, default="triple")
    certificate_title_color = models.CharField(max_length=7, default="#111111")
    certificate_corners_enabled = models.BooleanField(default=True)
    CERTIFICATE_NAME_FONT_CHOICES = [
        ("script", "Script (cursive)"),
        ("serif", "Elegant serif"),
        ("bold", "Bold serif"),
    ]
    certificate_name_font = models.CharField(max_length=10, choices=CERTIFICATE_NAME_FONT_CHOICES, default="script")

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

    def _translation(self, lang):
        if not lang or lang == "en":
            return None
        # .translations is prefetched with to_attr="_prefetched_translations"
        # in the hot paths (QuizLandingView, QuizTakeView) precisely so this
        # never issues a query per quiz/question in a loop -- falls back to
        # a real query here only for code paths that didn't prefetch (e.g.
        # the admin edit form loading a single quiz).
        cached = getattr(self, "_prefetched_translations", None)
        if cached is not None:
            return next((t for t in cached if t.language_id == lang), None)
        return self.translations.filter(language_id=lang).first()

    def title_for(self, lang="en"):
        t = self._translation(lang)
        return (t.title if t and t.title else self.title)

    def description_for(self, lang="en"):
        t = self._translation(lang)
        return (t.description if t and t.description else self.description)


class Language(models.Model):
    """One row per supported language. Seeded via the seed_languages
    management command with English + all 22 languages in the Indian
    Constitution's Eighth Schedule -- 'code' is the field Questions/Quizzes
    translations and QuizAttempt.language key off, kept as a plain string
    (not a FK to this table) on those so a Language row can be deactivated
    or even removed later without a cascading delete touching real
    attempt/translation history."""
    code = models.CharField(max_length=10, primary_key=True)  # ISO 639-1 where one exists, e.g. 'hi', 'ta'
    name = models.CharField(max_length=50)          # English name, e.g. "Tamil"
    native_name = models.CharField(max_length=50)   # e.g. "தமிழ்"
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


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

    def _translation(self, lang):
        if not lang or lang == "en":
            return None
        cached = getattr(self, "_prefetched_translations", None)
        if cached is not None:
            return next((t for t in cached if t.language_id == lang), None)
        return self.translations.filter(language_id=lang).first()

    def text_for(self, lang="en"):
        t = self._translation(lang)
        return (t.question_text if t and t.question_text else self.question)

    def explanation_for(self, lang="en"):
        t = self._translation(lang)
        return (t.explanation if t and t.explanation else self.explanation)

    def options_for(self, lang="en"):
        """Same shape as options_list (kept as the untouched, pre-existing
        no-arg property above -- two live call sites already use it as a
        property, not a method) but language-aware, falling back to English
        per-option whenever that specific option's translation is blank."""
        t = self._translation(lang)
        if t:
            return [
                (1, t.option_1 or self.option_1),
                (2, t.option_2 or self.option_2),
                (3, t.option_3 or self.option_3),
                (4, t.option_4 or self.option_4),
            ]
        return self.options_list


class QuizTranslation(models.Model):
    quiz = models.ForeignKey(Quizzes, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="quiz_translations")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("quiz", "language")]


class QuestionTranslation(models.Model):
    question = models.ForeignKey(Questions, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="question_translations")
    question_text = models.TextField(blank=True, default="")
    option_1 = models.CharField(max_length=255, blank=True, default="")
    option_2 = models.CharField(max_length=255, blank=True, default="")
    option_3 = models.CharField(max_length=255, blank=True, default="")
    option_4 = models.CharField(max_length=255, blank=True, default="")
    explanation = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("question", "language")]


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

    # Language the participant chose at Start Quiz -- 'en' or a Language.code
    # (see clean_language() in views.py, which validates against active
    # Language rows before this is ever set, same pattern as source/
    # clean_source above). Not a FK to Language: fixed for the life of the
    # attempt so the review/certificate screens stay consistent with what
    # was actually shown during the attempt even if a Language row is later
    # deactivated or a translation edited, and a plain string means neither
    # of those admin actions ever has to worry about attempt history.
    language = models.CharField(max_length=10, default="en")

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
    # null=True, not auto_now_add: added after this table already had real
    # rows, and auto_now_add would have needed a backfill default for all of
    # them anyway. Set explicitly in quiz_answer() at answer time instead --
    # per-question time-taken (Partner Portal's question-wise view) is then
    # this minus the PREVIOUS response's answered_at (or attempt.started_at
    # for the first question), so it's only ever available for attempts
    # answered after this field existed; older ones show "N/A" rather than
    # a fabricated number.
    answered_at = models.DateTimeField(null=True, blank=True)
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

