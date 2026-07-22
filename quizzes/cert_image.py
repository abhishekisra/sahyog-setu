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
CREAM = (250, 248, 239)


def _hex_to_rgb(hex_str, fallback=(200, 169, 81)):
    """'#RRGGBB' -> (r,g,b). Falls back on anything malformed rather than
    raising -- these values come from an admin-editable CharField with no
    format validator, and a bad certificate render is worse than one that
    silently falls back to the old default color."""
    try:
        h = (hex_str or "").lstrip("#")
        if len(h) != 6:
            return fallback
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, TypeError):
        return fallback


def _font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)
    except OSError:
        # A missing/renamed/case-mismatched font file previously 500'd the
        # whole certificate/story download with no fallback at all. Pillow's
        # own bitmap default font can't be resized, but a broken certificate
        # (wrong font, still legible) beats no certificate at all.
        return ImageFont.load_default()


_DEVANAGARI_RANGE = (0x0900, 0x097F)


def _has_devanagari(text):
    return any(_DEVANAGARI_RANGE[0] <= ord(ch) <= _DEVANAGARI_RANGE[1] for ch in text)


_NAME_FONT_FILES = {
    "script": "GreatVibes-Regular.ttf",
    "serif": "Cormorant-Regular.ttf",
    "bold": "Cinzel-Bold.ttf",
}


def _name_font(text, size, font_choice="script"):
    """GreatVibes/Cormorant (the site's cursive/serif "signature" looks for
    the name field, admin-editable via quiz.certificate_name_font) are
    Latin-only -- verified with PIL that a Devanagari codepoint and a
    genuinely unassigned one produce the identical glyph in GreatVibes, i.e.
    every Devanagari character silently falls back to a blank/tofu box.
    Any participant registered with a Hindi name got a certificate with
    their name rendered as a row of identical placeholder boxes instead of
    text. Falls back to Noto Sans Devanagari (bundled, real glyph coverage
    verified) whenever the name isn't representable -- not as elegant, but
    actually legible; this fallback applies regardless of font_choice, since
    none of the three Latin options cover Devanagari. Sized a little
    smaller than the Latin fonts would be at the same character count --
    Noto Sans Devanagari's default glyphs run visually heavier/wider at an
    equal point size."""
    if _has_devanagari(text):
        return _font("NotoSansDevanagari-Bold.ttf", int(size * 0.72))
    return _font(_NAME_FONT_FILES.get(font_choice, _NAME_FONT_FILES["script"]), size)


def _draw_centered(draw, cx, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def _fit_to_width(draw, text, font_loader, start_size, max_width, min_size=22, step=2):
    """font_loader(size) -> ImageFont.FreeTypeFont. Starts at start_size and
    shrinks until `text` fits max_width on one line, or min_size is reached.
    Both the participant name (GreatVibes at a fixed size per length
    bracket, no upper bound on the real name field's length) and the quiz
    title + score line (drawn with _draw_centered, no wrap/width check at
    all) could render past the inner border or canvas edge for a long
    enough real value -- this is the safety net under both."""
    size = start_size
    font = font_loader(size)
    while size > min_size and draw.textbbox((0, 0), text, font=font)[2] > max_width:
        size -= step
        font = font_loader(size)
    return font


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
    with Image.open(img_path) as src:
        im = ImageOps.exif_transpose(src).convert("RGBA")
    im.thumbnail((box_w, box_h), Image.LANCZOS)
    x = int(box_center_x - im.width / 2)
    y = int(box_center_y - im.height / 2)
    base.alpha_composite(im, (x, y))


def _paper_grain(im, sigma=26, alpha=24):
    """Fine cardstock-grain texture across the ENTIRE background -- real
    premium certificate paper is never perfectly flat/smooth the way a
    plain gradient is; this is the texture that actually reads as
    "expensive paper" rather than "a plain digital rectangle".

    Generated at low resolution, upscaled, then Gaussian-blurred -- full-
    resolution per-pixel noise defeats PNG's compression almost entirely
    (a first version of this blew the certificate from ~220KB to ~2.3MB
    and pushed render time up several seconds; even a 1/4-res upscale
    alone still landed north of 1MB, since BICUBIC-interpolated noise is
    still continuously-varying per pixel). The blur is what actually
    restores compressibility -- it smooths local pixel-to-pixel variation
    down to the point PNG's row filters find long, cheap-to-encode runs
    again, while still reading as soft fiber/blotch texture at normal
    viewing size, arguably closer to real paper grain than sharp noise
    would be anyway."""
    from PIL import ImageFilter
    small_size = (im.width // 10, im.height // 10)
    noise = Image.effect_noise(small_size, sigma).convert("L")
    noise = noise.resize(im.size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(radius=6))
    # effect_noise centers around 128 -- darken-only tint (ink-colored,
    # not white speckle) reads as paper fiber, not digital static.
    tint = Image.new("RGBA", im.size, INK + (0,))
    alpha_mask = noise.point(lambda v: max(0, (128 - v)) * alpha // 128)
    tint.putalpha(alpha_mask)
    im.alpha_composite(tint)


def _guilloche_band(im, y_center, band_height, n_waves=5, alpha=34, accent=GOLD):
    """A band of thin offset sine-wave lines -- the classic engraved
    "security paper" texture real certificates/currency use. Drawn on its
    own transparent layer and alpha-composited on, so it reads as subtle
    texture rather than clutter, and only in the top/bottom strips where
    there's no text sitting on top of it."""
    import math
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    w = im.width
    for i in range(n_waves):
        phase = i * (math.pi / n_waves)
        amp = band_height * 0.32
        points = []
        for x in range(0, w + 1, 6):
            yy = y_center + amp * math.sin((x / w) * math.pi * 6 + phase)
            points.append((x, yy))
        ld.line(points, fill=accent + (alpha,), width=2)
    im.alpha_composite(layer)


def _full_guilloche_wash(im, alpha=20, n_families=3, lines_per_family=14, accent=GOLD):
    """A faint interference pattern of overlapping sine-wave families
    across the WHOLE canvas -- the engraved-line texture on currency/
    security paper, at low enough alpha to read as texture, not lines.
    Distinct from _guilloche_band() (which draws a few bold, opaque-ish
    waves in a specific strip) -- this covers the full page at a much
    lower opacity so it can safely sit behind every line of text too."""
    import math
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    w, h = im.size
    for fam in range(n_families):
        base_period = w / (2.2 + fam * 0.9)
        amp = h * (0.05 + fam * 0.015)
        for i in range(lines_per_family):
            phase = (i / lines_per_family) * 2 * math.pi
            y0 = h * (i / lines_per_family)
            points = []
            for x in range(0, w + 1, 8):
                yy = y0 + amp * math.sin((x / base_period) + phase)
                points.append((x, yy))
            ld.line(points, fill=accent + (alpha,), width=1)
    im.alpha_composite(layer)


def _medallion_watermark(im, cx, cy, radius, alpha=30, accent=GOLD):
    """Large, very faint concentric-ring medallion behind the certificate
    body -- an official-document watermark cue, kept light enough (alpha
    ~20/255) to sit behind every line of text without hurting legibility."""
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for r, width in ((radius, 3), (radius * 0.82, 2), (radius * 0.64, 2)):
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent + (alpha,), width=width)
    # Radiating tick marks around the outer ring -- reads as a rosette/seal
    # rather than a plain bullseye.
    import math
    n_ticks = 48
    for i in range(n_ticks):
        angle = (i / n_ticks) * 2 * math.pi
        r1, r2 = radius * 0.9, radius * 1.02
        x1, y1 = cx + r1 * math.cos(angle), cy + r1 * math.sin(angle)
        x2, y2 = cx + r2 * math.cos(angle), cy + r2 * math.sin(angle)
        ld.line([(x1, y1), (x2, y2)], fill=accent + (alpha,), width=2)
    im.alpha_composite(layer)


def _default_background(accent=GOLD, paper=CREAM, pattern="classic", border_style="triple", corners_enabled=True):
    """Guilloche-style frame -- a Pillow equivalent of the SVG fallback
    used in certificate.html when no custom background is uploaded.
    accent/paper come from the quiz's certificate_accent_color/
    certificate_paper_color (admin-editable); pattern is
    certificate_pattern ("classic" or "plain"); border_style is
    certificate_border_style ("triple"/"double"/"single");
    corners_enabled is certificate_corners_enabled -- previously the
    quatrefoil corners were tied to pattern=="classic", now independent.

    Layers, back to front: a soft vertical gradient (the "premium paper"
    cue), a large faint medallion watermark behind the certificate body
    (official-document cue, alpha-composited so it never fights with the
    text sitting on top of it), fine sine-wave guilloche bands in the top/
    bottom strips where no text sits, the gold/ink border (1-3 lines per
    border_style), and optional ornate quatrefoil corner flourishes at the
    inner border's four corners. pattern="plain" skips everything except
    the flat paper color and the border -- for admins who want a cleaner
    look instead of the ornate default."""
    im = Image.new("RGBA", (CANVAS_W, CANVAS_H), paper + (255,))
    d = ImageDraw.Draw(im)

    if pattern != "plain":
        # Vertical gradient: a hair lighter at the very top/bottom edges,
        # a hair deeper through the vertical center -- subtle on purpose,
        # this is meant to read as "not perfectly flat", not as a visible band.
        # Computed as an offset from `paper` rather than a fixed pair of
        # RGB values, so it stays proportionally "a hair lighter/deeper"
        # whatever paper color the admin picked, not always cream-toned.
        top = tuple(min(255, c + 2) for c in paper)
        bottom = tuple(max(0, c - 6) for c in paper)
        for y in range(CANVAS_H):
            t = abs(y - CANVAS_H / 2) / (CANVAS_H / 2)  # 0 at center, 1 at edges
            r = int(bottom[0] + (top[0] - bottom[0]) * t)
            g = int(bottom[1] + (top[1] - bottom[1]) * t)
            b = int(bottom[2] + (top[2] - bottom[2]) * t)
            d.line([(0, y), (CANVAS_W, y)], fill=(r, g, b, 255))

        # Full-page guilloche interference wash + paper grain FIRST, both at
        # ultra-low alpha -- this is the actual "premium paper" texture across
        # the whole certificate, not just isolated bands. Everything drawn
        # after this (medallion, borders, corners) sits on top of it.
        _full_guilloche_wash(im, accent=accent)
        _paper_grain(im)

        # Medallion watermark, centered a little above canvas-middle (roughly
        # behind the name/description block) -- large enough to read as texture
        # across most of the certificate body without concentrating on any one
        # line of text.
        _medallion_watermark(im, CANVAS_W / 2, CANVAS_H * 0.48, radius=CANVAS_H * 0.34, accent=accent)

        # Guilloche wave BANDS (bolder, denser) in the low-text top/bottom
        # strips only (logos/title row, and below the signature line) -- on
        # top of the fainter full-page wash above, for extra texture where
        # there's no text to interfere with.
        _guilloche_band(im, CANVAS_H * 0.045, band_height=60, n_waves=6, alpha=30, accent=accent)
        _guilloche_band(im, CANVAS_H * 0.975, band_height=50, n_waves=6, alpha=30, accent=accent)

    d = ImageDraw.Draw(im)  # re-bind: alpha_composite() above replaced pixel data
    margin_outer = 50
    margin_mid = 84
    margin_inner = 118
    if border_style == "single":
        d.rectangle(
            [margin_outer, margin_outer, CANVAS_W - margin_outer, CANVAS_H - margin_outer],
            outline=accent, width=5,
        )
    elif border_style == "double":
        d.rectangle(
            [margin_outer, margin_outer, CANVAS_W - margin_outer, CANVAS_H - margin_outer],
            outline=accent, width=6,
        )
        d.rectangle(
            [margin_inner, margin_inner, CANVAS_W - margin_inner, CANVAS_H - margin_inner],
            outline=INK, width=3,
        )
    else:  # "triple" (default/classic)
        d.rectangle(
            [margin_outer, margin_outer, CANVAS_W - margin_outer, CANVAS_H - margin_outer],
            outline=accent, width=8,
        )
        d.rectangle(
            [margin_mid, margin_mid, CANVAS_W - margin_mid, CANVAS_H - margin_mid],
            outline=accent, width=2,
        )
        d.rectangle(
            [margin_inner, margin_inner, CANVAS_W - margin_inner, CANVAS_H - margin_inner],
            outline=INK, width=3,
        )

    if corners_enabled:
        # Quatrefoil (4-lobed) flourish at each inner-border corner -- upgraded
        # from a plain diamond outline for a more hand-finished, ornate feel.
        for cx, cy in (
            (margin_inner, margin_inner), (CANVAS_W - margin_inner, margin_inner),
            (margin_inner, CANVAS_H - margin_inner), (CANVAS_W - margin_inner, CANVAS_H - margin_inner),
        ):
            lobe_r = 15
            for dx, dy in ((lobe_r, 0), (-lobe_r, 0), (0, lobe_r), (0, -lobe_r)):
                d.ellipse([cx + dx - lobe_r, cy + dy - lobe_r, cx + dx + lobe_r, cy + dy + lobe_r],
                          outline=accent, width=2)
            d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=accent)
    return im


def render_certificate_image(attempt):
    """Returns PNG bytes for the given (already-issued) QuizAttempt."""
    quiz = attempt.quiz

    accent_rgb = _hex_to_rgb(quiz.certificate_accent_color, fallback=GOLD)
    name_rgb = _hex_to_rgb(quiz.certificate_name_color, fallback=NAME_COLOR)
    paper_rgb = _hex_to_rgb(quiz.certificate_paper_color, fallback=CREAM)
    title_rgb = _hex_to_rgb(quiz.certificate_title_color, fallback=INK)

    if quiz.certificate_background and os.path.exists(quiz.certificate_background.path):
        with Image.open(quiz.certificate_background.path) as src:
            bg = ImageOps.exif_transpose(src).convert("RGBA")
        bg = ImageOps.fit(bg, (CANVAS_W, CANVAS_H), Image.LANCZOS)
    else:
        bg = _default_background(
            accent=accent_rgb, paper=paper_rgb, pattern=quiz.certificate_pattern,
            border_style=quiz.certificate_border_style, corners_enabled=quiz.certificate_corners_enabled,
        )

    draw = ImageDraw.Draw(bg)

    name = attempt.user.get_full_name().strip() or attempt.user.username
    score = round(attempt.percentage)
    cx = CANVAS_W / 2

    # Logos -- position is admin-editable (quiz.logo1_x_pct/y_pct etc, "kahi
    # bhi laga sake") instead of the fixed top-left/top-right spots this used
    # to hardcode; defaults (14/11 and 86/11) match those old fixed spots
    # exactly, so an unedited quiz's certificate doesn't move.
    _paste_contain(bg, quiz.logo_1.path if quiz.logo_1 else None,
                    CANVAS_W * (quiz.logo1_x_pct / 100.0), CANVAS_H * (quiz.logo1_y_pct / 100.0), 300, 130)
    _paste_contain(bg, quiz.logo_2.path if quiz.logo_2 else None,
                    CANVAS_W * (quiz.logo2_x_pct / 100.0), CANVAS_H * (quiz.logo2_y_pct / 100.0), 300, 130)

    # Subtitle uses a lightened tint of the same title color (0.143 chosen so
    # the previous hardcoded default INK (17,17,17) -> (51,51,51) pair is
    # reproduced exactly when title color is left at its own default).
    subtitle_rgb = tuple(min(255, int(c + (255 - c) * 0.143)) for c in title_rgb)
    title_font = _font("Cinzel-Bold.ttf", 130)
    subtitle_font = _font("Cinzel-Bold.ttf", 42)
    _draw_centered(draw, cx, CANVAS_H * 0.075, "CERTIFICATE", title_font, title_rgb)
    _draw_centered(draw, cx, CANVAS_H * 0.155, "OF ACHIEVEMENT", subtitle_font, subtitle_rgb)

    presented_font = _font("Cormorant-Regular.ttf", 46)
    _draw_centered(draw, cx, CANVAS_H * 0.28, "This Certificate is Proudly Presented To", presented_font, MUTED)

    # Name -- admin-adjustable vertical position, same field the print view
    # uses. The per-length-bracket size below assumed Latin/GreatVibes-width
    # characters; _fit_to_width is the safety net for a name long enough (a
    # multi-part name near Django's 150-char first_name+last_name cap
    # measured wider than the canvas at the old floor size) to still
    # overflow past the inner border even at the smallest bracket.
    name_len = len(name)
    name_size = 150 if name_len <= 15 else 120 if name_len <= 25 else 96 if name_len <= 35 else 76
    name_font = _fit_to_width(draw, name, lambda s: _name_font(name, s, quiz.certificate_name_font), name_size, CANVAS_W * 0.8, min_size=40)
    _draw_centered(draw, cx, CANVAS_H * (quiz.name_top_pct / 100.0), name, name_font, name_rgb)

    desc_font = _font("Cormorant-Regular.ttf", 40)
    desc_text = quiz.certificate_text or (
        f"For successfully completing the assessment with outstanding performance."
    )
    _wrap_and_draw_centered(draw, cx, CANVAS_H * 0.52, desc_text, desc_font, (51, 51, 51),
                             max_width=CANVAS_W * 0.58, line_height=54)

    # quiz.title has no length cap that matters here (CharField(max_length=255))
    # and this line was drawn with _draw_centered -- no wrap, no width check --
    # while the description right above it correctly wraps. A long enough
    # real title rendered past the canvas edge.
    score_text = f"{quiz.title} · Score {score}%"
    score_font = _fit_to_width(draw, score_text, lambda s: _font("Cormorant-Regular.ttf", s),
                                38, CANVAS_W * 0.8, min_size=20)
    _draw_centered(draw, cx, CANVAS_H * (quiz.score_top_pct / 100.0), score_text, score_font, accent_rgb)

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

    # Meta line -- was drawn at 0.955*CANVAS_H, which sat almost exactly ON
    # the outer gold border line (_default_background()'s margin_outer=50
    # puts that border at CANVAS_H-50 -- hardcoded here too since this
    # function doesn't share that scope, and a custom certificate_background
    # has no border to align to anyway), so the certificate ID text
    # rendered visually crossed by/merged into the border instead of
    # sitting cleanly in either the frame gap or the outer margin. Moved
    # below the outer border position entirely, with a smaller font so it
    # comfortably clears both the border above it and the canvas edge
    # below it.
    meta_font = _font("Cormorant-Regular.ttf", 22)
    meta_text = f"Certificate ID: {attempt.certificate_id} · Verify at sahyogsetu.in/certificate/verify/{attempt.certificate_id}/"
    _draw_centered(draw, cx, CANVAS_H - 50 + 14, meta_text, meta_font, (136, 136, 136))

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

    # Was drawn at STORY_H-50, which landed almost exactly on the inner gold
    # border line (margin=36 + inner offset 14 puts it at STORY_H-50) --
    # same overlap bug as the landscape certificate's meta line. Moved
    # below the outer border into the true margin strip, smaller font so
    # it clears both the border above and the canvas edge below.
    footer_font = _font("Cormorant-Regular.ttf", 18)
    _draw_centered(d, cx, STORY_H - margin + 10, f"Certificate ID: {attempt.certificate_id}", footer_font, STORY_MUTED)

    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()
