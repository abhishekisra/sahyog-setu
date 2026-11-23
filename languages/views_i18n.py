"""Token-protected batch exchange for the Colab translation notebook (see languages/i18n_job.py).
GET  /i18n-job/<token>/<job>/manifest.json      job size + languages
GET  /i18n-job/<token>/<job>/chunk/<n>.json     one batch of English segments
GET  /i18n-job/<token>/<job>/done.json          {lang: [batch numbers already received]} (lets Colab resume)
POST /i18n-job/<token>/<job>/result/<lang>/<n>  {key: translation} for that batch
GET  /i18n-job/<token>/notebook.ipynb           the notebook itself, token filled in
The token lives in JOB_ROOT/.token (owner sahyog, 0600). Nothing here touches the database."""
import hmac
import json
import os
import re

from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import i18n_job as J

_JOB = re.compile(r"^(core|schemes)$")


def _token_ok(token):
    try:
        with open(os.path.join(J.JOB_ROOT, ".token")) as f:
            real = f.read().strip()
    except OSError:
        return False
    return bool(real) and hmac.compare_digest(str(token), real)


def _guard(token, job=None):
    if not _token_ok(token) or (job is not None and not _JOB.match(job)):
        raise Http404()


def manifest(request, token, job):
    _guard(token, job)
    p = os.path.join(J.job_dir(job), "manifest.json")
    if not os.path.exists(p):
        raise Http404()
    with open(p, encoding="utf-8") as f:
        return JsonResponse(json.load(f))


def chunk(request, token, job, n):
    _guard(token, job)
    p = os.path.join(J.job_dir(job), f"chunk_{int(n):04d}.json")
    if not os.path.exists(p):
        raise Http404()
    with open(p, "rb") as f:
        return HttpResponse(f.read(), content_type="application/json; charset=utf-8")


def done(request, token, job):
    _guard(token, job)
    out = {}
    rd = os.path.join(J.job_dir(job), "results")
    if os.path.isdir(rd):
        for lang in os.listdir(rd):
            out[lang] = sorted(int(f[6:10]) for f in os.listdir(os.path.join(rd, lang)) if f.startswith("chunk_") and f.endswith(".json"))
    return JsonResponse(out)


@csrf_exempt
@require_http_methods(["POST"])
def result(request, token, job, lang, n):
    _guard(token, job)
    if lang not in J.IT2_CODES:
        raise Http404()
    src = os.path.join(J.job_dir(job), f"chunk_{int(n):04d}.json")
    if not os.path.exists(src):
        raise Http404()
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "bad json"}, status=400)
    with open(src, encoding="utf-8") as f:
        keys = {it["k"] for it in json.load(f)}
    if not isinstance(data, dict) or not data or not set(data) <= keys \
            or not all(isinstance(v, str) and len(v) <= 20000 for v in data.values()):
        return JsonResponse({"ok": False, "error": "batch does not match"}, status=400)
    d = os.path.join(J.job_dir(job), "results", lang)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"chunk_{int(n):04d}.json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return JsonResponse({"ok": True, "saved": len(data), "of": len(keys)})


def notebook(request, token):
    _guard(token)
    p = os.path.join(os.path.dirname(__file__), "colab", "sahyog_translate.ipynb")
    with open(p, encoding="utf-8") as f:
        nb = f.read().replace("__SAHYOG_TOKEN__", token)
    resp = HttpResponse(nb, content_type="application/x-ipynb+json")
    resp["Content-Disposition"] = 'attachment; filename="sahyog_translate.ipynb"'
    resp["Cache-Control"] = "no-store"
    return resp


def site_languages(request):
    """Public: the languages visitors can pick (English + every language switched on in BOTH lists).
    Used by the homepage header now that Google Translate is gone (user 2026-11-23)."""
    from quizzes.models import Language as QuizLanguage

    from .models import Language as ContentLanguage
    on = set(QuizLanguage.objects.filter(is_active=True).values_list("code", flat=True))
    rows = [{"code": "en", "name": "English"}] + [
        {"code": l.code, "name": l.native_name} for l in ContentLanguage.objects.filter(is_active=True) if l.code in on]
    resp = JsonResponse({"languages": rows})
    resp["Cache-Control"] = "public, max-age=300"
    return resp
