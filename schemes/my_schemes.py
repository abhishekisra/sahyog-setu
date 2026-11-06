"""
"Mere liye yojanayein" (/my-schemes/, 2026-11-06).

Matches every active scheme against one participant: the signup fields on
accounts.User (age, gender, state, occupation) plus the optional extras in
SchemeProfile. Same rules as /api/check-eligibility (schemes.apis
.checkEligibility): a field the person hasn't told us never excludes a
scheme, an untagged area/occupation matches everyone, income_max 0 = no cap.

Most imported schemes are tagged "everyone" on every field (e.g. 4,449 of
4,653 have scheme_for "0,1,2"), so plain filtering says "700+ schemes for
you" to nearly everybody. On top of the filter, each scheme gets a score
for every way it is AIMED at this person (women-only, SC/ST, their state,
their occupation...) and the reasons are returned so the page can show
*why* a scheme was picked.
"""
from django.db.models import Q

from .models import Schemes, SchemeTranslation, Scheme_Occupations, Scheme_Areas, SchemeProfile

GENDER_CODE = {"male": 0, "female": 1, "other": 2}
FULL = {
    "scheme_for": {0, 1, 2},
    "castes": {0, 1, 2, 3, 4},
    "marital_status": {0, 1, 2, 3, 4},
    "religions": {0, 1, 2, 3, 4, 5, 6, 7},
}
TARGETED_MIN_SCORE = 2

# Reason labels shown as chips: key -> (en, hi)
REASONS = {
    "state": ("Your state", "आपके राज्य की"),
    "women": ("For women", "महिलाओं के लिए"),
    "men": ("For men", "पुरुषों के लिए"),
    "trans": ("For transgender persons", "ट्रांसजेंडर व्यक्तियों के लिए"),
    "caste": ("For your social category", "आपकी सामाजिक श्रेणी के लिए"),
    "marital": ("For your marital status", "आपकी वैवाहिक स्थिति के लिए"),
    "religion": ("For your community", "आपके समुदाय के लिए"),
    "divyang": ("For persons with disability", "दिव्यांगजन के लिए"),
    "occupation": ("For your occupation", "आपके व्यवसाय के लिए"),
    "area": ("For your area (rural/urban)", "आपके क्षेत्र (ग्रामीण/शहरी) के लिए"),
    "age": ("For your age group", "आपके आयु वर्ग के लिए"),
    "income": ("For your income level", "आपकी आय के स्तर के लिए"),
}


def _codes(csv):
    out = set()
    for part in (csv or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def person_from_user(user):
    """The facts we know about this person, from the account + SchemeProfile."""
    prof = SchemeProfile.objects.filter(user=user).first()
    return {
        "age": user.age,
        "gender": GENDER_CODE.get((user.gender or "").lower()),
        "state_id": user.state_id,
        "occupation_id": user.occupation_id,
        "family_income": prof.family_income if prof else None,
        "caste": prof.caste if prof else None,
        "marital_status": prof.marital_status if prof else None,
        "religion": prof.religion if prof else None,
        "divyang": prof.divyang if prof else None,
        "area": prof.area if prof else None,
    }


def match_schemes(person, lang="en"):
    """Returns a list of dicts sorted best-first:
    {id, title, category, state, central, score, reasons:[label,...], targeted}"""
    p = person
    qs = Schemes.objects.filter(status=1)
    if p["state_id"]:
        qs = qs.filter(Q(scheme_type=0) | Q(scheme_type=1, state_id=p["state_id"]))
    else:
        qs = qs.filter(scheme_type=0)
    if p["age"] is not None:
        qs = qs.filter(age_min__lte=p["age"], age_max__gte=p["age"])
    if p["family_income"] is not None:
        qs = qs.filter(income_min__lte=p["family_income"]).filter(
            Q(income_max__gte=p["family_income"]) | Q(income_max=0))
    if p["divyang"] == 1:          # not a person with disability
        qs = qs.exclude(divyang=0)  # schemes ONLY for divyangjan

    rows = list(qs.values("id", "title", "scheme_type", "state__state", "category__title",
                          "scheme_for", "castes", "marital_status", "religions", "divyang",
                          "age_min", "age_max", "income_max"))
    ids = [r["id"] for r in rows]

    occ_tags, area_tags = {}, {}
    for sid, oid in Scheme_Occupations.objects.filter(scheme_id__in=ids).values_list("scheme_id", "occupation_id"):
        occ_tags.setdefault(sid, set()).add(oid)
    for sid, a in Scheme_Areas.objects.filter(scheme_id__in=ids).values_list("scheme_id", "area"):
        area_tags.setdefault(sid, set()).add(a)

    titles = {}
    if lang and lang != "en":
        for sid, t in SchemeTranslation.objects.filter(scheme_id__in=ids, language__code=lang).exclude(title="").values_list("scheme_id", "title"):
            titles[sid] = t

    li = 1 if lang == "hi" else 0
    out = []
    for r in rows:
        score, why = 0, []

        def add(points, key):
            nonlocal score
            score += points
            why.append(REASONS[key][li])

        # hard checks on the comma-separated tag fields
        ok = True
        for field, val in (("scheme_for", p["gender"]), ("castes", p["caste"]),
                           ("marital_status", p["marital_status"]), ("religions", p["religion"])):
            if val is None:
                continue
            tags = _codes(r[field])
            if tags and val not in tags:
                ok = False
                break
        if not ok:
            continue
        occ = occ_tags.get(r["id"])
        if occ and p["occupation_id"] and p["occupation_id"] not in occ:
            continue
        area = area_tags.get(r["id"])
        if area and p["area"] is not None and p["area"] not in area:
            continue

        # targeting score
        if r["scheme_type"] == 1:
            add(2, "state")
        g = _codes(r["scheme_for"])
        if p["gender"] is not None and g and g != FULL["scheme_for"]:
            add(3, {0: "men", 1: "women", 2: "trans"}[p["gender"]])
        for field, val, key in (("castes", p["caste"], "caste"), ("marital_status", p["marital_status"], "marital"),
                                ("religions", p["religion"], "religion")):
            tags = _codes(r[field])
            if val is not None and tags and tags != FULL[field]:
                add(3 if key == "caste" else 2, key)
        if r["divyang"] == 0 and p["divyang"] == 0:
            add(3, "divyang")
        if occ and p["occupation_id"] in occ:
            add(3, "occupation")
        if area and p["area"] in area:
            add(1, "area")
        if p["age"] is not None and (r["age_min"], r["age_max"]) != (0, 100):
            add(1, "age")
        if p["family_income"] is not None and r["income_max"]:
            add(1, "income")

        out.append({
            "id": r["id"],
            "title": (titles.get(r["id"]) or r["title"] or "").strip(),
            "category": r["category__title"] or "",
            "state": r["state__state"] or "",
            "central": r["scheme_type"] == 0,
            "score": score,
            "reasons": why,
            "targeted": score >= TARGETED_MIN_SCORE,
        })
    out.sort(key=lambda s: (-s["score"], s["title"].lower()))
    return out
