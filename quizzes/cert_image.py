"""Certificate rendering as a downloadable/emailable PNG image (Part K).

Deliberately built with Pillow only -- no headless-browser dependency
(Playwright/Chromium) on the production server. Mirrors the same design
already implemented in certificate.html (Part J): a custom
quiz.certificate_background if uploaded, else a built-in guilloche-style
frame; name/score positioned by quiz.name_top_pct / quiz.score_top_pct
(percentage of canvas height) so admin-adjustable positioning stays in
sync between the print/PDF view and this image.
"""
import os
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageOps

# A4 landscape at ~240 DPI -- good quality for screen/email, reasonable file size.
CANVAS_W, CANVAS_H = 2481, 1754

FONTS_DIR = os.path.join(settings.BASE_DIR, "quizzes/fonts")
INK = (17, 17, 17)
MUTED = (85, 85, 85)
GOLD = (200, 169, 81)
NAME_COLOR = (27, 67, 50)
SCORE_COLOR = (110, 90, 32)
CREAM = (250, 248, 239)


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)


def _draw_centered(draw, cx, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def _wrap_and_draw_centered(draw, cx, y, text, font, fill, max_width, line_height):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    for i, line in enumerate(lines):
        _draw_centered(draw, cx, y + i * line_height, line, font, fill)
    return y + len(lines) * line_height


def _paste_contain(base, img_path, box_center_x, box_center_y, box_w, box_h):
    """Paste an image (e.g. logo/signature) centered in a box, preserving
    aspect ratio, never upscaling beyond its own native size."""
    if not img_path or not os.path.exists(img_path):
        return
    im = Image.open(img_path)
    im = ImageOps.exif_transpose(im).convert("RGBA")
    im.thumbnail((box_w, box_h), Image.LANCZOS)
    x = int(box_center_x - im.width / 2)
    y = int(box_center_y - im.height / 2)
    base.alpha_composite(im, (x, y))


def _default_background():
    """Guilloche-style frame -- a Pillow equivalent of the SVG fallback
    used in certificate.html when no custom background is uploaded."""
    im = Image.new("RGBA", (CANVAS_W, CANVAS_H), CREAM + (255,))
    d = ImageDraw.Draw(im)
    margin_outer = 50
    margin_inner = 118
    d.rectangle(
        [margin_outer, margin_outer, CANVAS_W - margin_outer, CANVAS_H - margin_outer],
        outline=GOLD, width=8,
    )
    d.rectangle(
        [margin_inner, margin_inner, CANVAS_W - margin_inner, CANVAS_H - margin_inner],
        outline=INK, width=3,
    )
    return im


def render_certificate_image(attempt):
    """Returns PNG bytes for the given (already-issued) QuizAttempt."""
    quiz = attempt.quiz

    if quiz.certificate_background and os.path.exists(quiz.certificate_background.path):
        bg = Image.open(quiz.certificate_background.path)
        bg = ImageOps.exif_transpose(bg).convert("RGBA")
        bg = ImageOps.fit(bg, (CANVAS_W, CANVAS_H), Image.LANCZOS)
    else:
        bg = _default_background()

    draw = ImageDraw.Draw(bg)

    name = attempt.user.get_full_name().strip() or attempt.user.username
    score = round(attempt.percentage)
    cx = CANVAS_W / 2

    # Logos + title row (~top 6-16%)
    _paste_contain(bg, quiz.logo_1.path if quiz.logo_1 else None, CANVAS_W * 0.14, CANVAS_H * 0.11, 300, 130)
    _paste_contain(bg, quiz.logo_2.path if quiz.logo_2 else None, CANVAS_W * 0.86, CANVAS_H * 0.11, 300, 130)

    title_font = _font("Cinzel-Bold.ttf", 130)
    subtitle_font = _font("Cinzel-Bold.ttf", 42)
    _draw_centered(draw, cx, CANVAS_H * 0.075, "CERTIFICATE", title_font, INK)
    _draw_centered(draw, cx, CANVAS_H * 0.155, "OF ACHIEVEMENT", subtitle_font, (51, 51, 51))

    presented_font = _font("Cormorant-Regular.ttf", 46)
    _draw_centered(draw, cx, CANVAS_H * 0.28, "This Certificate is Proudly Presented To", presented_font, MUTED)

    # Name -- admin-adjustable vertical position, same field the print view uses.
    name_len = len(name)
    name_size = 150 if name_len <= 15 else 120 if name_len <= 25 else 96 if name_len <= 35 else 76
    name_font = _font("GreatVibes-Regular.ttf", name_size)
    _draw_centered(draw, cx, CANVAS_H * (quiz.name_top_pct / 100.0), name, name_font, NAME_COLOR)

    desc_font = _font("Cormorant-Regular.ttf", 40)
    desc_text = quiz.certificate_text or (
        f"For successfully completing the assessment with outstanding performance."
    )
    _wrap_and_draw_centered(draw, cx, CANVAS_H * 0.52, desc_text, desc_font, (51, 51, 51),
                             max_width=CANVAS_W * 0.58, line_height=54)

    score_font = _font("Cormorant-Regular.ttf", 38)
    _draw_centered(draw, cx, CANVAS_H * (quiz.score_top_pct / 100.0),
                    f"{quiz.title} · Score {score}%", score_font, SCORE_COLOR)

    # Signatures (~84%)
    sign_y = CANVAS_H * 0.84
    auth_name_font = _font("Cinzel-Bold.ttf", 34)
    auth_desig_font = _font("Cormorant-Regular.ttf", 28)

    left_cx, right_cx = CANVAS_W * 0.22, CANVAS_W * 0.78
    _paste_contain(bg, quiz.authority1_sign_image.path if quiz.authority1_sign_image else None,
                    left_cx, sign_y - 60, 380, 130)
    draw.line([(left_cx - 260, sign_y), (left_cx + 260, sign_y)], fill=INK, width=2)
    _draw_centered(draw, left_cx, sign_y + 15, quiz.authority1_name or "Authorized Signatory", auth_name_font, INK)
    _draw_centered(draw, left_cx, sign_y + 60, quiz.authority1_designation or "Director", auth_desig_font, MUTED)

    _paste_contain(bg, quiz.authority2_sign_image.path if quiz.authority2_sign_image else None,
                    right_cx, sign_y - 60, 380, 130)
    draw.line([(right_cx - 260, sign_y), (right_cx + 260, sign_y)], fill=INK, width=2)
    _draw_centered(draw, right_cx, sign_y + 15, quiz.authority2_name or "Verified By", auth_name_font, INK)
    _draw_centered(draw, right_cx, sign_y + 60, quiz.authority2_designation or "Admin", auth_desig_font, MUTED)

    # Meta line (~96%)
    meta_font = _font("Cormorant-Regular.ttf", 26)
    meta_text = f"Certificate ID: {attempt.certificate_id} · Verify at sahyogsetu.in/certificate/verify/{attempt.certificate_id}/"
    _draw_centered(draw, cx, CANVAS_H * 0.955, meta_text, meta_font, (136, 136, 136))

    buf = BytesIO()
    bg.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()
