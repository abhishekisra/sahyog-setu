from django.db import models


class Language(models.Model):
    """One row per supported content language, independent of and separate
    from quizzes.models.Language (that table is untouched by this app --
    quiz already has its own working translation setup). Seeded via the
    seed_content_languages management command with all 22 languages in the
    Indian Constitution's Eighth Schedule. English is deliberately NOT a
    row here -- it's the base language living directly on each translatable
    model's own fields, never a translation."""
    code = models.CharField(max_length=10, primary_key=True)  # ISO 639-1 where one exists, e.g. 'hi', 'ta'
    name = models.CharField(max_length=50)          # English name, e.g. "Tamil"
    native_name = models.CharField(max_length=50)   # e.g. "தமிழ்"
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
