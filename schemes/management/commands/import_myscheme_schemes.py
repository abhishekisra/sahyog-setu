import difflib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from schemes.models import Categories, Schemes
from states.models import States

API_KEY = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"
HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json",
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}
SEARCH_URL = "https://api.myscheme.gov.in/search/v6/schemes"
DETAIL_URL = "https://api.myscheme.gov.in/schemes/v6/public/schemes"
PAGE_SIZE = 100
REQUEST_DELAY = 0.25
DUPLICATE_TITLE_THRESHOLD = 0.82  # matches an existing hand-entered scheme -> skip, don't duplicate

# myscheme's own schemeCategory label -> local Categories.title. Several
# myscheme categories (Social welfare & Empowerment, Housing & Shelter,
# Science/IT, Transport, Travel & Tourism, Public Safety) have no good local
# equivalent -- Categories.image is a required field with no placeholder
# asset available here, so rather than create new categories we fold those
# into the closest existing bucket via CATEGORY_KEYWORD_RULES below, checked
# before falling back to this table.
CATEGORY_LABEL_MAP = {
    "education & learning": "EDUCATION & LEARNING",
    "agriculture,rural & environment": "AGRICULTURE & FARMER WELFARE",
    "women and child": "WOMEN & CHILD DEVELOPMENT",
    "health & wellness": "HEALTH & HYGIENE",
    "utility & sanitation": "HEALTH & HYGIENE",
    "banking,financial services and insurance": "INSURANCE & PENSION",
    "sports & culture": "YOUTH AFFAIRS & SPORTS",
    "skills & employment": "LIVELIHOOD & EMPLOYBILITY",
    "business & entrepreneurship": "LIVELIHOOD & EMPLOYBILITY",
}
# Keyword rules checked FIRST, against the scheme's own title+tags+eligibility
# text -- these override the coarse category-label mapping above whenever a
# scheme is clearly about a specific population (e.g. a "Social welfare &
# Empowerment" scheme that's actually senior-citizen-specific should land in
# SENIOR CITIZEN, not the catch-all).
CATEGORY_KEYWORD_RULES = [
    (("senior citizen", "elderly", "old age", "vayoshri"), "SENIOR CITIZEN"),
    (("divyang", "disability", "disabled", "differently abled", "pwd "), "DIFFERENTLY ABLED"),
    (("tribal", "scheduled tribe", " st ", "vanbandhu", "adivasi"), "TRIBAL WELFARE"),
    (("cooperative", "co-operative"), "COOPERATIVE DEVELOPMENT"),
    (("fisheries", "fisherman", "fishing", "animal husbandry", "livestock", "dairy", "poultry",
      "piggery", " pig ", " pigs", "goat", "sheep", "cattle", "buffalo", "bakri", "gau palan",
      "pmmsy", "aquaculture", "biofloc", "matsya"), "ANIMAL HUSBANDRY & FISHERIES"),
    (("women", "girl", "mahila", "balika", "child", "bal ", "matru"), "WOMEN & CHILD DEVELOPMENT"),
    # myscheme's "Agriculture,Rural & Environment" label also covers generic
    # rural/environment schemes with nothing to do with farming -- checked
    # before the real agriculture rule so these route to the catch-all
    # instead.
    (("electric vehicle", "e-vehicle", "rural electrification", "solar rooftop"), "LIVELIHOOD & EMPLOYBILITY"),
    (("farmer", "farming", "agriculture", "kisan", "crop", "irrigation", "horticulture",
      "soil health", "soil testing", "rkvy"), "AGRICULTURE & FARMER WELFARE"),
    # Checked after every subject/group-specific rule above (so e.g. a tribal
    # or agriculture-subject scholarship still lands in that more specific
    # category), but before pension/health/sports below -- a bare "medical"
    # or "hospital" scholarship is really an education scheme (it funds
    # studying, not treatment), and "Chief Minister Scholarship Scheme" has
    # nothing to do with either; without this rule those fell through to
    # whatever unrelated keyword happened to match next.
    (("scholarship", "shiksha protsahan"), "EDUCATION & LEARNING"),
    # myscheme buckets business loans/term-loans/share-capital schemes under
    # the same "Banking,Financial Services and Insurance" label as genuine
    # personal insurance/pension schemes -- checked before the pension rule
    # below so e.g. "Term Loan Scheme for Backward Classes" lands in
    # Livelihood (the actual catch-all for business/entrepreneurship
    # schemes) instead of Insurance & Pension.
    (("loan", "credit", "entrepreneur", "share capital", "term loan"), "LIVELIHOOD & EMPLOYBILITY"),
    (("pension", "insurance", "bima"), "INSURANCE & PENSION"),
    (("bijli", "electricity bill", "vidyut bill"), "LIVELIHOOD & EMPLOYBILITY"),
    (("health", "hospital", "medical", "ayushman", "arogya", "sanitation", "hygiene"), "HEALTH & HYGIENE"),
    (("sports", "youth", "yuva", "culture", "khel"), "YOUTH AFFAIRS & SPORTS"),
]
CATCH_ALL_CATEGORY = "LIVELIHOOD & EMPLOYBILITY"

SCHEME_FOR_ALL = "0,1,2"
MARITAL_ALL = "0,1,2,3,4"
BENIFICIARIES_ALL = "0,1,2,3,4,5,6"
RELIGIONS_ALL = "0,1,2,3,4,5,6,7"
CASTES_ALL = "0,1,2,3,4"

RELIGION_CODES = {"hindu": 0, "muslim": 1, "christian": 2, "sikh": 3, "parsi": 4, "buddhis": 5, "jain": 6}
CASTE_CODES = {"general": 0, "obc": 1, "sc": 2, "scheduled caste": 2, "st": 3, "scheduled tribe": 3, "pvtg": 4}


def http_get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def search_page(keyword, frm, size=PAGE_SIZE):
    q = urllib.parse.quote(keyword)
    url = f"{SEARCH_URL}?lang=en&q=%5B%5D&keyword={q}&sort=&from={frm}&size={size}"
    return http_get_json(url)


def fetch_detail(slug):
    url = f"{DETAIL_URL}?slug={urllib.parse.quote(slug)}&lang=en"
    return http_get_json(url)


def fetch_documents(scheme_mongo_id):
    url = f"{DETAIL_URL}/{scheme_mongo_id}/documents?lang=en"
    return http_get_json(url)


def render_nodes(nodes):
    """Converts myscheme's Slate-style rich-text node tree into simple HTML
    matching the <p>/<ul>/<li>/<a> convention already used throughout the
    hand-entered Schemes rows (see e.g. id=13's eligibility/mode_of_application
    in the DB) -- so imported and hand-entered rows render identically on the
    public site."""
    if not nodes:
        return ""
    out = []
    for node in nodes:
        out.append(_render_node(node))
    return "".join(out)


def _render_text_run(run):
    text = run.get("text", "")
    if not text:
        return ""
    if run.get("bold"):
        text = f"<strong>{text}</strong>"
    if run.get("italic"):
        text = f"<em>{text}</em>"
    return text


def _render_node(node):
    ntype = node.get("type")
    children = node.get("children", [])
    if ntype in ("paragraph", None):
        inner = "".join(
            _render_text_run(c) if "text" in c else _render_node(c) for c in children
        )
        return f"<p>{inner}</p>" if inner.strip() else ""
    if ntype in ("ol_list", "ul_list"):
        tag = "ol" if ntype == "ol_list" else "ul"
        inner = "".join(_render_node(c) for c in children)
        return f"<{tag}>{inner}</{tag}>"
    if ntype == "list_item":
        inner = "".join(
            _render_text_run(c) if "text" in c else _render_node(c) for c in children
        )
        return f"<li>{inner}</li>"
    if ntype == "link":
        inner = "".join(_render_text_run(c) for c in children if "text" in c)
        href = node.get("url", "")
        return f'<a href="{href}" target="_blank">{inner}</a>'
    # Unknown node type -- fall back to just the text content so nothing is
    # silently dropped, even if the formatting isn't preserved.
    inner = "".join(
        _render_text_run(c) if "text" in c else _render_node(c) for c in children
    )
    return inner


def guess_category_id(category_cache, scheme_name, tags, myscheme_category_label):
    haystack = " ".join([scheme_name or "", " ".join(tags or [])]).lower()
    for keywords, local_title in CATEGORY_KEYWORD_RULES:
        if any(kw in haystack for kw in keywords):
            if local_title in category_cache:
                return category_cache[local_title]
    mapped = CATEGORY_LABEL_MAP.get((myscheme_category_label or "").lower())
    if mapped and mapped in category_cache:
        return category_cache[mapped]
    return category_cache[CATCH_ALL_CATEGORY]


def guess_eligibility(eligibility_text, scheme_name, tags):
    """Best-effort keyword scan -- only overrides the "everyone eligible"
    default when the scheme's own text/tags clearly say so, per the explicit
    instruction to guess from myscheme's text rather than leave everything
    blank. Never narrows a field on a weak/ambiguous signal, since a wrong
    exclusion here would incorrectly tell a real citizen they don't qualify."""
    text = (eligibility_text or "").lower()
    haystack = text + " " + " ".join(tags or []).lower() + " " + (scheme_name or "").lower()

    scheme_for = SCHEME_FOR_ALL
    if re.search(r"\btransgender\b", haystack):
        scheme_for = "2"
    elif re.search(r"\b(?:should|must)\s+be\s+a\s+wom[ae]n\b|\bwomen\s+only\b|\bfor\s+women\b|\bonly\s+for\s+women\b", haystack):
        scheme_for = "1"
    elif re.search(r"\b(?:should|must)\s+be\s+a\s+man\b|\bmen\s+only\b|\bonly\s+for\s+men\b", haystack):
        scheme_for = "0"

    # Only narrows on an explicit exclusivity phrase ("widows only", "must be
    # a widow") -- Udyogini's real text just lists widows as a *priority*
    # group within an otherwise open scheme ("preference to ... widow"),
    # which a bare `\bwidow\b` search wrongly treated as a hard requirement
    # and would have told every non-widow woman she didn't qualify.
    marital_status = MARITAL_ALL
    if re.search(r"\bwidows?\s+only\b|\b(?:should|must)\s+be\s+a\s+widow(?:er)?\b|\bonly\s+widows?\b", haystack):
        marital_status = "2"

    # A bare mention of a category name is not a restriction -- e.g. Udyogini's
    # real text says "for women belonging to general AND special categories"
    # (explicitly open to all), but a plain `\bgeneral\b` search matched it and
    # wrongly narrowed the scheme to General-caste-only. Require the keyword to
    # sit near an actual exclusivity marker ("only", "must be", "reserved for",
    # "exclusively") before treating it as a real restriction -- checked against
    # BOTH the scheme name (titles like "(General Category)" or "OBC Pre-Matric
    # Scholarship" are a reliable, deliberate signal) and the eligibility text.
    EXCL = r"(?:only|exclusiv\w*|reserved for|restrict\w*|(?:should|must)\s+(?:be|belong))"

    def exclusive_match(text, keyword, window=30):
        pat_before = rf"\b{keyword}\b.{{0,{window}}}?{EXCL}"
        pat_after = rf"{EXCL}.{{0,{window}}}?\b{keyword}\b"
        return bool(re.search(pat_before, text) or re.search(pat_after, text))

    title_lower = (scheme_name or "").lower()

    benificiaries = BENIFICIARIES_ALL
    if re.search(r"\(\s*bpl\s*\)|\bbpl\s+only\b|\bonly\s+bpl\b", title_lower) or exclusive_match(haystack, "bpl"):
        benificiaries = "0"

    religions = RELIGIONS_ALL
    found_religions = [code for name, code in RELIGION_CODES.items()
                        if f"({name}" in title_lower or exclusive_match(haystack, name)]
    if found_religions and len(found_religions) < len(RELIGION_CODES):
        religions = ",".join(str(c) for c in sorted(set(found_religions)))

    castes = CASTES_ALL
    found_castes = set()
    for name, code in CASTE_CODES.items():
        title_signal = re.search(rf"\({name}\)|\b{name}\b.{{0,20}}scholarship|scholarship.{{0,20}}\b{name}\b", title_lower)
        if title_signal or exclusive_match(haystack, name):
            found_castes.add(code)
    if found_castes and found_castes != {0, 1, 2, 3, 4}:
        castes = ",".join(str(c) for c in sorted(found_castes))

    divyang = 2  # Both -- no restriction either way, the safe default
    if re.search(r"\bdivyang\b|\bdisab(led|ility)\b|\bpwd\b|differently abled", haystack):
        divyang = 0

    age_min, age_max = 0, 100
    m = re.search(r"(\d{1,2})\s*(?:to|-|–)\s*(\d{1,3})\s*years", haystack)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 <= lo < hi <= 120:
            age_min, age_max = lo, hi

    income_min, income_max = 0, 0
    m = re.search(r"(?:income|earn).{0,60}?(?:rs\.?|₹)\s*([\d,]+)", haystack)
    if m:
        try:
            income_max = int(m.group(1).replace(",", ""))
        except ValueError:
            pass

    return {
        "scheme_for": scheme_for, "marital_status": marital_status,
        "benificiaries": benificiaries, "religions": religions, "castes": castes,
        "divyang": divyang, "age_min": age_min, "age_max": age_max,
        "income_min": income_min, "income_max": income_max,
    }


class Command(BaseCommand):
    help = (
        "Import schemes from myscheme.gov.in's public search API that don't already "
        "exist in the Schemes table. Existing hand-entered schemes are never modified "
        "-- matched by fuzzy title against every new candidate and skipped. Idempotent "
        "via the myscheme_slug field, safe to re-run/resume. Imported rows are created "
        "Inactive (status=0) for admin review before going live."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None,
                             help="Stop after importing this many NEW schemes (for test batches).")
        parser.add_argument("--dry-run", action="store_true",
                             help="Fetch and map everything but don't write to the DB.")

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]

        category_cache = {c.title: c.id for c in Categories.objects.all()}
        state_cache = {s.state.lower(): s.id for s in States.objects.all()}

        existing_titles = list(Schemes.objects.filter(myscheme_slug__isnull=True).values_list("title", flat=True))
        imported_slugs = set(Schemes.objects.filter(myscheme_slug__isnull=False).values_list("myscheme_slug", flat=True))

        self.stdout.write(f"Existing hand-entered schemes (never touched): {len(existing_titles)}")
        self.stdout.write(f"Already imported from myscheme in a previous run: {len(imported_slugs)}")

        first_page = search_page("", 0, size=1)
        total = first_page["data"]["summary"]["total"]
        self.stdout.write(f"Total schemes on myscheme.gov.in: {total}")

        created, skipped_dup, skipped_existing, errors = 0, 0, 0, 0
        frm = 0
        while frm < total:
            time.sleep(REQUEST_DELAY)
            try:
                page = search_page("", frm)
            except Exception as e:
                self.stderr.write(f"Search page fetch failed at from={frm}: {e}")
                frm += PAGE_SIZE
                continue

            items = page.get("data", {}).get("hits", {}).get("items", [])
            if not items:
                break

            for item in items:
                fields = item["fields"]
                slug = fields.get("slug")
                name = fields.get("schemeName", "")
                if not slug or not name:
                    continue
                if slug in imported_slugs:
                    continue

                # Never duplicate an existing hand-entered scheme.
                dup = False
                for t in existing_titles:
                    if difflib.SequenceMatcher(None, t.lower(), name.lower()).ratio() >= DUPLICATE_TITLE_THRESHOLD:
                        dup = True
                        break
                if dup:
                    skipped_existing += 1
                    imported_slugs.add(slug)  # don't re-check this slug on future runs
                    continue

                try:
                    time.sleep(REQUEST_DELAY)
                    detail = fetch_detail(slug)["data"]
                    en = detail["en"]
                    basic = en["basicDetails"]
                    content = en["schemeContent"]
                    eligibility_block = en.get("eligibilityCriteria", {}) or {}
                    app_process = en.get("applicationProcess", []) or []

                    time.sleep(REQUEST_DELAY)
                    try:
                        docs = fetch_documents(detail["_id"])["data"]["en"].get("documents_required", [])
                    except Exception:
                        docs = []

                    tags = basic.get("tags") or []
                    level_value = (basic.get("level") or {}).get("value", "central")
                    scheme_type = 0 if level_value == "central" else 1
                    cat_labels = [c.get("label") for c in (basic.get("schemeCategory") or [])]
                    category_id = guess_category_id(category_cache, name, tags, cat_labels[0] if cat_labels else None)

                    state_id = None
                    if scheme_type == 1:
                        ben_states = fields.get("beneficiaryState") or []
                        for s in ben_states:
                            sid = state_cache.get(s.lower())
                            if sid:
                                state_id = sid
                                break

                    description_html = render_nodes(content.get("detailedDescription") or [])
                    if not description_html.strip():
                        brief = content.get("briefDescription", "")
                        description_html = f"<p>{brief}</p>" if brief else ""
                    eligibility_html = render_nodes(eligibility_block.get("eligibilityDescription") or [])
                    if not eligibility_html.strip():
                        md = eligibility_block.get("eligibilityDescription_md", "")
                        eligibility_html = f"<p>{md}</p>" if md else "<p>Refer to the official scheme page for eligibility details.</p>"
                    documents_html = render_nodes(docs) or "<p>Refer to the official scheme page for the documents list.</p>"

                    mode_parts = []
                    for mode in app_process:
                        mode_label = mode.get("mode", "")
                        mode_html = render_nodes(mode.get("process") or [])
                        mode_parts.append(f"<h4>{mode_label} Apply:</h4>{mode_html}")
                    mode_of_application_html = "".join(mode_parts) or "<p>Refer to the official scheme page for how to apply.</p>"

                    # Prefer the scheme's own specific official links (ministry/
                    # department site, guidelines PDF, application portal --
                    # myscheme.gov.in's "references") over myscheme.gov.in's own
                    # generic aggregator page for that scheme -- visitors should
                    # land on the actual issuing authority's page, not a second
                    # discovery layer. Only fall back to the myscheme.gov.in page
                    # (relabeled, no "myScheme" wording) when a scheme has no
                    # specific references at all (~4 in 4485 at last count).
                    ref_links = [
                        f'<p><a href="{ref["url"]}" target="_blank">{ref.get("title") or "Reference"}</a></p>'
                        for ref in (content.get("references") or []) if ref.get("url")
                    ]
                    if ref_links:
                        web_links_html = "".join(ref_links)
                    else:
                        web_links_html = (
                            f'<p><a href="https://www.myscheme.gov.in/schemes/{slug}" target="_blank">'
                            f'View Official Scheme Details (Government of India)</a></p>'
                        )

                    elig = guess_eligibility(
                        eligibility_block.get("eligibilityDescription_md", ""), name, tags,
                    )

                    if not dry_run:
                        Schemes.objects.create(
                            title=name,
                            myscheme_slug=slug,
                            scheme_type=scheme_type,
                            status=0,
                            business_related=0,
                            dbt=1 if basic.get("dbtScheme") else 0,
                            category_id=category_id,
                            state_id=state_id,
                            income_max=elig["income_max"], income_min=elig["income_min"],
                            divyang=elig["divyang"],
                            description=description_html,
                            eligibility=eligibility_html,
                            required_documents=documents_html,
                            web_links=web_links_html,
                            mode_of_application=mode_of_application_html,
                            occupations="",
                            age_max=elig["age_max"], age_min=elig["age_min"],
                            scheme_for=elig["scheme_for"],
                            marital_status=elig["marital_status"],
                            benificiaries=elig["benificiaries"],
                            religions=elig["religions"],
                            castes=elig["castes"],
                        )
                    imported_slugs.add(slug)
                    created += 1
                    if created % 25 == 0:
                        self.stdout.write(f"...{created} imported so far (at from={frm}, slug={slug})")
                    if limit and created >= limit:
                        self.stdout.write(self.style.SUCCESS(
                            f"Reached --limit {limit}. created={created} skipped_existing={skipped_existing} errors={errors}"
                        ))
                        return
                except Exception as e:
                    errors += 1
                    self.stderr.write(f"Failed on slug={slug} ({name}): {e}")

            frm += PAGE_SIZE

        self.stdout.write(self.style.SUCCESS(
            f"Done. created={created} skipped_existing_duplicate={skipped_existing} errors={errors}"
        ))
