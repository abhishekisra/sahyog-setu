"""Machine translation of Sahyog Setu content into the 22 Indian languages (2026-11-23).

User: "sahyog setu mein 21 language kaise jode" -> chose option 3 "quiz aur sabhi jagah kewal sahyog setu
portal": AI4Bharat IndicTrans2 (open, MIT licence), run on Google Colab (this server has no GPU).

Flow
  1. `manage.py i18n_export` cuts every English text into unique segments (HTML fields: only the visible
     text between tags, so the formatting is kept) and writes batches to JOB_ROOT/<job>/.
  2. The Colab notebook downloads the batches (token-protected URLs in views_i18n.py), translates them and
     posts each batch back; results land in JOB_ROOT/<job>/results/<lang>/.
  3. `manage.py i18n_import` re-reads the CURRENT English text from the database, looks every segment up in
     the results and fills ONLY EMPTY translation fields. Existing (human) translations are never changed.
     Every machine-filled field is logged in JOB_ROOT/machine_log.jsonl for later review.

Jobs: "core" = everything except long scheme texts (quiz, states, districts, documents, portals, pages,
registrations, scheme titles, UI words); "schemes" = scheme description / eligibility / documents / how to apply.
"""
import hashlib
import json
import os
import re
from html.parser import HTMLParser

JOB_ROOT = os.environ.get("SAHYOG_I18N_ROOT", "/var/lib/sahyog-i18n")
CHUNK_CHARS = 60000          # keeps every result upload far below nginx's 1 MB limit

# site language code -> IndicTrans2 code (script as the site shows it, see Language.native_name)
IT2_CODES = {
    "as": "asm_Beng", "bn": "ben_Beng", "brx": "brx_Deva", "doi": "doi_Deva", "gu": "guj_Gujr",
    "hi": "hin_Deva", "kn": "kan_Knda", "ks": "kas_Arab", "kok": "gom_Deva", "mai": "mai_Deva",
    "ml": "mal_Mlym", "mni": "mni_Beng", "mr": "mar_Deva", "ne": "npi_Deva", "or": "ory_Orya",
    "pa": "pan_Guru", "sa": "san_Deva", "sat": "sat_Olck", "sd": "snd_Arab", "ta": "tam_Taml",
    "te": "tel_Telu", "ur": "urd_Arab",
}

# translation field -> base model field, where the names differ
FIELD_ALIASES = {("Questions", "question_text"): "question", ("States", "state_name"): "state"}
SCHEME_LONG = {"description", "eligibility", "required_documents", "mode_of_application"}
_CODES = re.compile(r"^[\d,\s]*$")
_SKIP_SEG = re.compile(r"^\s*(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.]+)\s*$", re.I)
_LETTERS = re.compile(r"[A-Za-z]")


def key_of(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def wants(text):
    """A segment worth translating: has English letters, is not just a link / email."""
    return bool(text and _LETTERS.search(text) and not _SKIP_SEG.match(text))


class _Nodes(HTMLParser):
    """Splits HTML into (is_text, raw) pieces so text can be swapped and the markup kept byte-for-byte."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def _raw(self):
        return self.get_starttag_text() or ""

    def handle_starttag(self, tag, attrs):
        self.parts.append((False, self._raw()))

    def handle_startendtag(self, tag, attrs):
        self.parts.append((False, self._raw()))

    def handle_endtag(self, tag):
        self.parts.append((False, f"</{tag}>"))

    def handle_data(self, data):
        self.parts.append((True, data))

    def handle_entityref(self, name):
        self.parts.append((True, f"&{name};"))

    def handle_charref(self, name):
        self.parts.append((True, f"&#{name};"))

    def handle_comment(self, data):
        self.parts.append((False, f"<!--{data}-->"))

    def handle_decl(self, decl):
        self.parts.append((False, f"<!{decl}>"))


def _merge_text(parts):
    """Adjacent text pieces (text + entity + text) become one piece."""
    out = []
    for is_text, raw in parts:
        if is_text and out and out[-1][0]:
            out[-1] = (True, out[-1][1] + raw)
        else:
            out.append((is_text, raw))
    return out


def is_html(text):
    return bool(re.search(r"<[a-zA-Z/!][^>]*>", text or ""))


def html_pieces(text):
    p = _Nodes()
    p.feed(text)
    p.close()
    return _merge_text(p.parts)


def _clean(raw):
    import html as _h
    return " ".join(_h.unescape(raw).split())


def segments_of(text):
    """Unique translatable segments (clean text) of one field value."""
    if not text or _CODES.match(text):
        return []
    if not is_html(text):
        t = _clean(text)
        return [t] if wants(t) else []
    return [c for is_t, raw in html_pieces(text) if is_t for c in [_clean(raw)] if wants(c)]


def rebuild(text, tr):
    """The field value with every segment replaced by its translation (dict clean->translated).
    None if any segment has no translation (the field then stays English)."""
    import html as _h
    if not is_html(text):
        t = _clean(text)
        return tr.get(t) if wants(t) else None
    out = []
    for is_t, raw in html_pieces(text):
        if not is_t:
            out.append(raw)
            continue
        c = _clean(raw)
        if not wants(c):
            out.append(raw)
            continue
        if c not in tr:
            return None
        lead = raw[: len(raw) - len(raw.lstrip())]
        trail = raw[len(raw.rstrip()):]
        out.append(lead + _h.escape(tr[c], quote=False) + trail)
    return "".join(out)


def translatable_models():
    """[(TranslationModel, BaseModel, fk_name, [(translation_field, base_field)])] for every *Translation model."""
    from django.apps import apps
    from django.db import models as M
    out = []
    for tm in apps.get_models():
        if not tm.__name__.endswith("Translation"):
            continue
        fks = [f for f in tm._meta.fields if isinstance(f, M.ForeignKey) and f.name != "language"]
        if not fks:
            continue
        base = fks[0].related_model
        base_names = {f.name for f in base._meta.fields}
        pairs = []
        for f in tm._meta.fields:
            if not isinstance(f, (M.CharField, M.TextField)) or f.name in ("id",):
                continue
            bf = FIELD_ALIASES.get((base.__name__, f.name), f.name)
            if bf in base_names:
                pairs.append((f.name, bf))
        if pairs:
            out.append((tm, base, fks[0].name, pairs))
    return out


def in_job(job, base, base_field):
    if base.__name__ == "Schemes" and base_field in SCHEME_LONG:
        return job == "schemes"
    return job == "core"


def ui_strings_path():
    return os.path.join(os.path.dirname(__file__), "ui_strings.json")


def ui_machine_path():
    return os.path.join(JOB_ROOT, "ui_strings_machine.json")


def _read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def load_ui_strings(machine=True):
    """{English: {lang: text}}: the hand-made list in the repo (languages/ui_strings.json), plus machine
    translations (JOB_ROOT/ui_strings_machine.json) only where the hand-made list has none."""
    data = _read_json(ui_strings_path())
    if machine:
        for en, langs in _read_json(ui_machine_path()).items():
            if en in data:
                for lg, t in langs.items():
                    if t and not data[en].get(lg):
                        data[en][lg] = t
    return data


def collect(job):
    """All unique segments of a job, in a useful order (short labels first, long texts last)."""
    seen, segs = set(), []

    def add(t):
        if t not in seen:
            seen.add(t)
            segs.append(t)
    if job == "core":
        for en in load_ui_strings():
            for s in segments_of(en):
                add(s)
    for tm, base, fk, pairs in translatable_models():
        for tf, bf in pairs:
            if not in_job(job, base, bf):
                continue
            for v in base.objects.values_list(bf, flat=True).iterator():
                for s in segments_of(str(v or "")):
                    add(s)
    return segs


def job_dir(job):
    return os.path.join(JOB_ROOT, job)


def write_job(job, langs):
    segs = collect(job)
    d = job_dir(job)
    os.makedirs(d, exist_ok=True)
    chunks, cur, size = [], [], 0
    for s in segs:
        if cur and size + len(s) > CHUNK_CHARS:
            chunks.append(cur)
            cur, size = [], 0
        cur.append({"k": key_of(s), "t": s})
        size += len(s)
    if cur:
        chunks.append(cur)
    for old in os.listdir(d):
        if old.startswith("chunk_"):
            os.remove(os.path.join(d, old))
    for i, c in enumerate(chunks):
        with open(os.path.join(d, f"chunk_{i:04d}.json"), "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False)
    manifest = {"job": job, "chunks": len(chunks), "segments": len(segs), "chars": sum(len(s) for s in segs),
                "langs": [{"code": c, "it2": IT2_CODES[c]} for c in langs]}
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return manifest


# ---- quality gate (user 2026-11-23: "language bilkul sahi ho") ----
# A machine translation is used only if it passes every check below; otherwise the field stays English
# and the segment is listed in JOB_ROOT/rejects/<job>_<lang>.jsonl for a person to fix.
SCRIPT_RANGES = {
    "Deva": [(0x0900, 0x097F), (0xA8E0, 0xA8FF)], "Beng": [(0x0980, 0x09FF)], "Gujr": [(0x0A80, 0x0AFF)],
    "Guru": [(0x0A00, 0x0A7F)], "Orya": [(0x0B00, 0x0B7F)], "Taml": [(0x0B80, 0x0BFF)],
    "Telu": [(0x0C00, 0x0C7F)], "Knda": [(0x0C80, 0x0CFF)], "Mlym": [(0x0D00, 0x0D7F)],
    "Arab": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)], "Olck": [(0x1C50, 0x1C7F)],
}
_NATIVE_DIGITS = {}
for _base in (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66, 0x06F0, 0x0660, 0x1C50):
    for _i in range(10):
        _NATIVE_DIGITS[chr(_base + _i)] = str(_i)
_DIGIT_TABLE = str.maketrans(_NATIVE_DIGITS)


def ascii_digits(text):
    """Numbers are kept as 0-9 everywhere (amounts / ages / dates stay exactly as in English)."""
    return str(text).translate(_DIGIT_TABLE)


def check(src, tgt, lang):
    """'' if the translation is acceptable, else the reason it was rejected."""
    tgt = str(tgt or "").strip()
    if not tgt:
        return "empty"
    script = IT2_CODES[lang].split("_")[1]
    ranges = SCRIPT_RANGES[script]
    # Latin words that also appear in the English (PAN, ABHA, UPI, e-Shram ...) may stay as they are
    src_words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z.-]*", src)}
    kept = "".join(w for w in re.findall(r"[A-Za-z][A-Za-z.-]*", tgt) if w.lower() in src_words)
    letters = [c for c in re.sub(r"[A-Za-z][A-Za-z.-]*", lambda m: "" if m.group(0).lower() in src_words else m.group(0), tgt) if c.isalpha()]
    src_latin_n = sum(1 for c in src if c.isascii() and c.isalpha())
    if src_latin_n > 20 and len(kept) > 0.5 * src_latin_n:
        return "left in English"
    if not letters:
        return "" if kept else "no letters"
    native = sum(1 for c in letters if any(a <= ord(c) <= b for a, b in ranges))
    latin = sum(1 for c in letters if c.isascii())
    src_latin = sum(1 for c in src if c.isascii() and c.isalpha())
    if native / len(letters) < 0.6 and not (src_latin <= 6):          # short acronyms (PAN, ABHA) may stay Latin
        return "wrong script"
    if latin > 0.5 * src_latin and src_latin > 20:
        return "left in English"
    if sorted(re.findall(r"\{[^{}]*\}", src)) != sorted(re.findall(r"\{[^{}]*\}", tgt)):
        return "placeholder changed"
    nums_src = sorted(re.findall(r"\d+", src.replace(",", "")))
    nums_tgt = sorted(re.findall(r"\d+", ascii_digits(tgt).replace(",", "")))
    if nums_src != nums_tgt:
        return "numbers changed"
    ratio = len(tgt) / max(1, len(src))
    if len(src) > 25 and not (0.35 <= ratio <= 3.5):
        return "length looks wrong"
    words = tgt.split()
    if len(words) >= 8 and max(words.count(w) for w in set(words)) > max(5, len(words) // 3):
        return "repeated words"
    return ""


def load_results(job, lang):
    """{clean English segment: translation} from every result batch of this job + language."""
    d = os.path.join(job_dir(job), "results", lang)
    by_key = {}
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        by_key.update(json.load(f))
                except (OSError, ValueError):
                    continue
    if not by_key:
        return {}
    out, rejects = {}, []
    for fn in sorted(os.listdir(job_dir(job))):
        if fn.startswith("chunk_"):
            with open(os.path.join(job_dir(job), fn), encoding="utf-8") as f:
                for it in json.load(f):
                    if it["k"] not in by_key:
                        continue
                    tgt = ascii_digits(" ".join(str(by_key[it["k"]]).split()))
                    why = check(it["t"], tgt, lang)
                    if why:
                        rejects.append({"k": it["k"], "en": it["t"], "machine": tgt, "why": why})
                    else:
                        out[it["t"]] = tgt
    rd = os.path.join(JOB_ROOT, "rejects")
    os.makedirs(rd, exist_ok=True)
    with open(os.path.join(rd, f"{job}_{lang}.jsonl"), "w", encoding="utf-8") as f:
        for x in rejects:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return out
