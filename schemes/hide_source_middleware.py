"""Never show the word "myScheme" on the public site (user rule, 2026-11-08).

Scheme text imported from myScheme sometimes says "applications will be
accepted through the myScheme platform", "signed in to myScheme", or prints
https://www.myscheme.gov.in/. The DB keeps the original text untouched
(the monthly check_myscheme_updates comparison depends on it, and "data
mat hatana"). This middleware rewrites only the VISIBLE text of public
HTML and JSON responses:

  * only text outside tags (href/src/attribute values are left alone, so
    links keep working) and never inside <script>/<style>;
  * JSON: every string value is processed the same way (scheme fields
    carry HTML), keys untouched;
  * /admin, /static, /media and non-HTML/JSON responses pass through.

Admin pages still say myScheme on purpose -- staff need to know the source.
"""
import json
import re

_SKIP = ("/admin", "/static", "/media", "/trainer", "/quiz-analytics")

_URL = re.compile(r"(?:https?://)?(?:www\.)?myscheme\.gov\.in[\w/.\-#?=&%]*", re.I)
_RULES = [
    (re.compile(r"\bthe\s+myscheme\s+(?:platform|portal|website)\b", re.I), "the online portal"),
    (re.compile(r"\bmyscheme\s+(?:platform|portal|website)\b", re.I), "online portal"),
    (re.compile(r"\bthe\s+myscheme\b", re.I), "the portal"),
    (re.compile(r"\bmyscheme\b", re.I), "the portal"),
]
_TAG_SPLIT = re.compile(r"(<script\b.*?</script\s*>|<style\b.*?</style\s*>|<!--.*?-->|<[^>]*>)", re.I | re.S)


def _url_sub(m):
    s = m.group(0)
    tail = ""
    while s and s[-1] in ".,;:)":
        tail = s[-1] + tail
        s = s[:-1]
    return "the official government portal" + tail


def clean_text(text):
    """Rewrite visible text in an HTML (or plain) string."""
    if not text or "myscheme" not in text.lower():
        return text
    parts = _TAG_SPLIT.split(text)
    for i in range(0, len(parts), 2):  # even indexes = text between tags
        seg = parts[i]
        if seg and "myscheme" in seg.lower():
            seg = _URL.sub(_url_sub, seg)
            for rx, rep in _RULES:
                seg = rx.sub(rep, seg)
            parts[i] = seg
    return "".join(parts)


def _walk(obj, key=None):
    if isinstance(obj, str):
        return obj if (key or "").startswith("myscheme") else clean_text(obj)
    if isinstance(obj, list):
        return [_walk(v, key) for v in obj]
    if isinstance(obj, dict):
        return {k: _walk(v, k) for k, v in obj.items()}
    return obj


class HideMySchemeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if request.path.startswith(_SKIP) or getattr(response, "streaming", False):
                return response
            ctype = response.get("Content-Type", "")
            if not ("text/html" in ctype or "application/json" in ctype):
                return response
            raw = response.content
            if b"myscheme" not in raw.lower():
                return response
            charset = response.charset or "utf-8"
            body = raw.decode(charset)
            if "application/json" in ctype:
                new = json.dumps(_walk(json.loads(body)), ensure_ascii=False)
            else:
                new = clean_text(body)
            if new != body:
                response.content = new.encode(charset)
                if response.has_header("Content-Length"):
                    response["Content-Length"] = str(len(response.content))
        except Exception:
            pass  # never break a page over wording
        return response
