"""Views for "Mere liye yojanayein" (/my-schemes/) and the save (star)
button used there and in the Scheme Viewer popup. See my_schemes.py."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from languages.utils import clean_language
from .models import Schemes, SavedScheme, SchemeProfile
from .my_schemes import person_from_user, match_schemes

# Allowed values for the optional profile form (same codes as the admin
# scheme form / /api/check-eligibility). Anything else is stored as None.
CHOICES = {
    "caste": {0, 1, 2, 3, 4},
    "marital_status": {0, 1, 2, 3, 4},
    "religion": {0, 1, 2, 3, 4, 5, 6, 7},
    "divyang": {0, 1},
    "area": {0, 1},
}
INCOME_MAX = 100_000_000


def _int_or_none(raw, allowed=None, maximum=None):
    raw = (raw or "").strip().replace(",", "")
    if not raw.isdigit():
        return None
    v = int(raw)
    if allowed is not None and v not in allowed:
        return None
    if maximum is not None and v > maximum:
        return None
    return v


def my_schemes(request):
    lang = clean_language(request.GET.get("lang", "en"))
    if not request.user.is_authenticated:
        return render(request, "custom_admin/schemes/my_schemes.html", {"lang": lang, "logged_out": True})

    user = request.user
    person = person_from_user(user)
    results = match_schemes(person, lang)
    saved_ids = list(SavedScheme.objects.filter(user=user).values_list("scheme_id", flat=True))
    saved = list(
        Schemes.objects.filter(id__in=saved_ids, status=1)
        .values("id", "title", "scheme_type", "state__state", "category__title")
    )
    order = {sid: i for i, sid in enumerate(saved_ids)}
    saved.sort(key=lambda s: order.get(s["id"], 0))
    saved = [{"id": s["id"], "title": (s["title"] or "").strip(), "category": s["category__title"] or "",
              "state": s["state__state"] or "", "central": s["scheme_type"] == 0} for s in saved]

    missing_account = [f for f, v in (("age", user.age), ("gender", user.gender), ("state", user.state_id)) if not v]
    extras_given = sum(1 for k in ("family_income", "caste", "marital_status", "religion", "divyang", "area")
                       if person[k] is not None)
    return render(request, "custom_admin/schemes/my_schemes.html", {
        "lang": lang,
        "logged_out": False,
        "person": person,
        "account": user,
        "missing_account": missing_account,
        "extras_given": extras_given,
        "results": results,
        "targeted_count": sum(1 for r in results if r["targeted"]),
        "total_count": len(results),
        "saved": saved,
        "saved_ids": saved_ids,
    })


@login_required
@require_POST
def my_schemes_profile(request):
    prof, _ = SchemeProfile.objects.get_or_create(user=request.user)
    prof.family_income = _int_or_none(request.POST.get("family_income"), maximum=INCOME_MAX)
    for field, allowed in CHOICES.items():
        setattr(prof, field, _int_or_none(request.POST.get(field), allowed=allowed))
    prof.save()
    lang = clean_language(request.POST.get("lang") or "en")
    return redirect("/my-schemes/" + (f"?lang={lang}" if lang != "en" else "") + "#ms-results")


@require_POST
def toggle_saved(request, scheme_id):
    """POST /my-schemes/save/<id>/  -> {"saved": true|false}. 401 when logged
    out so the page can send the person to the login screen instead."""
    if not request.user.is_authenticated:
        return JsonResponse({"login": True}, status=401)
    scheme = Schemes.objects.filter(id=scheme_id, status=1).first()
    if not scheme:
        return JsonResponse({"error": "not found"}, status=404)
    want = request.POST.get("saved")
    existing = SavedScheme.objects.filter(user=request.user, scheme=scheme)
    if want == "0" or (want is None and existing.exists()):
        existing.delete()
        return JsonResponse({"saved": False})
    SavedScheme.objects.get_or_create(user=request.user, scheme=scheme)
    return JsonResponse({"saved": True})


def saved_ids(request):
    """GET /my-schemes/saved-ids/ -> {"auth": bool, "ids": [...]}"""
    if not request.user.is_authenticated:
        return JsonResponse({"auth": False, "ids": []})
    ids = list(SavedScheme.objects.filter(user=request.user).values_list("scheme_id", flat=True))
    return JsonResponse({"auth": True, "ids": ids})
