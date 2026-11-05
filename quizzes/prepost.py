"""Before-training vs after-training comparison (2026-11-05).

A before-training test is a QuizAttempt with kind="pre" (hidden from
QuizAttempt.objects). For each person who took it, the "after" score is their
FIRST real attempt at the same quiz completed after the pre-test. Only those
pairs are averaged, so the gain compares the same people.
"""
from .models import QuizAttempt


def pre_post_summary(quiz_ids=None, include_demo=False):
    pre = QuizAttempt.all_objects.filter(kind=QuizAttempt.KIND_PRE, completed_at__isnull=False)
    if not include_demo:
        pre = pre.filter(is_demo=False)
    if quiz_ids is not None:
        pre = pre.filter(quiz_id__in=list(quiz_ids))
    rows = {}
    for a in pre.select_related("quiz").order_by("completed_at"):
        post = QuizAttempt.objects.filter(
            user_id=a.user_id, quiz_id=a.quiz_id, completed_at__gt=a.completed_at,
        )
        if not include_demo:
            post = post.filter(is_demo=False)
        post = post.order_by("completed_at").first()
        r = rows.setdefault(a.quiz_id, {"quiz_id": a.quiz_id, "quiz": a.quiz.title, "pre_n": 0, "pre_sum": 0.0,
                                         "pairs": 0, "pair_pre": 0.0, "pair_post": 0.0})
        r["pre_n"] += 1
        r["pre_sum"] += a.percentage
        if post:
            r["pairs"] += 1
            r["pair_pre"] += a.percentage
            r["pair_post"] += post.percentage
    out = []
    for r in rows.values():
        item = {"quiz_id": r["quiz_id"], "quiz": r["quiz"], "pre_count": r["pre_n"],
                "pre_avg": round(r["pre_sum"] / r["pre_n"], 1), "pairs": r["pairs"],
                "pair_pre_avg": None, "pair_post_avg": None, "gain": None}
        if r["pairs"]:
            item["pair_pre_avg"] = round(r["pair_pre"] / r["pairs"], 1)
            item["pair_post_avg"] = round(r["pair_post"] / r["pairs"], 1)
            item["gain"] = round(item["pair_post_avg"] - item["pair_pre_avg"], 1)
        out.append(item)
    return sorted(out, key=lambda x: x["quiz"].lower())
