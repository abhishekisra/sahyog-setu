import csv
from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from quizzes.models import Quizzes, QuizAttempt, QuestionResponse
from .models import Partner, PartnerQuizAccess


# ======================================================================
# Auth -- a fully separate identity system from django.contrib.auth (see
# Partner model docstring). Only ever reads/writes request.session['partner_id'],
# never touches request.user or login()/logout(), so a partner session and
# an admin/team session can coexist in the same browser without either
# clobbering the other, and there is no path from one identity to the other.
# ======================================================================

def _get_current_partner(request):
    partner_id = request.session.get("partner_id")
    if not partner_id:
        return None
    return Partner.objects.filter(pk=partner_id, is_active=True).first()


def partner_required(view_func):
    """Every partner-facing view (except login) is wrapped in this.
    Redirects to login rather than 403/404 -- unlike get_partner_quiz_or_404
    below, simply not being logged in isn't a data-isolation concern, just
    an auth gate."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        partner = _get_current_partner(request)
        if not partner:
            return redirect("partner_login")
        request.partner = partner
        return view_func(request, *args, **kwargs)
    return wrapper


def get_partner_quiz_or_404(request, quiz_id):
    """The single choke point every partner analytics view goes through --
    confirms request.partner actually has a PartnerQuizAccess row for this
    EXACT quiz_id before returning it. This is what stops a partner from
    seeing another partner's (or any unassigned) quiz's data just by
    editing the quiz_id in the URL -- every view below calls this first and
    only ever queries QuizAttempt/QuestionResponse through the quiz it
    returns, never an unchecked quiz_id from the URL directly. Raises
    Http404 (not a redirect/403 message) so a probing request learns
    nothing about whether the quiz id even exists."""
    quiz = get_object_or_404(Quizzes, pk=quiz_id)
    if not PartnerQuizAccess.objects.filter(partner=request.partner, quiz=quiz).exists():
        raise Http404("Quiz not found")
    return quiz


class PartnerLoginView(View):

    def get(self, request):
        if _get_current_partner(request):
            return redirect("partner_quiz_select")
        return render(request, "partners/login.html")

    def post(self, request):
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # iexact -- mobile keyboards auto-capitalize the first letter of a
        # plain text field by default (autocapitalize="off" on the input
        # now stops that going forward, but this also protects against it
        # for anyone who already has the page cached, and against a
        # partner just habitually typing their username differently).
        # Passwords are still matched exactly via check_password below --
        # only the username lookup is case-insensitive.
        partner = Partner.objects.filter(username__iexact=username, is_active=True).first()
        if not partner or not partner.check_password(password):
            return render(request, "partners/login.html", {
                "error": "Invalid username or password.",
                "username": username,
            })

        request.session["partner_id"] = partner.id
        return redirect("partner_quiz_select")


class PartnerLogoutView(View):

    def get(self, request):
        request.session.pop("partner_id", None)
        return redirect("partner_login")


@partner_required
def partner_quiz_select(request):
    """Entry point right after login (and the landing URL for /partner/).
    Exactly 1 assigned quiz -> skip straight to its dashboard, no extra
    click. 0 or 2+ -> this list page (0 shows a friendly empty state
    instead of an empty table)."""
    access = list(
        PartnerQuizAccess.objects.filter(partner=request.partner)
        .select_related("quiz").order_by("quiz__title")
    )
    if len(access) == 1:
        return redirect("partner_overview", quiz_id=access[0].quiz_id)
    return render(request, "partners/quiz_select.html", {"access": access})


# ======================================================================
# Dashboard -- every view below starts with get_partner_quiz_or_404, and
# every QuizAttempt/QuestionResponse query is filtered by that specific
# quiz. is_demo=False + completed_at__isnull=False matches the same
# exclusion the admin-side analytics already use (see quizzes.views.
# _analytics_base_qs) -- a partner should never see seeded demo rows or
# still-in-progress attempts inflating their numbers.
# ======================================================================

def _completed_attempts(quiz):
    return QuizAttempt.objects.filter(quiz=quiz, completed_at__isnull=False, is_demo=False)


@partner_required
def partner_overview(request, quiz_id):
    quiz = get_partner_quiz_or_404(request, quiz_id)

    all_attempts = QuizAttempt.objects.filter(quiz=quiz, is_demo=False)
    completed = all_attempts.filter(completed_at__isnull=False)

    total_started = all_attempts.count()
    total_completed = completed.count()
    completion_pct = round(total_completed / total_started * 100, 1) if total_started else 0

    agg = completed.aggregate(
        participants=Count("user", distinct=True),
        avg_pct=Avg("percentage"),
        passed=Count("id", filter=Q(passed=True)),
    )
    passed = agg["passed"] or 0
    failed = total_completed - passed

    return render(request, "partners/overview.html", {
        "partner": request.partner,
        "quiz": quiz,
        "active_tab": "overview",
        "total_participants": agg["participants"] or 0,
        "avg_pct": round(agg["avg_pct"] or 0, 1),
        "completion_pct": completion_pct,
        "total_completed": total_completed,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total_completed * 100, 1) if total_completed else 0,
    })


PARTICIPANTS_PER_PAGE = 25
SORT_WHITELIST = {
    "name": "user__name",
    "-name": "-user__name",
    "score": "percentage",
    "-score": "-percentage",
    "time": "time_taken_seconds",
    "-time": "-time_taken_seconds",
    "date": "completed_at",
    "-date": "-completed_at",
}


def _participants_queryset(request, quiz):
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "-date")

    rows = _completed_attempts(quiz).select_related("user", "user__state", "user__district")

    if q:
        rows = rows.filter(
            Q(user__name__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
            | Q(user__mobile__icontains=q) | Q(user__state__state__icontains=q)
            | Q(user__district__name__icontains=q)
        )

    rows = rows.order_by(SORT_WHITELIST.get(sort, "-completed_at"))
    return rows, q, sort


@partner_required
def partner_participants(request, quiz_id):
    quiz = get_partner_quiz_or_404(request, quiz_id)
    rows, q, sort = _participants_queryset(request, quiz)

    paginator = Paginator(rows, PARTICIPANTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "partners/participants.html", {
        "partner": request.partner,
        "quiz": quiz,
        "active_tab": "participants",
        "page_obj": page,
        "q": q,
        "sort": sort,
    })


@partner_required
def partner_participants_export(request, quiz_id):
    quiz = get_partner_quiz_or_404(request, quiz_id)
    rows, _, _ = _participants_queryset(request, quiz)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{quiz.slug}-participants.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "State", "District", "Score", "Percentage", "Time Taken (s)", "Attempt Date"])
    for a in rows:
        writer.writerow([
            a.user.get_full_name() or a.user.name or a.user.mobile,
            a.user.state.state if a.user.state else "",
            a.user.district.name if a.user.district else "",
            f"{a.score}/{a.total_questions}",
            round(a.percentage, 1),
            a.time_taken_seconds or "",
            a.completed_at.strftime("%Y-%m-%d %H:%M") if a.completed_at else "",
        ])
    return response


@partner_required
def partner_regions(request, quiz_id):
    quiz = get_partner_quiz_or_404(request, quiz_id)
    attempts = _completed_attempts(quiz)

    state_rows = list(
        attempts.values("user__state_id", "user__state__state")
        .annotate(n=Count("id"), avg_pct=Avg("percentage"))
        .order_by("-n")
    )
    max_n = max((r["n"] for r in state_rows), default=1)
    for r in state_rows:
        r["avg_pct"] = round(r["avg_pct"] or 0, 1)
        r["bar_pct"] = round(r["n"] / max_n * 100, 1) if max_n else 0

    selected_state_id = request.GET.get("state")
    district_rows = []
    selected_state_name = None
    if selected_state_id:
        district_rows = list(
            attempts.filter(user__state_id=selected_state_id)
            .values("user__district_id", "user__district__name")
            .annotate(n=Count("id"), avg_pct=Avg("percentage"))
            .order_by("-n")
        )
        max_dn = max((r["n"] for r in district_rows), default=1)
        for r in district_rows:
            r["avg_pct"] = round(r["avg_pct"] or 0, 1)
            r["bar_pct"] = round(r["n"] / max_dn * 100, 1) if max_dn else 0
        match = next((r for r in state_rows if str(r["user__state_id"]) == str(selected_state_id)), None)
        selected_state_name = match["user__state__state"] if match else None

    return render(request, "partners/regions.html", {
        "partner": request.partner,
        "quiz": quiz,
        "active_tab": "regions",
        "state_rows": state_rows,
        "district_rows": district_rows,
        "selected_state_id": selected_state_id,
        "selected_state_name": selected_state_name,
    })


@partner_required
def partner_questions(request, quiz_id):
    quiz = get_partner_quiz_or_404(request, quiz_id)

    question_rows = []
    for question in quiz.questions.all().order_by("id"):
        responses = QuestionResponse.objects.filter(
            question=question, attempt__quiz=quiz, attempt__completed_at__isnull=False, attempt__is_demo=False,
        )
        total = responses.count()
        correct = responses.filter(is_correct=True).count()

        option_counts = dict(
            responses.values_list("selected_option").annotate(n=Count("id"))
        )
        options_by_number = dict(question.options_list)
        option_breakdown = []
        for n, label in options_by_number.items():
            count = option_counts.get(str(n), 0)
            option_breakdown.append({
                "label": label,
                "is_correct": n == question.correct_option,
                "count": count,
                "pct": round(count / total * 100, 1) if total else 0,
            })
        skipped = option_counts.get("", 0)

        question_rows.append({
            "question": question,
            "total": total,
            "correct": correct,
            "pct_correct": round(correct / total * 100, 1) if total else 0,
            "pct_wrong": round((total - correct - skipped) / total * 100, 1) if total else 0,
            "skipped": skipped,
            "option_breakdown": option_breakdown,
        })

    return render(request, "partners/questions.html", {
        "partner": request.partner,
        "quiz": quiz,
        "active_tab": "questions",
        "question_rows": question_rows,
    })


@partner_required
def partner_attempt_detail(request, quiz_id, attempt_id):
    quiz = get_partner_quiz_or_404(request, quiz_id)
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("user"),
        pk=attempt_id, quiz=quiz, completed_at__isnull=False,
    )
    responses = attempt.responses.select_related("question").order_by("id")

    def option_label(opt_str, options_by_number):
        if not opt_str:
            return "Skipped"
        try:
            n = int(opt_str)
        except ValueError:
            return opt_str
        return options_by_number.get(n, f"Option {n}")

    rows = []
    prev_time = attempt.started_at
    for r in responses:
        options_by_number = dict(r.question.options_list) if r.question else {}
        if r.answered_at:
            time_taken_seconds = round((r.answered_at - prev_time).total_seconds())
            prev_time = r.answered_at
        else:
            # answered_at didn't exist yet when this attempt was answered --
            # no fabricated number, the template shows "N/A".
            time_taken_seconds = None
        rows.append({
            "question_text": r.question_text_snapshot,
            "selected_label": option_label(r.selected_option, options_by_number),
            "correct_label": option_label(r.correct_option, options_by_number),
            "is_correct": r.is_correct,
            "explanation": r.explanation_snapshot,
            "time_taken_seconds": time_taken_seconds,
        })

    return render(request, "partners/attempt_detail.html", {
        "partner": request.partner,
        "quiz": quiz,
        "active_tab": "participants",
        "attempt": attempt,
        "rows": rows,
    })


# ======================================================================
# Admin-side "Manage Partners" CRUD -- routed under /admin/ via
# custom_admin/urls.py, same staff_member_required gate the quiz analytics
# admin views use (Partner accounts are credentials for external
# organizations, so this gets the stronger is_staff check, not the plain
# request.user.is_authenticated some older admin CRUD pages in this
# codebase use). Never touches the partner-facing session key
# (session['partner_id']) -- this is plain django.contrib.auth admin auth,
# completely separate from partner login, same as every other /admin/ page.
# ======================================================================

@method_decorator(staff_member_required(login_url="adminLogin"), name="dispatch")
class ManagePartnersView(View):

    def get(self, request):
        partners = (
            Partner.objects.all()
            .annotate(quiz_count=Count("quiz_access"))
            .order_by("-created_at")
        )
        quizzes = Quizzes.objects.all().order_by("title")
        return render(request, "custom_admin/partners.html", {
            "partners": partners,
            "quizzes": quizzes,
        })

    def post(self, request):
        name = request.POST.get("name", "").strip()
        organization = request.POST.get("organization", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        quiz_ids = request.POST.getlist("quiz_ids")

        if not name or not username or not password:
            messages.error(request, "Name, username, and password are required.")
            return redirect("adminManagePartners")

        if Partner.objects.filter(username__iexact=username).exists():
            messages.error(request, "This username is already taken.")
            return redirect("adminManagePartners")

        partner = Partner(name=name, organization=organization, username=username)
        partner.set_password(password)
        partner.save()

        for quiz_id in quiz_ids:
            PartnerQuizAccess.objects.get_or_create(partner=partner, quiz_id=quiz_id)

        messages.success(request, "Partner added successfully.")
        return redirect("adminManagePartners")


@staff_member_required(login_url="adminLogin")
def updatePartner(request, id):
    partner = get_object_or_404(Partner, pk=id)

    name = request.POST.get("name", "").strip()
    organization = request.POST.get("organization", "").strip()
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    is_active = request.POST.get("is_active") == "1"
    quiz_ids = set(request.POST.getlist("quiz_ids"))

    if not name or not username:
        messages.error(request, "Name and username are required.")
        return redirect("adminManagePartners")

    if Partner.objects.filter(username__iexact=username).exclude(pk=partner.pk).exists():
        messages.error(request, "This username is already taken by another partner.")
        return redirect("adminManagePartners")

    partner.name = name
    partner.organization = organization
    partner.username = username
    partner.is_active = is_active
    if password:
        partner.set_password(password)
    partner.save()

    existing_ids = set(str(qid) for qid in partner.quiz_access.values_list("quiz_id", flat=True))
    PartnerQuizAccess.objects.filter(partner=partner, quiz_id__in=(existing_ids - quiz_ids)).delete()
    for quiz_id in (quiz_ids - existing_ids):
        PartnerQuizAccess.objects.get_or_create(partner=partner, quiz_id=quiz_id)

    messages.success(request, "Partner updated successfully.")
    return redirect("adminManagePartners")


@staff_member_required(login_url="adminLogin")
def togglePartnerActive(request):
    partner_id = request.POST.get("partner_id")
    partner = get_object_or_404(Partner, pk=partner_id)
    partner.is_active = not partner.is_active
    partner.save(update_fields=["is_active"])
    messages.success(request, f"Partner {'activated' if partner.is_active else 'deactivated'}.")
    return redirect("adminManagePartners")
