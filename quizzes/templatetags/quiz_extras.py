import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Admin-authored rich text (quiz description, etc.) -- allow enough tags for
# normal formatting (paragraphs, lists, bold/italic, links) but never
# script/style/iframe/on*-attributes, since this renders on a public page.
ALLOWED_TAGS = ["p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "a", "span"]
ALLOWED_ATTRS = {"a": ["href", "title", "target", "rel"]}


@register.filter(name="sanitize_html")
def sanitize_html(value):
    if not value:
        return ""
    cleaned = bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return mark_safe(cleaned)
