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
        "c_auth1_role": quiz.authority1_designation or "",
        "c_auth2_name": quiz.authority2_name or "Authorized Signatory",
        "c_auth2_role": quiz.authority2_designation or "",
    }


def render_certificate_jpeg(attempt, display_name, scale=2.6, quality=90):
    """A4-landscape JPEG (~2920x2065 px, ~250 dpi) of the exact sheet. JPEG,
    not PNG: the design's paper grain/noise layers made the PNG ~5 MB and
    slow; JPEG keeps every layer at ~1 MB."""
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", BROWSERS_PATH)
    from playwright.sync_api import sync_playwright

    html = render_to_string("custom_admin/quizzes/_cert_standalone.html",
                            certificate_context(attempt, display_name))
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"], env={**os.environ, "HOME": "/tmp"})
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 850}, device_scale_factor=scale)
            page.set_content(html, wait_until="networkidle", timeout=30000)
            page.evaluate("document.fonts.ready")
            img = page.locator(".cert").screenshot(type="jpeg", quality=quality)
        finally:
            browser.close()
    return img


def render_certificate_pdf(attempt, display_name):
    """Exactly ONE A4-landscape page (user: "ek hi page par, 2 page nahi,
    blank bhi nahi"). Built from the JPEG with Pillow, so there's nothing for
    a print engine to paginate: one image, one page, page size = 297x210 mm.
    (Chromium's own page.pdf() of this design came out at 9-13 MB because it
    rasterises the gradient/blend layers.)"""
    from PIL import Image

    img = Image.open(BytesIO(render_certificate_jpeg(attempt, display_name))).convert("RGB")
    dpi = img.width / (297 / 25.4)
    buf = BytesIO()
    img.save(buf, format="PDF", resolution=dpi, title=f"Certificate {attempt.certificate_id or ''}")
    return buf.getvalue()
