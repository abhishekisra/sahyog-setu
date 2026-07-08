"""Email delivery for quiz certificates (Part L)."""
from django.core.mail import EmailMessage

from .cert_image import render_certificate_image


def send_certificate_email(attempt, request=None):
    """Renders the certificate PNG and emails it to attempt.user.email.
    Returns (ok: bool, message: str) -- never raises, so a bad SMTP config
    surfaces as a clean user-facing message instead of a 500."""
    user = attempt.user
    if not user.email:
        return False, "Aapke account mein email address nahi hai."

    quiz = attempt.quiz
    verify_url = f"https://sahyogsetu.in/certificate/verify/{attempt.certificate_id}/"

    subject = f"Your Certificate — {quiz.title}"
    body = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        f"Congratulations on completing \"{quiz.title}\" with a score of "
        f"{round(attempt.percentage)}%! Your certificate is attached.\n\n"
        f"Verify anytime at: {verify_url}\n\n"
        f"— Sahyog Setu Team"
    )

    try:
        image_bytes = render_certificate_image(attempt)
        email = EmailMessage(subject=subject, body=body, to=[user.email])
        email.attach(f"certificate_{attempt.certificate_id}.png", image_bytes, "image/png")
        email.send(fail_silently=False)
        return True, f"Certificate {user.email} par bhej diya gaya."
    except Exception as e:
        return False, f"Email bhejne mein dikkat hui: {e}"
