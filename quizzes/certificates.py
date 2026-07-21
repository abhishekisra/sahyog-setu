"""Certificate ID generation (Part I).

Format: SAHYOG/<month>/<year>/<sequence>, e.g. SAHYOG/07/26/01 -- the
sequence resets to 01 at the start of each calendar month (confirmed
with the user rather than assumed -- the alternative was a never-
resetting running total).

Retries on collision. The unique constraint on certificate_id is the
real safety net for the rare case of two concurrent requests both
computing the same "next" sequence number for the month; this loop just
makes that recoverable (retry with the next number) instead of a hard
IntegrityError.
"""
from django.utils import timezone


def generate_certificate_id(model):
    now = timezone.now()
    prefix = f"SAHYOG/{now.month:02d}/{now.year % 100:02d}/"

    for _ in range(10):
        existing_ids = model.objects.filter(
            certificate_id__startswith=prefix
        ).values_list("certificate_id", flat=True)
        max_seq = 0
        for cert_id in existing_ids:
            suffix = cert_id[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))
        cert_id = f"{prefix}{max_seq + 1:02d}"
        if not model.objects.filter(certificate_id=cert_id).exists():
            return cert_id
    raise RuntimeError("Could not generate a unique certificate_id after 10 attempts.")
