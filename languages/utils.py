from .models import Language


def clean_language(raw):
    """Whitelist ?lang= against active Language rows -- 'en' is always valid
    without a DB row (it's the base/fallback text living on the content
    model's own fields, not a translation), anything else must be an active
    Language.code. Same reasoning as quizzes.views.clean_language, but
    against this app's own (separate) Language table."""
    if not raw or raw == "en":
        return "en"
    if Language.objects.filter(code=raw, is_active=True).exists():
        return raw
    return "en"


def available_languages_for(translation_queryset, field=None):
    """Only offer languages that actually have translated content for this
    specific object -- an active Language with zero real translation for it
    would silently fall back to English everywhere (see
    TranslatableMixin.field_for), which is a confusing, apparently-broken
    toggle to show at all.

    translation_queryset: the Translation rows for ONE content object, e.g.
        SchemeTranslation.objects.filter(scheme=scheme)
    field: optional -- if given, only counts a language when that specific
        field is non-blank (mirrors quizzes.views.available_languages_for's
        `.exclude(question_translations__question_text="")`); otherwise any
        translation row's mere existence counts.

    Returns (languages, translated_codes) -- same shape as
    quizzes.views.available_languages_for.
    """
    qs = translation_queryset.filter(language__is_active=True)
    if field:
        qs = qs.exclude(**{field: ""})
    translated_codes = list(qs.values_list("language__code", flat=True).distinct())
    languages = [{"code": "en", "name": "English", "native_name": "English"}] + [
        {"code": l.code, "name": l.name, "native_name": l.native_name}
        for l in Language.objects.filter(code__in=translated_codes)
    ]
    return languages, translated_codes
