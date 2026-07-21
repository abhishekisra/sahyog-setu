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
    used in certificate.html when no custom background is uploaded.

    Was a completely flat CREAM rectangle behind two plain outline
    rectangles -- readable, but visibly flatter than the browser preview
    (which gets free depth from CSS box-shadow/gradients Pillow has no
    equivalent for). Adds a subtle vertical gradient (reads as a soft
    vignette, the classic "premium certificate paper" cue), a third
    hairline between the two existing borders so the frame is a proper
    triple-line border instead of two disconnected rectangles, and small
    diamond flourishes at the inner corners -- the kind of hand-finished
    detail that's normally the first thing missing from an auto-generated
    certificate."""
    im = Image.new("RGBA", (CANVAS_W, CANVAS_H), CREAM + (255,))
    d = ImageDraw.Draw(im)
    # Vertical gradient: a hair lighter at the very top/bottom edges,
    # a hair deeper through the vertical center -- subtle on purpose,
    # this is meant to read as "not perfectly flat", not as a visible band.
    top = (252, 250, 242)
    bottom = (244, 240, 226)
    for y in range(CANVAS_H):
        t = abs(y - CANVAS_H / 2) / (CANVAS_H / 2)  # 0 at center, 1 at edges
        r = int(bottom[0] + (top[0] - bottom[0]) * t)
        g = int(bottom[1] + (top[1] - bottom[1]) * t)
        b = int(bottom[2] + (top[2] - bottom[2]) * t)
        d.line([(0, y), (CANVAS_W, y)], fill=(r, g, b, 255))
    margin_outer = 50
    margin_mid = 84
    margin_inner = 118
    d.rectangle(
        [margin_outer, margin_outer, CANVAS_W - margin_outer, CANVAS_H - margin_outer],
        outline=GOLD, width=8,
    )
    d.rectangle(
        [margin_mid, margin_mid, CANVAS_W - margin_mid, CANVAS_H - margin_mid],
        outline=GOLD, width=2,
    )
    d.rectangle(
        [margin_inner, margin_inner, CANVAS_W - margin_inner, CANVAS_H - margin_inner],
        outline=INK, width=3,
    )

    # Small diamond flourish at each of the four inner-border corners.
    flourish_r = 14
    for cx, cy in (
        (margin_inner, margin_inner), (CANVAS_W - margin_inner, margin_inner),
        (margin_inner, CANVAS_H - margin_inner), (CANVAS_W - margin_inner, CANVAS_H - margin_inner),
    ):
        d.polygon(
            [(cx, cy - flourish_r), (cx + flourish_r, cy), (cx, cy + flourish_r), (cx - flourish_r, cy)],
            outline=GOLD, width=3,
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

    # _paste_contain centers the image ON its given y, so with box_h=130 the
    # old center (sign_y - 60) put the box's own bottom edge just 5px below
    # sign_y -- the signature line and printed name were drawn almost right
    # on top of the ink for most real (un-cropped, pre-Part-H) signature
    # uploads on this site. Centering 95px above sign_y instead leaves a
    # real ~30px gap to the line, matching the equivalent padding fix in
    # certificate.html's .sigbox.
    sign_box_w, sign_box_h = 380, 130
    sign_center_y = sign_y - 95
    left_cx, right_cx = CANVAS_W * 0.22, CANVAS_W * 0.78
    _paste_contain(bg, quiz.authority1_sign_image.path if quiz.authority1_sign_image else None,
                    left_cx, sign_center_y, sign_box_w, sign_box_h)
    draw.line([(left_cx - 260, sign_y), (left_cx + 260, sign_y)], fill=INK, width=2)
    _draw_centered(draw, left_cx, sign_y + 15, quiz.authority1_name or "Authorized Signatory", auth_name_font, INK)
    _draw_centered(draw, left_cx, sign_y + 60, quiz.authority1_designation or "Director", auth_desig_font, MUTED)

    _paste_contain(bg, quiz.authority2_sign_image.path if quiz.authority2_sign_image else None,
                    right_cx, sign_center_y, sign_box_w, sign_box_h)
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


# ======================================================================
# Story/Status share image -- vertical 9:16, sized for WhatsApp/Instagram
# Status rather than the landscape certificate above. Bakes the quiz's
# own shareable link into the image itself (as both a scannable QR code
# and plain text) rather than relying on accompanying share-sheet text,
# which many apps silently drop when the share payload includes an image
# file -- the link survives however this image actually gets shared.
# ======================================================================

STORY_W, STORY_H = 1080, 1920
STORY_BG_TOP = (24, 42, 31)      # matches the site's own dark-green gradient
STORY_BG_BOTTOM = (14, 22, 17)
STORY_GOLD = (255, 215, 0)       # #ffd700, the site's current accent
STORY_GOLD_DIM = (201, 162, 39)  # #c9a227
STORY_CREAM = (244, 239, 225)
STORY_MUTED = (173, 194, 177)    # matches --ink-soft elsewhere on the site


def _qr_image(url, scale=8, border=3, fg="black", bg="white"):
    """Same reportlab-encode + Pillow-rasterize approach as
    quizzes.views.quiz_qr_code (kept as a separate, small copy here
    rather than importing from views.py -- views.py imports from this
    module already, and importing back would be circular)."""
    from reportlab.graphics.barcode.qr import QrCodeWidget

    widget = QrCodeWidget(url)
    widget.qr.make()
    matrix = widget.qr.modules
    module_count = widget.qr.moduleCount

    size = (module_count + border * 2) * scale
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    for row in range(module_count):
        for col in range(module_count):
            if matrix[row][col]:
                x0, y0 = (col + border) * scale, (row + border) * scale
                draw.rectangle([x0, y0, x0 + scale - 1, y0 + scale - 1], fill=fg)
    return img


def _draw_check(draw, cx, cy, size, color, width=6):
    """Small checkmark drawn as two line segments instead of a Unicode ✓ --
    Cinzel-Bold has no glyph for U+2713, which was rendering as a visible
    tofu box next to "PASSED" instead of a checkmark."""
    draw.line([
        (cx - size * 0.5, cy),
        (cx - size * 0.15, cy + size * 0.4),
        (cx + size * 0.55, cy - size * 0.5),
    ], fill=color, width=width, joint="curve")


def render_certificate_story_image(attempt, quiz_url):
    """Returns PNG bytes: a 1080x1920 shareable card for WhatsApp/Instagram
    Status. Was a purely abstract score card (big number + QR, no actual
    certificate visual at all) -- when shared, that read as "just a link
    and a score", not a certificate, which is the whole point of a status
    share. Now embeds the REAL rendered certificate (render_certificate_image,
    same landscape PNG "Download as Image" produces) as a bordered thumbnail,
    so what gets shared actually looks like the certificate, plus a QR code
    + printed URL so anyone who sees the story can go take the quiz too."""
    quiz = attempt.quiz
    cx = STORY_W / 2

    im = Image.new("RGB", (STORY_W, STORY_H), STORY_BG_TOP)
    d = ImageDraw.Draw(im)
    for y in range(STORY_H):
        t = y / STORY_H
        r = int(STORY_BG_TOP[0] + (STORY_BG_BOTTOM[0] - STORY_BG_TOP[0]) * t)
        g = int(STORY_BG_TOP[1] + (STORY_BG_BOTTOM[1] - STORY_BG_TOP[1]) * t)
        b = int(STORY_BG_TOP[2] + (STORY_BG_BOTTOM[2] - STORY_BG_TOP[2]) * t)
        d.line([(0, y), (STORY_W, y)], fill=(r, g, b))

    margin = 36
    d.rectangle([margin, margin, STORY_W - margin, STORY_H - margin], outline=STORY_GOLD_DIM, width=3)
    d.rectangle([margin + 14, margin + 14, STORY_W - margin - 14, STORY_H - margin - 14], outline=STORY_GOLD, width=1)

    # Brand row
    seal_r = 40
    seal_cy = 120
    d.ellipse([cx - seal_r, seal_cy - seal_r, cx + seal_r, seal_cy + seal_r], fill=STORY_GOLD)
    seal_font = _font("Cinzel-Bold.ttf", 46)
    _draw_centered(d, cx, seal_cy - 28, "S", seal_font, (18, 32, 25))
    brand_font = _font("Cinzel-Bold.ttf", 38)
    _draw_centered(d, cx, seal_cy + seal_r + 18, "SAHYOG SETU", brand_font, STORY_GOLD)

    # The actual certificate, embedded as a bordered thumbnail -- this IS
    # the certificate, not a stand-in stat card, which is what a "share my
    # certificate" status is supposed to show.
    cert_png = render_certificate_image(attempt)
    cert_im = Image.open(BytesIO(cert_png)).convert("RGB")
    thumb_w = int(STORY_W * 0.87)
    thumb_h = int(thumb_w * cert_im.height / cert_im.width)
    cert_im = cert_im.resize((thumb_w, thumb_h), Image.LANCZOS)

    thumb_top = 250
    frame_pad = 10
    d.rectangle(
        [cx - thumb_w / 2 - frame_pad, thumb_top - frame_pad,
         cx + thumb_w / 2 + frame_pad, thumb_top + thumb_h + frame_pad],
        fill=STORY_CREAM,
    )
    d.rectangle(
        [cx - thumb_w / 2 - frame_pad, thumb_top - frame_pad,
         cx + thumb_w / 2 + frame_pad, thumb_top + thumb_h + frame_pad],
        outline=STORY_GOLD, width=2,
    )
    im.paste(cert_im, (int(cx - thumb_w / 2), thumb_top))

    # Score + pass/complete status just below the certificate thumbnail --
    # keeps the "flex" appeal of a visible number without it being the ONLY
    # thing the card shows.
    score = round(attempt.percentage)
    status_y = thumb_top + thumb_h + frame_pad + 50
    score_font = _font("Cinzel-Bold.ttf", 90)
    _draw_centered(d, cx, status_y, f"{score}%", score_font, STORY_GOLD)

    pass_y = status_y + 120
    pass_font = _font("Cinzel-Bold.ttf", 34)
    if attempt.passed:
        label = "PASSED"
        bbox = d.textbbox((0, 0), label, font=pass_font)
        label_w = bbox[2] - bbox[0]
        _draw_centered(d, cx - 24, pass_y, label, pass_font, STORY_CREAM)
        _draw_check(d, cx + label_w / 2 + 10, pass_y + 22, 34, STORY_GOLD)
    else:
        _draw_centered(d, cx, pass_y, "COMPLETED", pass_font, STORY_CREAM)

    # QR + link -- this is what makes the quiz link travel with the image
    # itself regardless of how it's shared.
    qr = _qr_image(quiz_url, scale=6, border=2)
    qr_size = 220
    qr = qr.resize((qr_size, qr_size), Image.LANCZOS)
    qr_box_pad = 16
    qr_top = pass_y + 90
    d.rectangle(
        [cx - qr_size / 2 - qr_box_pad, qr_top - qr_box_pad,
         cx + qr_size / 2 + qr_box_pad, qr_top + qr_size + qr_box_pad],
        fill=STORY_CREAM,
    )
    im.paste(qr, (int(cx - qr_size / 2), qr_top))

    scan_font = _font("Cormorant-Regular.ttf", 32)
    _draw_centered(d, cx, qr_top + qr_size + qr_box_pad + 18, "Scan to take this quiz", scan_font, STORY_CREAM)

    url_font = _font("Cormorant-Regular.ttf", 26)
    # Long URLs (with ?src=... etc.) wrap ugly at this width -- show just
    # the bare domain, the QR code carries the full link for anyone who
    # actually wants to follow it precisely.
    _draw_centered(d, cx, qr_top + qr_size + qr_box_pad + 60, "sahyogsetu.in", url_font, STORY_GOLD)

    footer_font = _font("Cormorant-Regular.ttf", 24)
    _draw_centered(d, cx, STORY_H - 50, f"Certificate ID: {attempt.certificate_id}", footer_font, STORY_MUTED)

    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()
