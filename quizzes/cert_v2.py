"""Certificate design v2 (user's design, 2026-11-05).

One template (custom_admin/quizzes/_cert_sheet.html) drives both the on-screen
/ print certificate page and the downloadable PNG, so they always match. The
PNG is a headless-Chromium screenshot of that same sheet (user chose this over
the older Pillow-only drawing in cert_image.py, which stays for the vertical
"story" image).

Logos, signatures and the QR code are embedded as data: URIs so the sheet
renders without any request back to the site (signature files are not public
-- nginx 404s /media/quiz/authorities/signatures/).
"""
import base64
import glob
import hashlib
import logging
import mimetypes
import os
from io import BytesIO

from django.template.loader import render_to_string

VERIFY_BASE = "https://sahyogsetu.in/certificate/verify/"
# Chromium lives in a shared, world-readable path because the gunicorn user
# (sahyog) has no home directory (/nonexistent) for Playwright's default cache.
BROWSERS_PATH = "/opt/ms-playwright"


def _file_data_uri(field_file):
    if not field_file:
        return ""
    try:
        path = field_file.path
        with open(path, "rb") as fh:
            data = fh.read()
    except (ValueError, OSError):
        return ""
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _qr_data_uri(text, color=(28, 43, 36)):
    """Same reportlab-matrix + Pillow approach as views.quiz_qr_code."""
    from PIL import Image, ImageDraw
    from reportlab.graphics.barcode.qr import QrCodeWidget

    widget = QrCodeWidget(text)
    widget.qr.make()
    matrix, count = widget.qr.modules, widget.qr.moduleCount
    scale, border = 8, 2
    size = (count + border * 2) * scale
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)
    for r in range(count):
        for c in range(count):
            if matrix[r][c]:
                x0, y0 = (c + border) * scale, (r + border) * scale
                draw.rectangle([x0, y0, x0 + scale - 1, y0 + scale - 1], fill=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def grade_for(percentage):
    p = round(percentage or 0)
    return "DISTINCTION" if p >= 90 else "MERIT" if p >= 75 else "PASS"


ROLE_FULL = {"CEO": "Chief Executive Officer", "COO": "Chief Operating Officer"}


def _role(text):
    text = (text or "").strip()
    return ROLE_FULL.get(text.upper(), text)


def certificate_context(attempt, display_name):
    quiz = attempt.quiz
    cert_id = attempt.certificate_id or ""
    verify_url = VERIFY_BASE + cert_id + "/"
    issued = attempt.certificate_issued_at or attempt.completed_at
    return {
        "c_name": display_name,
        "c_quiz": quiz.title,
        "c_body": (quiz.certificate_text or "").strip(),
        "c_score": round(attempt.percentage or 0),
        "c_grade": grade_for(attempt.percentage),
        "c_date": issued.strftime("%d %b %Y") if issued else "",
        "c_id": cert_id,
        "c_verify_text": "sahyogsetu.in/certificate/verify/" + cert_id,
        "c_qr": _qr_data_uri(verify_url) if cert_id else "",
        "c_logo_left": _file_data_uri(quiz.logo_1),
        "c_logo_right": _file_data_uri(quiz.logo_2),
        "c_sig1": _file_data_uri(quiz.authority1_sign_image),
        "c_sig2": _file_data_uri(quiz.authority2_sign_image),
        "c_auth1_name": quiz.authority1_name or "Authorized Signatory",
        "c_auth1_role": _role(quiz.authority1_designation),
        "c_auth2_name": quiz.authority2_name or "Authorized Signatory",
        "c_auth2_role": _role(quiz.authority2_designation),
    }


# ---------------------------------------------------------------------------
# File cache (2026-11-05). Each render takes ~4 s of a gunicorn worker and the
# site has only 3 workers, so a training batch downloading at once would stall
# every page. A finished file is kept, keyed by a hash of exactly what it was
# drawn from (the full sheet HTML: name, score, date, quiz text, authorities,
# logo/signature bytes, design). Anything changes -> new key -> fresh render.
# Kept outside /media so it is never web-served.
# ---------------------------------------------------------------------------
CACHE_DIR = "/var/lib/sahyogsetu/cert_cache"


def _cached(attempt_id, kind, key_material, ext, build):
    if isinstance(key_material, str):
        key_material = key_material.encode("utf-8")
    key = hashlib.sha256(key_material).hexdigest()[:24]
    path = os.path.join(CACHE_DIR, f"{attempt_id}-{kind}-{key}.{ext}")
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        pass
    data = build()
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        for old in glob.glob(os.path.join(CACHE_DIR, f"{attempt_id}-{kind}-*.{ext}")):
            try:
                os.remove(old)  # an older version of this same file
            except OSError:
                pass
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except OSError:
        logging.getLogger(__name__).exception("certificate cache write failed")
    return data


def _shoot(html, selector, viewport, scale, quality, refit_js=None):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", BROWSERS_PATH)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"], env={**os.environ, "HOME": "/tmp"})
        try:
            page = browser.new_page(viewport=viewport, device_scale_factor=scale)
            page.set_content(html, wait_until="networkidle", timeout=30000)
            page.evaluate("document.fonts.ready")
            if refit_js:
                page.evaluate(refit_js)
                page.wait_for_timeout(150)
            return page.locator(selector).screenshot(type="jpeg", quality=quality)
        finally:
            browser.close()


def render_certificate_jpeg(attempt, display_name, scale=2.6, quality=90):
    """A4-landscape JPEG (~2920x2065 px, ~250 dpi) of the exact sheet. JPEG,
    not PNG: the design's paper grain/noise layers made the PNG ~5 MB and
    slow; JPEG keeps every layer at ~1.5 MB. Cached (see _cached)."""
    # Template + DB work happens here, before any browser starts (inside
    # sync_playwright Django raises SynchronousOnlyOperation).
    html = render_to_string("custom_admin/quizzes/_cert_standalone.html",
                            certificate_context(attempt, display_name))
    return _cached(attempt.id, f"cert{scale}q{quality}", html, "jpg",
                   lambda: _shoot(html, ".cert", {"width": 1200, "height": 850}, scale, quality))


def render_certificate_pdf(attempt, display_name):
    """Exactly ONE A4-landscape page (user: "ek hi page par, 2 page nahi,
    blank bhi nahi"). Built from the JPEG with Pillow, so there's nothing for
    a print engine to paginate: one image, one page, page size = 297x210 mm.
    (Chromium's own page.pdf() of this design came out at 9-13 MB because it
    rasterises the gradient/blend layers.)"""
    from PIL import Image

    jpeg = render_certificate_jpeg(attempt, display_name)

    def build():
        img = Image.open(BytesIO(jpeg)).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PDF", resolution=img.width / (297 / 25.4),
                 title=f"Certificate {attempt.certificate_id or ''}")
        return buf.getvalue()

    return _cached(attempt.id, "pdf", jpeg, "pdf", build)


def render_story_jpeg(attempt, display_name, quiz_url, quality=90):
    """1080x1920 WhatsApp/Instagram status card in the v2 design. Embeds the
    real v2 certificate (rendered first) plus a QR to the quiz landing page
    (?src=story), so anyone who sees the status can take the quiz too."""
    cert_jpeg = render_certificate_jpeg(attempt, display_name, scale=1.4, quality=88)
    ctx = certificate_context(attempt, display_name)
    ctx["s_cert_img"] = "data:image/jpeg;base64," + base64.b64encode(cert_jpeg).decode()
    ctx["s_qr"] = _qr_data_uri(quiz_url)
    html = render_to_string("custom_admin/quizzes/_cert_story.html", ctx)
    return _cached(attempt.id, f"story-q{quality}", html, "jpg",
                   lambda: _shoot(html, ".story", {"width": 1080, "height": 1920}, 1, quality,
                                  refit_js="window.sscFitName && window.sscFitName()"))
