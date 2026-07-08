"""Certificate ID generation (Part I).

Format: SS-QZ-<year>-<6 char base32>, e.g. SS-QZ-2026-K3F9QX
Retries on collision (astronomically unlikely at this volume, but cheap
to guard anyway since certificate_id is a unique column).
"""
import base64
import secrets

from django.utils import timezone


def generate_certificate_id(model):
    year = timezone.now().year
    for _ in range(10):
        raw = secrets.token_bytes(5)
        b32 = base64.b32encode(raw).decode("ascii").rstrip("=")[:6]
        cert_id = f"SS-QZ-{year}-{b32}"
        if not model.objects.filter(certificate_id=cert_id).exists():
            return cert_id
    raise RuntimeError("Could not generate a unique certificate_id after 10 attempts.")
