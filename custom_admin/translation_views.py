"""Generic translation admin views, shared by every content app (schemes,
helplines, important_portals, etc.) -- replaces what would otherwise be a
near-duplicate TranslationsView/EditTranslationView pair per app, following
the exact same pattern quizzes.views.QuizTranslationsView/EditTranslationView
already established, just parameterized instead of hand-written per model.

All 15 content models this covers are FLAT (no nested child rows like
Quizzes->Questions), so a single generic pair works for all of them --
subclass and set the class attributes below, no other code needed per app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.db import transaction

from languages.models import Language


class TranslationsPickerView(View):
    """Picker page: one row per active Language, showing how many of this
    object's translatable fields already have a translation, and a link
    into the paired EditTranslationView for that language. Subclass and set:
    model, translation_model, fk_name (translation_model's FK field name
    back to `model`), fields (translation_model field names used for
    completeness), list_url_name, edit_url_name."""
    model = None
    translation_model = None
    fk_name = None
    fields = []
    object_label = "title"
    list_url_name = None
    list_label = "Items"
    edit_url_name = None
    template_name = "custom_admin/translations/picker.html"

    def get(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        obj = get_object_or_404(self.model, id=id)
        by_lang = {
            t.language_id: t
            for t in self.translation_model.objects.filter(**{self.fk_name: obj})
        }

        languages = list(Language.objects.filter(is_active=True))
        for lang in languages:
            t = by_lang.get(lang.code)
            lang.translated_count = sum(1 for f in self.fields if t and getattr(t, f, ""))
            lang.field_count = len(self.fields)
            lang.is_done = bool(self.fields) and lang.translated_count == lang.field_count

        return render(request, self.template_name, {
            "obj": obj,
            "object_label": getattr(obj, self.object_label, ""),
            "languages": languages,
            "list_url_name": self.list_url_name,
            "list_label": self.list_label,
            "edit_url_name": self.edit_url_name,
        })


class EditTranslationView(View):
    """Add/edit the translation of one object's fields into one language.
    English itself is never edited here -- it's shown read-only alongside
    each field purely as a reference, and lives on the base model row, not
    a translation row. Leaving every field blank removes any existing
    translation instead of saving an empty row, so a half-started
    translation never masquerades as a finished one in the picker's
    progress count. Subclass and set: model, translation_model, fk_name,
    fields (list of (name, label, widget) tuples, widget in
    ("text", "textarea")), picker_url_name."""
    model = None
    translation_model = None
    fk_name = None
    fields = []
    object_label = "title"
    picker_url_name = None
    template_name = "custom_admin/translations/edit.html"

    def get(self, request, id, lang):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        obj = get_object_or_404(self.model, id=id)
        language = get_object_or_404(Language, code=lang, is_active=True)
        translation = self.translation_model.objects.filter(
            **{self.fk_name: obj, "language": language}
        ).first()

        rows = [
            (name, label, widget, getattr(obj, name, ""),
             getattr(translation, name, "") if translation else "")
            for name, label, widget in self.fields
        ]

        return render(request, self.template_name, {
            "obj": obj,
            "object_label": getattr(obj, self.object_label, ""),
            "language": language,
            "rows": rows,
            "picker_url_name": self.picker_url_name,
        })

    def post(self, request, id, lang):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        obj = get_object_or_404(self.model, id=id)
        language = get_object_or_404(Language, code=lang, is_active=True)

        try:
            with transaction.atomic():
                values = {name: (request.POST.get(name) or "").strip() for name, _, _ in self.fields}
                if any(values.values()):
                    self.translation_model.objects.update_or_create(
                        **{self.fk_name: obj, "language": language},
                        defaults=values,
                    )
                else:
                    self.translation_model.objects.filter(
                        **{self.fk_name: obj, "language": language}
                    ).delete()
            messages.success(request, f"{language.name} translation saved.")
        except Exception as e:
            print("Translation Save Error:", e)
            messages.error(request, "Something went wrong while saving the translation.")

        return redirect(self.picker_url_name, id=obj.id)
