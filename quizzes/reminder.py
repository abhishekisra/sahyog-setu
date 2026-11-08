"""'Aapka quiz adhoora hai -- poora karein' reminder (2026-11-08).

A participant who started a quiz and left half-way (tab closed, network
dropped) used to get no hint about it when they came back. This finds
their unfinished attempts so public pages can show a small strip, and the
quiz list can mark the card.

Only counts an attempt that is:
  * a real one (is_demo=False), main quiz (not the pre-test),
  * still open (completed_at is NULL),
  * for a quiz that is live right now, and
  * NOT already followed by a finished attempt of the same quiz (several
    old open rows belong to people who finished on a later try).

"resumable" is True while the attempt is still inside its own time budget
(questions x PER_QUESTION_SERVER_BUDGET). After that QuizTakeView closes the
old row and starts a fresh attempt, so the strip says "phir se shuru karein"
instead of promising they continue where they left off.
"""
from django.utils import timezone

from .models import QuizAttempt, QuestionResponse


def pending_quizzes(user):
    if not getattr(user, "is_authenticated", False):
        return []
    from .views import PER_QUESTION_SERVER_BUDGET  # avoid import cycle

    open_rows = (
        QuizAttempt.objects.filter(
            user=user, completed_at__isnull=True, is_demo=False, kind=QuizAttempt.KIND_MAIN,
        )
        .select_related("quiz")
        .order_by("-started_at")
    )
    out, seen = [], set()
    now = timezone.now()
    for a in open_rows:
        quiz = a.quiz
        if quiz.id in seen or not quiz.status or not quiz.is_live:
            continue
        seen.add(quiz.id)
        if QuizAttempt.objects.filter(
            user=user, quiz=quiz, completed_at__isnull=False, is_demo=False,
            completed_at__gte=a.started_at,
        ).exists():
            continue
        # One-attempt quiz they already PASSED: the card is locked and the
        # landing page only shows the old result, so nothing to complete.
        if quiz.one_attempt_only and QuizAttempt.objects.filter(
            user=user, quiz=quiz, completed_at__isnull=False, is_demo=False, passed=True,
        ).exists():
            continue
        total = len(a.question_ids) or 0
        answered = QuestionResponse.objects.filter(attempt=a).count()
        budget = (total or 1) * PER_QUESTION_SERVER_BUDGET
        out.append({
            "quiz": quiz,
            "attempt_id": a.id,
            "answered": answered,
            "total": total,
            "resumable": (now - a.started_at).total_seconds() <= budget,
        })
    return out


# Pages where the strip would only get in the way (the quiz itself, its
# result, certificates) or isn't the public site at all.
_SKIP_PREFIXES = ("/quiz/", "/admin", "/trainer", "/quiz-analytics", "/static", "/media")


def quiz_reminder(request):
    """Context processor -> {'quiz_pending': [...]} on public pages."""
    try:
        path = request.path or ""
        if path.startswith(_SKIP_PREFIXES) or not request.user.is_authenticated:
            return {}
        if getattr(request.user, "user_type", None) == 1:  # admins
            return {}
        return {"quiz_pending": pending_quizzes(request.user)}
    except Exception:  # never break a page over a reminder
        return {}
