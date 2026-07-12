"""Image normalisation for quiz logos/signatures (Part H).

Two independent problems this solves:
  1. normalize()             -- resize on save so every uploaded logo/sign
                                 ends up in a sane, consistent pixel box
                                 regardless of what the admin uploaded.
  2. validate_image_upload() -- reject obviously-bad uploads (too big, wrong
                                 type, too small/blurry) before they ever
                                 reach normalize().
"""
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

LOGO_BOX = (400, 160)
SIGN_BOX = (600, 200)

# Logos/signatures only -- banner has its own, separate BANNER_MAX_BYTES
# below (2MB), since a full 16:10 banner photo legitimately needs more
# headroom than a small logo or a cropped signature.
MAX_UPLOAD_BYTES = 1 * 1024 * 1024  # 1 MB
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MIN_LONG_EDGE_PX = 200


def normalize(django_file, box, strip_white=False):
    im = Image.open(django_file)
    im = ImageOps.exif_transpose(im)  # fix phone-camera rotation
    im = im.convert("RGBA")
    if strip_white:
        # signature photographed on white paper -> make white transparent, then trim
        px = im.getdata()
        im.putdata([(r, g, b, 0) if r > 235 and g > 235 and b > 235 else (r, g, b, a) for r, g, b, a in px])
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
    im.thumbnail(box, Image.LANCZOS)  # preserves aspect ratio, never upscales
    return im  # caller saves as PNG to preserve transparency


def normalized_file(django_file, box, strip_white=False, name_hint="image"):
    """normalize() + wrap the result as a Django-savable PNG ContentFile."""
    im = normalize(django_file, box, strip_white=strip_white)
    buf = BytesIO()
    im.save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name=f"{name_hint}.png")


def validate_image_upload(django_file):
    """Raises ValidationError with a clear message if the upload is unusable.
    Call this BEFORE normalize() — normalize() has no opinion on quality,
    it just resizes whatever it's given."""
    if django_file.size > MAX_UPLOAD_BYTES:
        max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValidationError(f"{django_file.name}: file is bigger than {max_mb}MB — shrink it and try again.")

    content_type = getattr(django_file, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"{django_file.name}: only PNG, JPG/JPEG or WEBP allowed.")

    try:
        django_file.seek(0)
        im = Image.open(django_file)
        im.verify()
        django_file.seek(0)
        im = Image.open(django_file)
        long_edge = max(im.size)
    except Exception:
        raise ValidationError(f"{django_file.name}: this is not a valid image file.")
    finally:
        django_file.seek(0)

    if long_edge < MIN_LONG_EDGE_PX:
        raise ValidationError(
            f"{django_file.name}: image is too small ({long_edge}px) — at least "
            f"{MIN_LONG_EDGE_PX}px is needed, otherwise it will look blurry."
        )


# ------------------------------------------------------------------
# Certificate background (Part J) -- a full-bleed A4-landscape backdrop,
# so the rules are different from logos/signatures: bigger size cap, an
# aspect-ratio requirement (must actually BE landscape A4-ish), and no
# LOGO_BOX/SIGN_BOX-style thumbnailing since shrinking a full-page
# backdrop would make it blurry when printed.
# ------------------------------------------------------------------

BG_MAX_BYTES = 4 * 1024 * 1024  # 4 MB
BG_MIN_WIDTH_PX = 1600
BG_ASPECT_MIN = 1.35
BG_ASPECT_MAX = 1.48  # A4 landscape = 297/210 = 1.414, right in the middle


def validate_certificate_background(django_file):
    """Raises ValidationError for hard rejects (size / type / aspect ratio).
    Returns a warning string (or None) for a soft issue (low resolution) --
    caller decides how to surface that (e.g. messages.warning), since a low
    resolution is a "may look bad" not a "can't use this" situation."""
    if django_file.size > BG_MAX_BYTES:
        raise ValidationError(f"{django_file.name}: file is bigger than 4MB.")

    content_type = getattr(django_file, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"{django_file.name}: only PNG, JPG/JPEG or WEBP allowed.")

    try:
        django_file.seek(0)
        im = Image.open(django_file)
        im.verify()
        django_file.seek(0)
        im = Image.open(django_file)
        width, height = im.size
    except Exception:
        raise ValidationError(f"{django_file.name}: this is not a valid image file.")
    finally:
        django_file.seek(0)

    aspect = (width / height) if height else 0
    if not (BG_ASPECT_MIN <= aspect <= BG_ASPECT_MAX):
        raise ValidationError(
            f"Certificate background must be A4 landscape (aspect ratio ~1.414). "
            f"Yours is {width}:{height}."
        )

    if width < BG_MIN_WIDTH_PX:
        return f"{django_file.name}: width is only {width}px — may look blurry when printed (min {BG_MIN_WIDTH_PX}px recommended)."
    return None


def normalized_certificate_background(django_file):
    """exif_transpose + convert RGB + re-encode as optimized PNG. No resize
    -- unlike normalize(), a full-bleed backdrop should keep its native
    resolution so print quality doesn't suffer."""
    im = Image.open(django_file)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return ContentFile(buf.getvalue(), name="certificate_bg.png")


# ------------------------------------------------------------------
# Quiz banner image -- listing/detail card art. 16:10 crop so it lines
# up with the fixed card box every quiz listing renders it into; unlike
# the certificate background, a wrong-ratio banner isn't "may look
# blurry", it's "will be cropped wrong", so this is a hard reject too.
# ------------------------------------------------------------------

BANNER_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
BANNER_MIN_WIDTH_PX = 1000
BANNER_ASPECT_MIN = 1.55
BANNER_ASPECT_MAX = 1.65  # 16:10 = 1.60


def validate_banner_image(django_file):
    """Raises ValidationError — banner must be 16:10, admin sees exactly why."""
    if django_file.size > BANNER_MAX_BYTES:
        raise ValidationError(f"{django_file.name}: keep the file under 2 MB.")

    content_type = getattr(django_file, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(f"{django_file.name}: only PNG, JPG/JPEG or WEBP allowed.")

    try:
        django_file.seek(0)
        im = Image.open(django_file)
        im.verify()
        django_file.seek(0)
        im = Image.open(django_file)
        w, h = im.size
    except Exception:
        raise ValidationError(f"{django_file.name}: this is not a valid image file.")
    finally:
        django_file.seek(0)

    ratio = (w / h) if h else 0
    if not (BANNER_ASPECT_MIN <= ratio <= BANNER_ASPECT_MAX):
        raise ValidationError(
            f"Banner must be 16:10 (1.60:1). Yours is {ratio:.2f}:1. "
            f"Suggested: 1200×750 px. Current: {w}×{h}"
        )
    if w < BANNER_MIN_WIDTH_PX:
        raise ValidationError(f"Width must be at least {BANNER_MIN_WIDTH_PX}px. Yours is {w}px.")


def normalized_banner(django_file):
    """exif_transpose + re-encode as optimized WEBP (PNG fallback if WEBP
    save fails for any reason). No resize -- banner keeps its uploaded
    resolution, only orientation/format is cleaned up."""
    im = Image.open(django_file)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    buf = BytesIO()
    try:
        im.save(buf, format="WEBP", quality=88, method=6)
        name = "banner.webp"
    except Exception:
        buf = BytesIO()
        im.save(buf, format="PNG", optimize=True)
        name = "banner.png"
    return ContentFile(buf.getvalue(), name=name)
