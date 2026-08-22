class TranslatableMixin:
    """Mix into any content model whose Translation model has a `translations`
    related_name FK back to it, and an FK to languages.Language. Generic
    replacement for the copy-pasted _translation()/*_for() boilerplate on
    quizzes.Questions -- one method pair covers every field on every
    translatable model in this app, instead of hand-writing a title_for(),
    description_for(), etc. per model.

    Usage:
        class Schemes(TranslatableMixin, models.Model):
            ...
        class SchemeTranslation(models.Model):
            scheme = models.ForeignKey(Schemes, on_delete=models.CASCADE,
                                        related_name="translations")
            language = models.ForeignKey(Language, on_delete=models.CASCADE)
            title = models.CharField(...)
            ...

        scheme.field_for("title", lang)  # -> translated title, or English
                                          #    scheme.title if blank/missing
    """

    def _translation(self, lang):
        if not lang or lang == "en":
            return None
        cached = getattr(self, "_prefetched_translations", None)
        if cached is not None:
            return next((t for t in cached if t.language_id == lang), None)
        return self.translations.filter(language_id=lang).first()

    def field_for(self, field, lang="en"):
        t = self._translation(lang)
        val = getattr(t, field, None) if t else None
        return val if val else getattr(self, field)
