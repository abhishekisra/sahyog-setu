"""Print every real quiz participant + their finished quizzes as JSON
(stdout). Used by the root-only sync that adds quiz participants as
beneficiaries on upliftdata.cloud (2026-11-08). Read-only; prints no
passwords/tokens -- only what a beneficiary record needs."""
import json
from datetime import date

from django.core.management.base import BaseCommand
from zoneinfo import ZoneInfo

from django.utils import timezone

IST = ZoneInfo("Asia/Kolkata")

from quizzes.models import QuizAttempt


def _age(u):
    if u.date_of_birth:
        t = date.today()
        b = u.date_of_birth
        return t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    return u.age


class Command(BaseCommand):
    help = "JSON list of quiz participants (finished, non-demo attempts)"

    def handle(self, *args, **opts):
        rows = (
            QuizAttempt.objects.filter(completed_at__isnull=False, is_demo=False, kind=QuizAttempt.KIND_MAIN)
            .select_related("user", "quiz", "user__district", "user__state", "user__occupation")
            .order_by("completed_at")
        )
        people = {}
        for a in rows:
            u = a.user
            if getattr(u, "user_type", 2) != 2:  # only normal participants
                continue
            p = people.setdefault(u.id, {
                "uid": u.id,
                "name": " ".join(((u.name or "").strip() or f"{u.first_name or ''} {u.last_name or ''}").split()),
                "mobile": (u.mobile or "").strip(),
                "gender": (u.gender or "").strip(),
                "age": _age(u),
                "district": u.district.name if u.district_id else "",
                "state": u.state.state if u.state_id else "",
                "occupation": u.occupation.title if u.occupation_id else "",
                "shg": (u.ngo_shg_name or "").strip(),
                "quizzes": {},
            })
            q = p["quizzes"].setdefault(a.quiz.slug, {
                "title": a.quiz.title,
                "first_date": a.completed_at.astimezone(IST).date().isoformat(),
                "best": 0, "attempts": 0, "passed": False,
            })
            q["attempts"] += 1
            q["best"] = max(q["best"], round(a.percentage or 0))
            q["passed"] = q["passed"] or bool(a.passed)
        self.stdout.write(json.dumps(list(people.values()), ensure_ascii=False))
