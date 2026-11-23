"""{% load ui %} ... {% ui "English text" %} -> the text in the page's language (context var `lang`),
from languages/ui_strings.json {English: {lang: text}}; English when that language has none yet.
2026-11-23: replaces the old {% if lang == 'hi' %}Hindi{% else %}English{% endif %} pairs so all 22
languages can be filled (Hindi kept exactly as it was)."""
import html
import os

from django import template

from languages import i18n_job as J

register = template.Library()
_CACHE = {"mtime": None, "data": {}}


def _strings():
    m = []
    for p in (J.ui_strings_path(), J.ui_machine_path()):
        try:
            m.append(os.path.getmtime(p))
        except OSError:
            m.append(None)
    if _CACHE["mtime"] != m:
        _CACHE["data"] = J.load_ui_strings()
        _CACHE["mtime"] = m
    return _CACHE["data"]


def ui_text(en, lang):
    key = " ".join(html.unescape(str(en)).split())
    entry = _strings().get(key) or {}
    return entry.get(lang) or key if lang and lang != "en" else key


@register.simple_tag(takes_context=True)
def ui(context, en):
    return ui_text(en, context.get("lang") or "en")
