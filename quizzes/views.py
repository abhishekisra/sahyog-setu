import csv
import html
import random
import urllib.parse
from datetime import timedelta
from io import BytesIO

from django.db import transaction, IntegrityError
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Max, Q
from django.db.models.functions import TruncDate
from django.core.exceptions import ValidationError
from accounts.models import User
from .certificates import generate_certificate_id
from .cert_image import render_certificate_image
from .imaging import validate_image_upload, validate_certificate_background, validate_banner_image
from .models import Questions, Quizzes, QuizAttempt, QuestionResponse, Language, QuizTranslation, QuestionTranslation
from .question_import import SAMPLE_ROWS, normalize_correct_option, parse_upload, validate_rows
from .ai_generate import AIGenerationError, MAX_QUESTIONS_PER_BATCH, generate_questions

# Every quiz now runs a fixed 20s-per-question timer (forward-only, no
# going back) instead of quiz.quiz_time as an overall countdown -- that
# field was a longstanding source of bad data (admins had no unit hint on
# the entry field, so values like 1500 ended up meaning 1500 *minutes*).
# +5s/question is network/render slack for the server-side safety check
# below; the client-side 20s countdown is what actually paces the user.
PER_QUESTION_SECONDS = 20
PER_QUESTION_SERVER_BUDGET = 25

# Each question is worth a flat 10 marks -- attempt.score/total_questions
# stay as raw correct-answer COUNTS everywhere internally (percentage,
# pass_threshold, leaderboard ordering, analytics, the CSV export column)
# so none of that math or any existing report changes meaning; this is
# purely the multiplier used wherever a participant-facing mark total is
# displayed.
MARKS_PER_QUESTION = 10



class QuizzesView(View):

    def get(self, request):
        if request.user.is_authenticated:
            quizzes = (
                Quizzes.objects.all()
                .order_by("-id")
                .annotate(
                    question_count=Count("questions", distinct=True),
                    attempt_count=Count("attempts", distinct=True),
                )
            )
            stats = {
                "total": len(quizzes),
                "active": sum(1 for q in quizzes if q.status),
                "questions": sum(q.question_count for q in quizzes),
                "attempts": sum(q.attempt_count for q in quizzes),
            }
            return render(request, "custom_admin/quizzes/quizzes.html", {"quizzes": quizzes, "stats": stats})

        else:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")



class QuizView(View):

    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/quizzes/add-quiz.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        # Upload validation (Part H) -- max 1MB, png/jpg/jpeg/webp only,
        # min 200px long edge. Runs BEFORE the quiz is created, so a bad
        # image never reaches Quizzes.save()'s normalize() step at all.
        # "image" (banner) deliberately excluded here -- it has its own,
        # more permissive validate_banner_image() check below (2MB, 16:10
        # ratio required), which would conflict with this 1MB logo/signature cap.
        for field_name in ("logo_1", "logo_2", "authority1_sign_image", "authority2_sign_image"):
            f = request.FILES.get(field_name)
            if f:
                try:
                    validate_image_upload(f)
                except ValidationError as e:
                    messages.error(request, e.message)
                    return render(request, "custom_admin/quizzes/add-quiz.html")

        # Certificate background validation (Part J) -- different rules
        # (aspect ratio, bigger size cap) since it's a full-page backdrop,
        # not a logo. Low resolution is a warning, not a hard reject.
        bg_file = request.FILES.get("certificate_background")
        if bg_file:
            try:
                warning = validate_certificate_background(bg_file)
                if warning:
                    messages.warning(request, warning)
            except ValidationError as e:
                messages.error(request, e.message)
                return render(request, "custom_admin/quizzes/add-quiz.html")

        # Banner aspect-ratio validation -- 16:10, hard reject (wrong ratio
        # means the listing card will crop it wrong, not just "look blurry").
        banner_file = request.FILES.get("image")
        if banner_file:
            try:
                validate_banner_image(banner_file)
            except ValidationError as e:
                messages.error(request, e.message)
                return render(request, "custom_admin/quizzes/add-quiz.html")

        try:
            # ====================== # CREATE QUIZ # ======================
            quiz = Quizzes.objects.create( title = request.POST.get("title"),
                                    description = request.POST.get("description"),
                                    certificate_text = request.POST.get("certificate_text"),
                                    image = request.FILES.get("image"),
                                    logo_1 = request.FILES.get("logo_1"),
                                    logo_2 = request.FILES.get("logo_2"),
                                    authority1_name = request.POST.get("authority1_name"),
                                    authority1_designation = request.POST.get("authority1_designation"),
                                    authority1_sign_image = request.FILES.get("authority1_sign_image"),
                                    authority2_name = request.POST.get("authority2_name"),
                                    authority2_designation = request.POST.get("authority2_designation"),
                                    authority2_sign_image = request.FILES.get("authority2_sign_image"),
                                    quiz_time = request.POST.get("quiz_time"),
                                    certificate_background = request.FILES.get("certificate_background"),
                                    name_top_pct = request.POST.get("name_top_pct") or 42.0,
                                    score_top_pct = request.POST.get("score_top_pct") or 64.0,
                                    status = request.POST.get("status") == "1" )
                                    
            # ====================== # GET QUESTIONS DATA # ====================== 
            questions = request.POST.getlist("question[]") 
            option_1 = request.POST.getlist("option_1[]") 
            option_2 = request.POST.getlist("option_2[]") 
            option_3 = request.POST.getlist("option_3[]") 
            option_4 = request.POST.getlist("option_4[]") 
            correct_option = request.POST.getlist("correct_option[]")
            # ====================== # SAVE QUESTIONS # ====================== 
            question_list = [] 
            for i in range(len(questions)): 
                if not questions[i].strip(): 
                    continue 
                question_list.append(Questions( quiz = quiz, question = questions[i], option_1 = option_1[i], option_2 = option_2[i], option_3 = option_3[i], option_4 = option_4[i], correct_option = int(correct_option[i]) ) )
            Questions.objects.bulk_create(question_list)
            messages.success(request, "Quiz created successfully")
            if not question_list:
                # No questions typed manually -- straight to bulk import
                # instead of the list, so an admin who plans to upload a
                # CSV/XLSX of questions doesn't have to go find the quiz
                # again first.
                messages.info(request, "Now bulk-import questions, or add them one by one below.")
                return redirect("adminImportQuestions", id=quiz.id)
            return redirect("adminQuizzes")
        except Exception as e: 
            print("Quiz Create Error:", e) 
            messages.error(request, "Something went wrong.") 
            return redirect("adminQuizzes")
            

    
class EditQuizView(View):

    def get(self, request, id):

        if not request.user.is_authenticated:
            messages.error(request,"Login required")
            return redirect("adminLogin")

        quiz = Quizzes.objects.get(id=id)

        # Editing questions deletes+recreates the whole set (see post()
        # below) -- anyone mid-attempt right now would silently hold dead
        # question IDs. Not blocked, just surfaced, so the admin can choose
        # to wait.
        live_attempt_count = QuizAttempt.objects.filter(
            quiz=quiz, completed_at__isnull=True, is_demo=False
        ).count()

        # Same strip_tags+unescape treatment as the public listing's
        # short_desc (see quiz_list below) -- the raw description is rich
        # HTML (<p>/<ul>/<strong>...), and this preview card is plain text,
        # so rendering it unstripped just dumps literal tags on the admin.
        preview_desc = html.unescape(strip_tags(quiz.description or ""))
        preview_desc = Truncator(preview_desc.strip()).chars(100)

        # Warns the admin below (see edit-quiz.html) that saving this form
        # deletes+recreates every Questions row, which cascades onto
        # QuestionTranslation too -- surfaced here for the same reason as
        # live_attempt_count above.
        translated_lang_count = (
            QuestionTranslation.objects.filter(question__quiz=quiz)
            .exclude(question_text="")
            .values("language_id")
            .distinct()
            .count()
        )

        return render(request, "custom_admin/quizzes/edit-quiz.html", {
            "quiz": quiz,
            "live_attempt_count": live_attempt_count,
            "preview_desc": preview_desc,
            "translated_lang_count": translated_lang_count,
        })


    def post(self, request, id):

        # Upload validation (Part H) -- same rule as QuizView.post: reject
        # before anything is touched, so a bad image can't half-save.
        # "image" (banner) excluded -- see QuizView.post for why.
        for field_name in ("logo_1", "logo_2", "authority1_sign_image", "authority2_sign_image"):
            f = request.FILES.get(field_name)
            if f:
                try:
                    validate_image_upload(f)
                except ValidationError as e:
                    messages.error(request, e.message)
                    quiz = get_object_or_404(Quizzes, id=id)
                    return render(request, "custom_admin/quizzes/edit-quiz.html", {"quiz": quiz})

        # Certificate background validation (Part J)
        bg_file = request.FILES.get("certificate_background")
        if bg_file:
            try:
                warning = validate_certificate_background(bg_file)
                if warning:
                    messages.warning(request, warning)
            except ValidationError as e:
                messages.error(request, e.message)
                quiz = get_object_or_404(Quizzes, id=id)
                return render(request, "custom_admin/quizzes/edit-quiz.html", {"quiz": quiz})

        # Banner aspect-ratio validation (same rule as QuizView.post)
        banner_file = request.FILES.get("image")
        if banner_file:
            try:
                validate_banner_image(banner_file)
            except ValidationError as e:
                messages.error(request, e.message)
                quiz = get_object_or_404(Quizzes, id=id)
                return render(request, "custom_admin/quizzes/edit-quiz.html", {"quiz": quiz})

        try:
            quiz = Quizzes.objects.get(id=id)

            # Update quiz
            quiz.title = request.POST.get("title")
            quiz.description = request.POST.get("description")
            quiz.certificate_text = request.POST.get("certificate_text")
            quiz.status = request.POST.get("status")
            quiz.quiz_time = request.POST.get("quiz_time")
            quiz.name_top_pct = request.POST.get("name_top_pct") or quiz.name_top_pct
            quiz.score_top_pct = request.POST.get("score_top_pct") or quiz.score_top_pct
            if request.FILES.get("image"):
                quiz.image = request.FILES.get("image")
            if request.FILES.get("logo_1"):
                quiz.logo_1 = request.FILES.get("logo_1")
            if request.FILES.get("logo_2"):
                quiz.logo_2 = request.FILES.get("logo_2")
            if request.FILES.get("authority1_sign_image"):
                quiz.authority1_sign_image = request.FILES.get("authority1_sign_image")
            if request.FILES.get("authority2_sign_image"):
                quiz.authority2_sign_image = request.FILES.get("authority2_sign_image")
            if request.FILES.get("certificate_background"):
                quiz.certificate_background = request.FILES.get("certificate_background")
            quiz.save()


            # ❌ Remove all old questions
            Questions.objects.filter(quiz=quiz).delete()


            # ✅ Get new questions
            questions = request.POST.getlist("question[]")
            option_1 = request.POST.getlist("option_1[]")
            option_2 = request.POST.getlist("option_2[]")
            option_3 = request.POST.getlist("option_3[]")
            option_4 = request.POST.getlist("option_4[]")
            correct_option = request.POST.getlist("correct_option[]")


            # ✅ Create new questions
            for i in range(len(questions)):

                if questions[i].strip():   # skip empty

                    Questions.objects.create(
                        quiz=quiz,
                        question=questions[i],
                        option_1=option_1[i],
                        option_2=option_2[i],
                        option_3=option_3[i],
                        option_4=option_4[i],
                        correct_option=int(correct_option[i])
                    )


            messages.success(request, "Quiz updated successfully")

            return redirect("adminQuizzes")

        except Exception as e:
            print(e)
            messages.error(request, "Update failed")
            return redirect("adminQuizzes")



class QuizTranslationsView(View):
    """Picker page: one row per active Language, showing how many of this
    quiz's questions (plus the title itself) already have a translation, and
    a link into EditTranslationView for that language. No translator name is
    ever recorded or shown anywhere in this flow (by design -- see
    EditTranslationView)."""

    def get(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        quiz = get_object_or_404(Quizzes, id=id)
        question_count = quiz.questions.count()

        translated_counts = dict(
            QuestionTranslation.objects.filter(question__quiz=quiz)
            .exclude(question_text="")
            .values_list("language_id")
            .annotate(c=Count("id"))
        )
        titled_langs = set(
            QuizTranslation.objects.filter(quiz=quiz)
            .exclude(title="")
            .values_list("language_id", flat=True)
        )

        languages = list(Language.objects.filter(is_active=True))
        for lang in languages:
            lang.translated_count = translated_counts.get(lang.code, 0)
            lang.has_title = lang.code in titled_langs
            lang.is_done = question_count > 0 and lang.translated_count == question_count and lang.has_title

        return render(request, "custom_admin/quizzes/quiz_translations.html", {
            "quiz": quiz,
            "languages": languages,
            "question_count": question_count,
        })


class EditTranslationView(View):
    """Add/edit the translation of one quiz (title/description + every
    question's text/options/explanation) into one language. English itself
    is never edited here -- it's shown read-only alongside each field purely
    as a reference for whoever is translating, and is stored as the base
    Quizzes/Questions row, not a translation row. Leaving every field for a
    question blank removes any existing translation for it instead of
    saving an empty row, so a half-started translation never masquerades as
    a finished one in QuizTranslationsView's progress count."""

    def get(self, request, id, lang):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        quiz = get_object_or_404(Quizzes, id=id)
        language = get_object_or_404(Language, code=lang, is_active=True)
        quiz_translation = QuizTranslation.objects.filter(quiz=quiz, language=language).first()

        existing = {
            t.question_id: t
            for t in QuestionTranslation.objects.filter(question__quiz=quiz, language=language)
        }
        rows = [(q, existing.get(q.id)) for q in quiz.questions.all().order_by("id")]

        return render(request, "custom_admin/quizzes/edit_translation.html", {
            "quiz": quiz,
            "language": language,
            "quiz_translation": quiz_translation,
            "rows": rows,
        })

    def post(self, request, id, lang):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        quiz = get_object_or_404(Quizzes, id=id)
        language = get_object_or_404(Language, code=lang, is_active=True)

        try:
            with transaction.atomic():
                title = (request.POST.get("title") or "").strip()
                description = (request.POST.get("description") or "").strip()
                if title or description:
                    QuizTranslation.objects.update_or_create(
                        quiz=quiz, language=language,
                        defaults={"title": title, "description": description},
                    )
                else:
                    QuizTranslation.objects.filter(quiz=quiz, language=language).delete()

                for q in quiz.questions.all():
                    prefix = f"q_{q.id}_"
                    question_text = (request.POST.get(prefix + "question") or "").strip()
                    option_1 = (request.POST.get(prefix + "option_1") or "").strip()
                    option_2 = (request.POST.get(prefix + "option_2") or "").strip()
                    option_3 = (request.POST.get(prefix + "option_3") or "").strip()
                    option_4 = (request.POST.get(prefix + "option_4") or "").strip()
                    explanation = (request.POST.get(prefix + "explanation") or "").strip()

                    if any([question_text, option_1, option_2, option_3, option_4, explanation]):
                        QuestionTranslation.objects.update_or_create(
                            question=q, language=language,
                            defaults={
                                "question_text": question_text,
                                "option_1": option_1,
                                "option_2": option_2,
                                "option_3": option_3,
                                "option_4": option_4,
                                "explanation": explanation,
                            },
                        )
                    else:
                        QuestionTranslation.objects.filter(question=q, language=language).delete()

            messages.success(request, f"{language.name} translation saved.")
        except Exception as e:
            print("Translation Save Error:", e)
            messages.error(request, "Something went wrong while saving the translation.")

        return redirect("adminQuizTranslations", id=quiz.id)


def deleteQuiz(request):
    if request.user.is_authenticated:
        try:
            id = request.POST.get("id")
            quiz = Quizzes.objects.get(id=id)
            quiz.delete()
            messages.success(request, "Quiz deleted successfully.")
        except Quizzes.DoesNotExist:
            messages.error(request, "Quiz not found.")
        return redirect("adminQuizzes")
    else:
        messages.error(request, "You have to login first.")
        return redirect("adminLogin")


# ======================================================================
# AI QUESTION GENERATION
# ======================================================================

def _ai_draft_session_key(quiz_id):
    return f"ai_draft_questions_{quiz_id}"


class GenerateQuestionsView(View):
    """Admin-only: give a topic, get an AI-drafted question batch. Never
    writes to Questions directly -- the draft is stashed in the session
    and handed to ReviewGeneratedQuestionsView, where the admin edits/
    excludes rows before anything is saved. Same manual auth pattern as
    ImportQuestionsView (this is the admin panel's own login, not the
    participant-facing @login_required one)."""

    def get(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")
        quiz = get_object_or_404(Quizzes, id=id)
        return render(request, "custom_admin/quizzes/generate-questions.html", {
            "quiz": quiz,
            "max_questions": MAX_QUESTIONS_PER_BATCH,
        })

    def post(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        quiz = get_object_or_404(Quizzes, id=id)
        topic = request.POST.get("topic", "").strip()
        count_raw = request.POST.get("count", "10").strip()
        count = int(count_raw) if count_raw.isdigit() else 10

        try:
            draft_rows = generate_questions(topic, count)
        except AIGenerationError as e:
            return render(request, "custom_admin/quizzes/generate-questions.html", {
                "quiz": quiz,
                "max_questions": MAX_QUESTIONS_PER_BATCH,
                "error": str(e),
                "topic": topic,
                "count": count,
            })

        request.session[_ai_draft_session_key(quiz.id)] = draft_rows
        return redirect("adminReviewGeneratedQuestions", id=quiz.id)


class ReviewGeneratedQuestionsView(View):
    """Editable review screen for an AI-drafted batch sitting in the
    session. Each row is independently included/excluded and fully
    editable before Save -- Save only bulk_creates the rows the admin
    left checked, and never touches existing questions in the bank
    (unlike EditQuizView.post's delete-and-replace-everything model,
    which would be the wrong behaviour here: this is meant to ADD to the
    bank, same as ImportQuestionsView)."""

    def get(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")
        quiz = get_object_or_404(Quizzes, id=id)
        draft_rows = request.session.get(_ai_draft_session_key(quiz.id))
        if not draft_rows:
            messages.error(request, "No AI-generated draft found -- generate questions first.")
            return redirect("adminGenerateQuestions", id=quiz.id)
        return render(request, "custom_admin/quizzes/review-generated-questions.html", {
            "quiz": quiz,
            "draft_rows": draft_rows,
        })

    def post(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        quiz = get_object_or_404(Quizzes, id=id)
        action = request.POST.get("action")

        if action == "regenerate":
            request.session.pop(_ai_draft_session_key(quiz.id), None)
            return redirect("adminGenerateQuestions", id=quiz.id)

        questions = request.POST.getlist("question[]")
        option_1 = request.POST.getlist("option_1[]")
        option_2 = request.POST.getlist("option_2[]")
        option_3 = request.POST.getlist("option_3[]")
        option_4 = request.POST.getlist("option_4[]")
        correct_option = request.POST.getlist("correct_option[]")
        explanation = request.POST.getlist("explanation[]")
        included = {int(i) for i in request.POST.getlist("include[]") if i.isdigit()}

        existing_titles_lower = {
            t.strip().lower() for t in quiz.questions.values_list("question", flat=True)
        }

        clean_rows = []
        skipped = 0
        for i in range(len(questions)):
            if i not in included:
                continue
            q_text = questions[i].strip()
            opts = [option_1[i].strip(), option_2[i].strip(), option_3[i].strip(), option_4[i].strip()]
            correct_int = normalize_correct_option(correct_option[i]) if i < len(correct_option) else None
            if not q_text or any(not o for o in opts) or correct_int is None:
                skipped += 1
                continue
            if q_text.lower() in existing_titles_lower:
                skipped += 1
                continue
            clean_rows.append(Questions(
                quiz=quiz,
                question=q_text,
                option_1=opts[0], option_2=opts[1], option_3=opts[2], option_4=opts[3],
                correct_option=correct_int,
                explanation=explanation[i].strip() if i < len(explanation) else "",
            ))

        if not clean_rows:
            messages.error(request, "No question was fit to save (either all were unchecked or duplicates).")
            return redirect("adminReviewGeneratedQuestions", id=quiz.id)

        with transaction.atomic():
            Questions.objects.bulk_create(clean_rows)

        request.session.pop(_ai_draft_session_key(quiz.id), None)
        messages.success(request, f"{len(clean_rows)} AI-generated questions added.")
        if skipped:
            messages.warning(request, f"{skipped} question(s) were skipped (empty/duplicate/unchecked).")
        return redirect("adminEditQuiz", id=quiz.id)


# ======================================================================
# BULK QUESTION IMPORT (Part G)
# ======================================================================

class ImportQuestionsView(View):
    """Admin-only bulk question upload for one quiz. Uses the same manual
    is_authenticated + redirect('adminLogin') pattern as QuizView/
    EditQuizView above -- NOT @login_required, because that decorator
    redirects to settings.LOGIN_URL (/accounts/login/), which is the
    PARTICIPANT login page, not this admin panel's own login."""

    def get(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")
        quiz = get_object_or_404(Quizzes, id=id)
        return render(request, "custom_admin/quizzes/import-questions.html", {"quiz": quiz})

    def post(self, request, id):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect("adminLogin")

        quiz = get_object_or_404(Quizzes, id=id)
        uploaded = request.FILES.get("file")

        if not uploaded:
            messages.error(request, "No file selected.")
            return redirect("adminImportQuestions", id=quiz.id)

        try:
            raw_rows = parse_upload(uploaded)
        except Exception as e:
            messages.error(request, f"Could not parse the file: {e}")
            return redirect("adminImportQuestions", id=quiz.id)

        existing_titles_lower = {
            t.strip().lower() for t in quiz.questions.values_list("question", flat=True)
        }

        clean_rows, errors, warnings = validate_rows(raw_rows, existing_titles_lower)

        if errors:
            # Reject the whole file -- show every problem row at once so
            # the admin can fix the sheet in one pass instead of trial-and-error.
            return render(request, "custom_admin/quizzes/import-questions.html", {
                "quiz": quiz,
                "errors": errors,
                "warnings": warnings,
                "row_count": len(raw_rows),
            })

        # All rows import, or none -- bulk_create runs exactly once, after
        # the loop that built clean_rows in question_import.validate_rows,
        # same fix as QuizView.post's bulk_create bug.
        with transaction.atomic():
            Questions.objects.bulk_create([
                Questions(quiz=quiz, **row) for row in clean_rows
            ])

        messages.success(request, f"{len(clean_rows)} questions imported.")
        if warnings:
            messages.warning(request, f"{len(warnings)} duplicate warning(s) (imported anyway).")
        return redirect("adminEditQuiz", id=quiz.id)


def download_question_template(request):
    if not request.user.is_authenticated:
        messages.error(request, "You have to login first.")
        return redirect("adminLogin")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="question_import_template.csv"'
    writer = csv.writer(response)
    for row in SAMPLE_ROWS:
        writer.writerow(row)
    return response


# ======================================================================
# PARTICIPANT QUIZ FLOW
# ======================================================================

ALLOWED_SOURCES = {"whatsapp", "sms", "facebook", "email", "qr", "direct"}


def clean_source(raw):
    """Whitelist ?src= against ALLOWED_SOURCES -- never store raw user
    input here. This value gets rendered back in the admin analytics
    dashboard's source breakdown, so an unvalidated value is an XSS vector,
    and would otherwise pollute the analytics with arbitrary junk."""
    return raw if raw in ALLOWED_SOURCES else "direct"


def _source_session_key(quiz_id):
    return f"quiz_{quiz_id}_src"


def clean_language(raw):
    """Whitelist ?lang= against active Language rows, same reasoning as
    clean_source above -- 'en' is always valid without a DB row (it's the
    base/fallback text on Quizzes/Questions themselves, not a translation),
    anything else must be an active Language.code."""
    if not raw or raw == "en":
        return "en"
    if Language.objects.filter(code=raw, is_active=True).exists():
        return raw
    return "en"


# Hand-authored line-icons (24x24, stroke=currentColor) instead of emoji --
# emoji render inconsistently across OS/browsers (different art style per
# platform, some literally missing), so this keeps every card's icon
# looking identical everywhere and matching the site's premium
# gold/dark-green theme instead of whatever emoji set the visitor's
# device ships.
QUIZ_ICON_SVGS = {
    "rocket": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 2c2.5 2 4 5.5 4 9 0 2-.5 4-1.5 6l-2.5 3-2.5-3C8.5 15 8 13 8 11c0-3.5 1.5-7 4-9z"/>'
        '<circle cx="12" cy="10" r="1.6"/>'
        '<path d="M8.5 15c-2 .5-3 2-3.5 4.5 2.5-.5 4-1.5 4.5-3.5"/>'
        '<path d="M15.5 15c2 .5 3 2 3.5 4.5-2.5-.5-4-1.5-4.5-3.5"/>'
        '</svg>'
    ),
    "users": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="9" cy="8" r="3"/>'
        '<path d="M3.5 19c0-3 2.5-5.5 5.5-5.5s5.5 2.5 5.5 5.5"/>'
        '<circle cx="17" cy="8.5" r="2.3"/>'
        '<path d="M15 13.8c2.5.2 4.5 2.3 5.5 5"/>'
        '</svg>'
    ),
    "shield": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 3l7 3v5.5c0 4.5-3 8-7 9.5-4-1.5-7-5-7-9.5V6l7-3z"/>'
        '<path d="M9 12l2 2 4-4.5"/>'
        '</svg>'
    ),
    "landmark": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M2.5 10.5L12 4l9.5 6.5z"/>'
        '<path d="M4.5 21V10.5M9 21V10.5M15 21V10.5M19.5 21V10.5"/>'
        '<path d="M3 21h18"/>'
        '</svg>'
    ),
    "book": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M6 3.5C4.9 3.5 4 4.4 4 5.5v14c0 1.1.9 2 2 2h11.5V5.5c0-1.1-.9-2-2-2H6z"/>'
        '<path d="M8 8h6M8 11.5h6"/>'
        '</svg>'
    ),
    "megaphone": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 11v2a2 2 0 0 0 2 2h1l4 4V5L6 9H5a2 2 0 0 0-2 2z"/>'
        '<path d="M15 8a3 3 0 0 1 0 8"/>'
        '<path d="M18 5a7 7 0 0 1 0 14"/>'
        '</svg>'
    ),
    "tag": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20.6 13.4 11 3.8A2 2 0 0 0 9.6 3H4.5A1.5 1.5 0 0 0 3 4.5v5.1a2 2 0 0 0 .6 1.4l9.6 9.6a2 2 0 0 0 2.8 0l4.6-4.6a2 2 0 0 0 0-2.6z"/>'
        '<circle cx="7.5" cy="7.5" r="1.3"/>'
        '</svg>'
    ),
}

QUIZ_LIST_CARD_META = {
    # No "subtitle" here -- quiz.title is already descriptive enough on its
    # own, so appending a second subtitle line just duplicated the same text.
    "government-welfare-schemes": {"icon": "landmark", "tag": "Yojana", "accent": "#35d67f"},
    "shg-training-quiz": {"icon": "users", "tag": "SHG", "accent": "#ffd75e"},
    "cyber-security": {"icon": "shield", "tag": "Cyber", "accent": "#5eb8ff"},
    "yuvakendra-need-assessment-planning-document-for-startup": {"icon": "rocket", "tag": "Startup", "accent": "#ff9d6e"},
    "branding-and-marketing": {"icon": "megaphone", "tag": "Marketing", "accent": "#a78bfa"},
    "pricing-strategies-and-standards": {"icon": "tag", "tag": "Pricing", "accent": "#f472b6"},
}
QUIZ_LIST_CARD_DEFAULT = {"icon": "book", "tag": "Quiz", "accent": "#c9a227"}


class QuizListView(View):
    """Public, no-login quiz listing -- data-driven replacement for the
    React SPA's own /quizzes card grid (which showed uploaded banner
    images, a stale '0 min' badge, and full question-bank sizes instead
    of the actual per-attempt sample size). Reuses the same
    questions_per_attempt/MARKS_PER_QUESTION logic as QuizLandingView so
    the numbers shown here always match what the landing page promises."""

    def get(self, request):
        # Logged-in participants: which of these quizzes they've already
        # completed, so the card can show "Completed" + their score instead
        # of "Start Quiz" -- QuizTakeView already redirects a one_attempt_only
        # quiz straight to the old result if they click in anyway, this just
        # makes that lock visible *before* the click instead of a surprise
        # after it. is_demo=False for the same reason as MyResultsView: a
        # stale/timed-out attempt auto-closed by _get_or_create_attempt was
        # never really "completed" by the participant.
        my_attempts_by_quiz = {}
        if request.user.is_authenticated:
            my_attempts = (
                QuizAttempt.objects.filter(user=request.user, completed_at__isnull=False, is_demo=False)
                .order_by("quiz_id", "-completed_at")
            )
            for a in my_attempts:
                my_attempts_by_quiz.setdefault(a.quiz_id, a)

        quizzes = []
        for quiz in Quizzes.objects.filter(status=True).order_by("id"):
            if not quiz.is_live:
                continue
            meta = QUIZ_LIST_CARD_META.get(quiz.slug, QUIZ_LIST_CARD_DEFAULT)
            question_count = min(quiz.questions_per_attempt, quiz.questions.count())
            # strip_tags() alone leaves entities like "&amp;" as literal
            # text, which autoescaping then re-escapes on render (visible
            # as "&amp;" on the page) -- unescape() first so what's left
            # is plain text with real "&" characters for autoescape to
            # handle correctly, exactly once.
            short_desc = html.unescape(strip_tags(quiz.description or ""))
            short_desc = Truncator(short_desc.strip()).chars(140)
            my_attempt = my_attempts_by_quiz.get(quiz.id)
            quizzes.append({
                "quiz": quiz,
                "icon_svg": QUIZ_ICON_SVGS[meta["icon"]],
                "tag": meta["tag"],
                "accent": meta["accent"],
                "question_count": question_count,
                "total_marks": question_count * MARKS_PER_QUESTION,
                "short_desc": short_desc,
                # Same PER_QUESTION_SECONDS the actual quiz-take timer uses
                # (not a separate guess), so this can never drift out of
                # sync with the real per-question countdown.
                "estimated_minutes": round(question_count * PER_QUESTION_SECONDS / 60),
                # Only actually "locked" if the quiz itself is one-attempt --
                # a repeatable quiz still shows the participant's last score
                # but Start Quiz stays live.
                "my_attempt": my_attempt,
                "locked": bool(my_attempt) and quiz.one_attempt_only,
            })
        return render(request, "custom_admin/quizzes/quiz_list.html", {
            "quizzes": quizzes,
            "is_authenticated": request.user.is_authenticated,
        })


class QuizLandingView(View):
    """Public, no login required -- this is the ONLY URL ever put into a
    WhatsApp/QR/social share. Reads ?src=, stashes it in session so
    QuizTakeView can attribute the eventual attempt, and carries Open Graph
    tags so WhatsApp's link-preview crawler (not logged in, so it can only
    ever see this page) shows a real title/image instead of a bare URL."""

    def get(self, request, slug):
        quiz = get_object_or_404(Quizzes, slug=slug, status=True)

        src = clean_source(request.GET.get("src", "direct"))
        request.session[_source_session_key(quiz.id)] = src

        share_url = request.build_absolute_uri(reverse("quiz_landing", kwargs={"slug": quiz.slug}))
        og_image = request.build_absolute_uri(quiz.image.url) if quiz.image else None
        whatsapp_text = f"Try the \"{quiz.title}\" quiz on Sahyog Setu: {share_url}?src=whatsapp"

        # How many questions THIS attempt will actually contain, not the
        # size of the full bank -- quiz.questions.count() (e.g. 100) was
        # shown here before, but QuizTakeView only ever samples
        # questions_per_attempt (e.g. 10), so the old number promised
        # far more than the quiz actually delivers.
        question_count = min(quiz.questions_per_attempt, quiz.questions.count())

        # Only offer languages that this SPECIFIC quiz actually has at least
        # one translated question in -- an active Language with zero
        # translations for this quiz would silently fall back to English
        # everywhere (see Questions.text_for), which is a confusing,
        # apparently-broken toggle to show at all. distinct() because a
        # language could have translations on multiple questions.
        translated_codes = list(
            Language.objects.filter(
                is_active=True, question_translations__question__quiz=quiz
            ).exclude(question_translations__question_text="").distinct().values_list("code", flat=True)
        )
        available_languages = [{"code": "en", "name": "English", "native_name": "English"}] + [
            {"code": l.code, "name": l.name, "native_name": l.native_name}
            for l in Language.objects.filter(code__in=translated_codes)
        ]

        lang = clean_language(request.GET.get("lang", "en"))
        if lang != "en" and lang not in translated_codes:
            lang = "en"

        # Built here (not in the template) so the ?lang= carries through to
        # Start Quiz correctly encoded even when nested inside next= for the
        # logged-out case -- letting the template hand-assemble a query
        # string inside another query string is exactly how that kind of
        # link quietly breaks.
        take_url = reverse("quiz_take", kwargs={"quiz_id": quiz.id}) + f"?lang={lang}"
        login_url = f"{reverse('login')}?next={urllib.parse.quote(take_url)}"

        return render(request, "custom_admin/quizzes/quiz_landing.html", {
            "quiz": quiz,
            "share_url": share_url,
            "whatsapp_text": whatsapp_text,
            "og_image": og_image,
            "question_count": question_count,
            "total_marks": question_count * MARKS_PER_QUESTION,
            "take_url": take_url,
            "login_url": login_url,
            "lang": lang,
            "available_languages": available_languages,
            "quiz_title": quiz.title_for(lang),
            "quiz_description": quiz.description_for(lang),
        })


@staff_member_required(login_url="adminLogin")
def quiz_qr_code(request, slug):
    """PNG QR code of the public landing page URL, tagged ?src=qr, for
    field staff to print for village meetings / SHG training sessions.
    Uses reportlab's QR encoder to build the module matrix (already a
    dependency for certificate generation), then rasterizes it with Pillow
    directly -- reportlab's own PNG renderer (renderPM) needs a rlPyCairo
    or compiled _rl_renderPM backend that isn't installed in this
    environment, and Pillow is already a hard dependency (see imaging.py),
    so this needs no new package either way."""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from PIL import Image, ImageDraw

    quiz = get_object_or_404(Quizzes, slug=slug)
    landing_path = reverse("quiz_landing", kwargs={"slug": quiz.slug})
    target_url = request.build_absolute_uri(landing_path) + "?src=qr"

    widget = QrCodeWidget(target_url)
    widget.qr.make()
    matrix = widget.qr.modules
    module_count = widget.qr.moduleCount

    scale = 10
    border = 4  # quiet zone, per QR spec minimum
    size = (module_count + border * 2) * scale
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)
    for row in range(module_count):
        for col in range(module_count):
            if matrix[row][col]:
                x0, y0 = (col + border) * scale, (row + border) * scale
                draw.rectangle([x0, y0, x0 + scale - 1, y0 + scale - 1], fill="black")

    buf = BytesIO()
    img.save(buf, format="PNG")
    response = HttpResponse(buf.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="quiz-{quiz.slug}-qr.png"'
    return response


@method_decorator(login_required, name='dispatch')
class QuizTakeView(View):

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quizzes, id=quiz_id, status=True)

        if not quiz.is_live:
            messages.error(request, "This quiz is not available right now.")
            return redirect("/")

        # is_demo=False here too -- a seeded demo row must never count toward
        # a real participant's one-attempt limit or their displayed average.
        completed_attempts = QuizAttempt.objects.filter(quiz=quiz, completed_at__isnull=False, is_demo=False)

        if quiz.one_attempt_only:
            existing = completed_attempts.filter(user=request.user).order_by('-completed_at').first()
            if existing:
                return redirect("quiz_result", pk=existing.id)

        lang = clean_language(request.GET.get("lang", "en"))
        attempt = self._get_or_create_attempt(request, quiz, lang)

        # Resolve against attempt.question_ids -- NEVER request.session.
        # gunicorn restarts, session expiry, and a second browser tab all
        # destroy session state mid-quiz; this row survives all three.
        # IDs that no longer resolve (admin deleted the question mid-attempt
        # via EditQuizView) are simply skipped here -- quiz_submit excludes
        # them from total_questions too, never counts them wrong.
        questions_by_id = Questions.objects.in_bulk(attempt.question_ids)
        questions = [questions_by_id[qid] for qid in attempt.question_ids if qid in questions_by_id]

        # Already-saved answers, so a resumed attempt (crash/reload/new tab)
        # shows correct palette state on first paint, not just after JS runs.
        existing_answers = dict(
            attempt.responses.exclude(question_id__isnull=True).values_list("question_id", "selected_option")
        )

        # Server is the only clock. remaining_seconds here is the whole-
        # attempt safety budget backing quiz_answer's server-side rejection
        # below, NOT what drives the client's visible countdown any more --
        # the client now runs its own fixed 30s-per-question timer (see
        # quiz_take.html), reset locally on every question change.
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        remaining_seconds = max(0, len(questions) * PER_QUESTION_SERVER_BUDGET - int(elapsed))

        avg_percentage = completed_attempts.aggregate(avg=Avg('percentage'))['avg'] or 0

        # Forward-only + one-shot answers (see quiz_answer) mean an already-
        # answered question is never shown again -- resume at the first
        # question that has no saved response yet, not always index 0,
        # otherwise reloading mid-quiz would strand the participant back on
        # a locked, already-answered Q1.
        resume_index = next(
            (i for i, q in enumerate(questions) if q.id not in existing_answers),
            len(questions),
        )

        # Question text/options travel to the client (needed to render the
        # gamified single-card UI without a full-page reload per question),
        # but correct_option/explanation never do -- those only ever come
        # back from quiz_answer(), after an answer for that specific
        # question is already locked in, same secure boundary as before.
        quiz_data = {
            "attemptId": attempt.id,
            "answerUrl": reverse("quiz_answer", kwargs={"quiz_id": quiz.id}),
            "perQuestionSeconds": PER_QUESTION_SECONDS,
            "resumeIndex": resume_index,
            "questions": [
                {
                    "id": q.id,
                    "text": q.text_for(attempt.language),
                    "options": [text for _, text in q.options_for(attempt.language)],
                }
                for q in questions
            ],
        }

        return render(request, "custom_admin/quizzes/quiz_take.html", {
            "quiz": quiz,
            "attempt": attempt,
            "questions": questions,
            "existing_answers": existing_answers,
            "total_questions": len(questions),
            "remaining_seconds": remaining_seconds,
            "completed_count": completed_attempts.count(),
            "avg_percentage": round(avg_percentage, 1),
            "quiz_data": quiz_data,
            "lang": attempt.language,
        })

    def _get_or_create_attempt(self, request, quiz, lang="en"):
        # Reusing an in-progress attempt (rather than always creating a new
        # one) is what makes the timer un-resettable by just reloading the
        # page, AND is what makes a resubmit idempotent later in
        # quiz_submit -- there's only ever one live row per (user, quiz).
        #
        # That guarantee is enforced by QuizAttempt.live_lock's real unique
        # constraint (see the field's docstring for why it's this and not a
        # Meta.UniqueConstraint(condition=...) -- MySQL doesn't support
        # conditional unique constraints, so that declaration would silently
        # create nothing). The .filter().first() below is just a fast-path
        # read for the common case; live_lock's uniqueness is what actually
        # stops two simultaneous taps on "Start Quiz" from both
        # succeeding.
        attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz, completed_at__isnull=True).first()

        # An incomplete attempt whose own time budget has already run out
        # (abandoned tab, browser crash, or the participant simply never
        # came back) was being resumed here unconditionally -- reloading
        # attempt.started_at from hours/days ago, so elapsed already exceeds
        # the budget and quiz_answer rejects the very first answer as
        # time_up (403). The client correctly treats time_up as terminal
        # and finishes immediately, which reads as the whole quiz being
        # broken: every attempt instantly fails on question one. Close the
        # stale row out here (is_demo=True so it never counts against
        # one_attempt_only, certificates, or the average-score stat -- same
        # exclusion seeded/demo rows already get) to free live_lock, then
        # fall through and create a genuinely fresh attempt below.
        if attempt:
            stale_budget = (len(attempt.question_ids) or 1) * PER_QUESTION_SERVER_BUDGET
            if (timezone.now() - attempt.started_at).total_seconds() > stale_budget:
                attempt.completed_at = timezone.now()
                attempt.is_demo = True
                # Same release quiz_submit does on a normal finish (see
                # below) -- live_lock is a real unique column that isn't
                # freed just by setting completed_at, so skipping this
                # would leave the stale row still holding "{user}_{quiz}"
                # and the create() below would IntegrityError right away.
                attempt.live_lock = None
                attempt.save(update_fields=["completed_at", "is_demo", "live_lock"])
                attempt = None

        # A resumed attempt kept its ORIGINAL locked language regardless of
        # what the landing page's dropdown was just showing/set to, which
        # reads as "language selector doesn't do anything" -- reload the
        # landing page after starting a Hindi attempt, it still defaults to
        # showing English, but clicking Start/Continue silently dropped you
        # right back into Hindi. take_url always threads the landing page's
        # current lang through as ?lang=... (see QuizLandingView.get), so
        # arriving here with a different lang than the attempt's is always
        # a genuine, explicit choice, not incidental -- safe to honor it:
        # remaining unanswered questions render fresh via text_for(attempt.
        # language) every time anyway, nothing about already-answered ones
        # (frozen in their QuestionResponse snapshots) changes retroactively.
        if attempt and attempt.language != lang:
            attempt.language = lang
            attempt.save(update_fields=["language"])

        created = False

        if not attempt:
            try:
                with transaction.atomic():
                    attempt = QuizAttempt.objects.create(
                        user=request.user, quiz=quiz,
                        live_lock=f"{request.user.id}_{quiz.id}",
                        source=clean_source(request.session.get(_source_session_key(quiz.id), "direct")),
                        language=lang,
                    )
                    created = True
            except IntegrityError:
                # Someone else's concurrent request won the race and holds
                # live_lock for this (user, quiz) pair right now -- re-fetch
                # their row instead of erroring out.
                attempt = QuizAttempt.objects.get(user=request.user, quiz=quiz, completed_at__isnull=True)

        if created or not attempt.question_ids:
            bank_ids = list(quiz.questions.values_list("id", flat=True))
            sample_size = min(quiz.questions_per_attempt, len(bank_ids))
            attempt.question_ids = random.sample(bank_ids, sample_size) if bank_ids else []
            attempt.save(update_fields=["question_ids"])

        return attempt


@login_required
def quiz_answer(request, quiz_id):
    """Per-question answer, called via fetch() the instant the participant
    picks an option (or a question times out/is skipped) -- NOT at final
    submit (quiz_submit reads no client answers at all; everything
    scoreable is already here). Also the ONLY place correct_option/
    explanation are ever revealed to the client, and only for the one
    question just answered -- the gamified UI shows an immediate right/
    wrong reveal, so this response carries isCorrect/correctOption/
    explanation back down.

    One-shot, not update_or_create: the new UI locks a question's options
    the instant it's answered (no "change your mind" affordance left on
    the client), so the server enforces the same rule -- otherwise, since
    this endpoint now echoes back whether an answer was correct, a client
    that ignored its own UI lock could brute-force every question by
    POSTing each option in turn and reading isCorrect. First answer for a
    question is final; a repeat POST just replays the original result
    instead of erroring, so a network retry after a dropped response is
    harmless."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "post_required"}, status=405)

    quiz = get_object_or_404(Quizzes, id=quiz_id, status=True)
    attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz, completed_at__isnull=True).first()
    if not attempt:
        return JsonResponse({"ok": False, "error": "no_active_attempt"}, status=409)

    # Server is the only clock -- reject anything POSTed after time's up.
    # Budget is per-attempt question count * PER_QUESTION_SERVER_BUDGET,
    # matching the client's fixed 30s-per-question pacing (not quiz.quiz_time,
    # which no longer drives timing -- see PER_QUESTION_SECONDS above).
    # (quiz_submit re-derives elapsed time independently too; this is just
    # the earliest point an over-time answer can be caught.)
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    if elapsed > len(attempt.question_ids) * PER_QUESTION_SERVER_BUDGET:
        return JsonResponse({"ok": False, "error": "time_up"}, status=403)

    try:
        question_id = int(request.POST.get("question_id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "bad_question_id"}, status=400)

    # Must be a question actually sampled for THIS attempt -- closes off
    # answering something that was never assigned to this participant.
    if question_id not in attempt.question_ids:
        return JsonResponse({"ok": False, "error": "not_in_attempt"}, status=400)

    question = Questions.objects.filter(id=question_id, quiz=quiz).first()
    if not question:
        # Deleted mid-attempt by EditQuizView -- nothing to score against.
        # Told to the client so it can grey that palette slot instead of
        # silently failing or retrying forever.
        return JsonResponse({"ok": False, "error": "question_deleted"}, status=410)

    existing = QuestionResponse.objects.filter(attempt=attempt, question=question).first()
    if existing:
        return JsonResponse({
            "ok": True,
            "isCorrect": existing.is_correct,
            "correctOption": int(existing.correct_option),
            "explanation": existing.explanation_snapshot,
        })

    # selected_option is "" for a skip/timeout -- never equals correct_option
    # ("1".."4"), so it scores as wrong exactly like any other wrong answer.
    selected_option = request.POST.get("selected_option", "")
    correct_option = str(question.correct_option)
    is_correct = selected_option == correct_option

    try:
        response = QuestionResponse.objects.create(
            attempt=attempt, question=question,
            question_text_snapshot=question.text_for(attempt.language),
            selected_option=selected_option,
            correct_option=correct_option,
            is_correct=is_correct,
            explanation_snapshot=question.explanation_for(attempt.language),
        )
    except IntegrityError:
        # Two near-simultaneous POSTs for the same question (e.g. a
        # double-tap before the client-side lock kicks in) -- the
        # UniqueConstraint on (attempt, question) means only one could have
        # won the create(); hand back that winner's real result instead of
        # 500ing on the loser.
        response = QuestionResponse.objects.get(attempt=attempt, question=question)

    return JsonResponse({
        "ok": True,
        "isCorrect": response.is_correct,
        "correctOption": int(response.correct_option),
        "explanation": response.explanation_snapshot,
    })


@login_required
def quiz_submit(request, pk):
    """Idempotent finalize. The client sends NO answers and NO score --
    everything is already in QuestionResponse, saved incrementally by
    quiz_answer() as the participant went. A question with no response row
    is unanswered = wrong. select_for_update + an already-completed
    short-circuit closes the same double-scoring hole /api/quiz/certificate
    had: a double-tap, a network retry, or a queued offline POST replaying
    after the attempt already finished all just redirect to the existing
    result instead of re-scoring."""
    if request.method != "POST":
        attempt = get_object_or_404(QuizAttempt, pk=pk, user=request.user)
        return redirect("quiz_take", quiz_id=attempt.quiz_id)

    with transaction.atomic():
        attempt = get_object_or_404(
            QuizAttempt.objects.select_for_update(), pk=pk, user=request.user
        )

        if attempt.completed_at:
            return redirect("quiz_result", pk=attempt.pk)

        quiz = attempt.quiz

        # Recompute elapsed from started_at server-side -- never trust
        # anything the client sends about timing.
        elapsed_seconds = (timezone.now() - attempt.started_at).total_seconds()

        # Resolve against question_ids fixed at attempt creation. Any ID
        # that no longer exists (admin deleted the question mid-attempt) is
        # excluded from total_questions entirely, never counted wrong --
        # the user is never punished for an admin's edit.
        live_question_ids = set(
            Questions.objects.filter(id__in=attempt.question_ids).values_list("id", flat=True)
        )
        total_questions = len(live_question_ids)

        responses_by_qid = dict(
            attempt.responses.filter(question_id__in=live_question_ids)
            .values_list("question_id", "is_correct")
        )
        # A live question with no saved response = never answered = wrong.
        score = sum(1 for qid in live_question_ids if responses_by_qid.get(qid))

        percentage = (score / total_questions * 100) if total_questions else 0
        passed = percentage >= quiz.pass_threshold

        attempt.score = score
        attempt.total_questions = total_questions
        attempt.percentage = percentage
        attempt.passed = passed
        attempt.time_taken_seconds = int(elapsed_seconds)
        attempt.completed_at = timezone.now()
        # Release live_lock -- this is what lets the same user start a NEW
        # live attempt later (repeat attempts, if one_attempt_only=False)
        # without live_lock's unique constraint blocking them.
        attempt.live_lock = None
        attempt.save()

    return redirect("quiz_result", pk=attempt.pk)


@method_decorator(login_required, name='dispatch')
class QuizResultView(View):

    def get(self, request, pk):
        attempt = get_object_or_404(QuizAttempt, pk=pk, user=request.user)
        responses = attempt.responses.all()
        correct = responses.filter(is_correct=True).count()
        # "Wrong" (picked an option, got it wrong) vs "missed" (skipped, or
        # timed out with no answer -- quiz_answer records those with
        # selected_option="") are shown as separate states in the gamified
        # navigator grid/report, matching the taking flow's own reveal.
        # missed is total-minus-the-rest rather than its own filter so a
        # question with NO response row at all (the network gave up after
        # retries in quiz_take.html, see submitAnswer there) still counts
        # toward it -- correct+wrong+missed always equals total_questions
        # even in that edge case, even though that particular question has
        # no snapshot to show in the review list below.
        wrong = responses.filter(is_correct=False).exclude(selected_option="").count()
        missed = attempt.total_questions - correct - wrong
        incorrect = attempt.total_questions - correct

        marks = attempt.score * MARKS_PER_QUESTION
        total_marks = attempt.total_questions * MARKS_PER_QUESTION

        # Share the QUIZ landing page, never this result page -- /quiz/result/<id>/
        # is private and guessable by id; sharing it would leak this user's
        # score to whoever clicks the link.
        share_url = request.build_absolute_uri(reverse("quiz_landing", kwargs={"slug": attempt.quiz.slug}))
        whatsapp_text = (
            f"I completed the \"{attempt.quiz.title}\" quiz on Sahyog Setu "
            f"with {round(attempt.percentage)}% 🎓\n"
            f"You try it too: {share_url}?src=whatsapp"
        )

        return render(request, "custom_admin/quizzes/quiz_result.html", {
            "attempt": attempt,
            "responses": responses,
            "correct": correct,
            "wrong": wrong,
            "missed": missed,
            "incorrect": incorrect,
            "marks": marks,
            "total_marks": total_marks,
            "percentage": attempt.percentage,
            "pass_threshold": attempt.quiz.pass_threshold,
            "certificate_min_percentage": CERTIFICATE_MIN_PERCENTAGE,
            "share_url": share_url,
            "whatsapp_text": whatsapp_text,
        })


@method_decorator(login_required, name='dispatch')
class QuizLeaderboardView(View):

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quizzes, id=quiz_id)
        is_staff = request.user.is_authenticated and request.user.is_staff

        if not is_staff and not quiz.leaderboard_public:
            messages.error(request, "This leaderboard is not public.")
            return redirect("quiz_take", quiz_id=quiz.id)

        attempts = QuizAttempt.objects.filter(
            quiz=quiz, completed_at__isnull=False
        ).select_related("user").annotate(
            marks=F("score") * MARKS_PER_QUESTION,
            total_marks=F("total_questions") * MARKS_PER_QUESTION,
        ).order_by("-score", "time_taken_seconds")[:100]

        return render(request, "custom_admin/quizzes/quiz_leaderboard.html", {
            "quiz": quiz,
            "attempts": attempts,
        })


# ======================================================================
# CERTIFICATE (Part I) -- HTML + browser print-to-PDF, no WeasyPrint/
# wkhtmltopdf, so no new system deps on the VPS.
# ======================================================================

# Hard floor, independent of quiz.pass_threshold -- pass_threshold is
# admin-configurable per quiz (e.g. for leaderboard/analytics "did they
# pass" purposes) and could be set below 60 for some future quiz. A
# certificate must never go out under 60% regardless of that setting.
CERTIFICATE_MIN_PERCENTAGE = 60


@method_decorator(login_required, name='dispatch')
class CertificateView(View):

    def get(self, request, pk):
        # passed=True in the lookup itself -- a failed attempt 404s here
        # rather than needing a separate "sorry, you didn't pass" branch.
        # is_demo=False -- a demo/seed row can never issue a real certificate.
        # percentage__gte -- see CERTIFICATE_MIN_PERCENTAGE above.
        attempt = get_object_or_404(
            QuizAttempt, pk=pk, user=request.user, passed=True, is_demo=False,
            percentage__gte=CERTIFICATE_MIN_PERCENTAGE,
        )

        if not attempt.quiz.certificate_enabled:
            messages.error(request, "Certificate is not available for this quiz.")
            return redirect("quiz_result", pk=attempt.id)

        # Some users registered with mobile only and have a blank first_name
        # -- get_full_name() then returns ''. username is required NOT NULL
        # for auth so this should be unreachable in practice, but a blank
        # name signed onto a certificate is bad enough to guard explicitly
        # rather than trust that invariant silently.
        display_name = (attempt.user.get_full_name() or attempt.user.username or "").strip()
        if not display_name:
            messages.error(request, "Your profile has no name on file — a certificate cannot be issued. Please contact support.")
            return redirect("quiz_result", pk=attempt.id)

        if not attempt.certificate_id:
            attempt.certificate_id = generate_certificate_id(QuizAttempt)
            attempt.certificate_issued_at = timezone.now()
            attempt.save(update_fields=["certificate_id", "certificate_issued_at"])

        # Share URL is ALWAYS the public quiz landing page, never this
        # certificate page -- the certificate URL is private and user-scoped
        # by id; sharing it would leak this attempt to whoever clicks the link.
        landing_path = reverse("quiz_landing", kwargs={"slug": attempt.quiz.slug})
        share_url = request.build_absolute_uri(landing_path)
        share_text = (
            f"I completed the \"{attempt.quiz.title}\" quiz on Sahyog Setu "
            f"with {round(attempt.percentage)}% 🎓\n"
            f"You try it too: {share_url}?src=whatsapp"
        )

        return render(request, "custom_admin/quizzes/certificate.html", {
            "attempt": attempt,
            "quiz": attempt.quiz,
            "display_name": display_name,
            "share_url": share_url,
            "share_text": share_text,
        })


@method_decorator(login_required, name='dispatch')
class CertificateImageDownloadView(View):
    """PNG download (Part K) -- same eligibility checks as CertificateView
    (own attempt, passed, not demo) since this bypasses the certificate
    page entirely; without them a logged-in user could download any
    attempt's certificate by guessing a pk."""

    def get(self, request, pk):
        attempt = get_object_or_404(
            QuizAttempt, pk=pk, user=request.user, passed=True, is_demo=False,
            percentage__gte=CERTIFICATE_MIN_PERCENTAGE,
        )
        if not attempt.certificate_id:
            messages.error(request, "Certificate has not been issued yet.")
            return redirect("quiz_result", pk=attempt.id)

        image_bytes = render_certificate_image(attempt)
        response = HttpResponse(image_bytes, content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="certificate_{attempt.certificate_id}.png"'
        return response


def verify_certificate(request, cert_id):
    # Public, no login -- deliberately does not select_related("user") into
    # the template with mobile/email fields; the template only ever
    # receives get_full_name(), never the User object itself, so there's
    # no field to accidentally leak later.
    attempt = QuizAttempt.objects.filter(certificate_id=cert_id).select_related("quiz", "user").first()

    context = {"cert_id": cert_id, "attempt": None}
    if attempt:
        context["attempt"] = {
            "name": attempt.user.get_full_name().strip() or "Participant",
            "quiz_title": attempt.quiz.title,
            "percentage": attempt.percentage,
            "issued_at": attempt.certificate_issued_at,
        }

    return render(request, "custom_admin/quizzes/verify_certificate.html", context)


# ======================================================================
# ANALYTICS -- staff-only, read-only. login_url points at THIS app's own
# admin login (adminLogin), not settings.LOGIN_URL -- that's the
# participant login page (/accounts/login/), same mismatch already
# avoided everywhere else in this file (see the ImportQuestionsView note
# above). is_staff is already the established "staff" marker in this app
# (QuizLeaderboardView checks it too).
# ======================================================================

ALLOWED_ANALYTICS_DAYS = {7, 30, 90}


def _analytics_base_qs(include_demo):
    qs = QuizAttempt.objects.filter(completed_at__isnull=False)
    if not include_demo:
        qs = qs.filter(is_demo=False)
    return qs


@method_decorator(staff_member_required(login_url="adminLogin"), name="dispatch")
class QuizAnalyticsView(View):

    def get(self, request):
        include_demo = request.GET.get("demo") == "1"

        try:
            days = int(request.GET.get("days", 30))
        except ValueError:
            days = 30
        if days not in ALLOWED_ANALYTICS_DAYS:
            days = 30

        base = _analytics_base_qs(include_demo)

        # KPIs -- one aggregate call.
        kpi = base.aggregate(
            total=Count("id"),
            participants=Count("user", distinct=True),
            avg_pct=Avg("percentage"),
            passed=Count("id", filter=Q(passed=True)),
        )
        total = kpi["total"] or 0
        pass_rate = round((kpi["passed"] / total * 100), 1) if total else 0

        # Score distribution -- one aggregate.
        distribution = base.aggregate(
            low=Count("id", filter=Q(percentage__lt=40)),
            mid=Count("id", filter=Q(percentage__gte=40, percentage__lt=70)),
            high=Count("id", filter=Q(percentage__gte=70)),
        )

        # Most-failed questions -- grouped by snapshot text, NOT question_id,
        # because EditQuizView deletes+recreates Questions on every edit,
        # which would null out question_id on every past response.
        response_qs = QuestionResponse.objects.filter(attempt__completed_at__isnull=False)
        if not include_demo:
            response_qs = response_qs.filter(attempt__is_demo=False)

        most_failed = list(
            response_qs.values("question_text_snapshot")
            .annotate(seen=Count("id"), wrong=Count("id", filter=Q(is_correct=False)))
            .filter(seen__gte=5)
            .annotate(pct_wrong=100.0 * F("wrong") / F("seen"))
            .order_by("-pct_wrong")[:10]
        )

        # Per-quiz breakdown -- aggregated from QuizAttempt (never chain
        # Avg()+Count() through Quizzes' reverse FKs -- that JOIN multiplies
        # rows and silently corrupts the average).
        quiz_breakdown = list(
            base.values("quiz_id", "quiz__title")
            .annotate(
                attempts=Count("id"),
                participants=Count("user", distinct=True),
                avg_pct=Avg("percentage"),
                avg_time=Avg("time_taken_seconds"),
                passed=Count("id", filter=Q(passed=True)),
            )
            .order_by("-attempts")
        )

        # Daily attempts -- fill missing days with 0 so the line doesn't
        # jump across gaps and lie about the trend.
        since = timezone.localdate() - timedelta(days=days - 1)
        daily_rows = (
            base.filter(completed_at__date__gte=since)
            .annotate(day=TruncDate("completed_at"))
            .values("day")
            .annotate(n=Count("id"))
        )
        daily_by_date = {row["day"]: row["n"] for row in daily_rows}
        daily_series = [
            {"date": (since + timedelta(days=i)).isoformat(), "count": daily_by_date.get(since + timedelta(days=i), 0)}
            for i in range(days)
        ]

        # Source breakdown -- "Traffic Sources" panel.
        source_breakdown = list(
            base.values("source").annotate(n=Count("id")).order_by("-n")
        )

        chart_data = {
            "distribution": distribution,
            "daily": daily_series,
            "quiz_breakdown": [
                {**row, "avg_pct": round(row["avg_pct"] or 0, 1)} for row in quiz_breakdown
            ],
            "source_breakdown": source_breakdown,
        }

        return render(request, "custom_admin/quizzes/quiz_analytics.html", {
            "total": total,
            "participants": kpi["participants"] or 0,
            "avg_pct": round(kpi["avg_pct"] or 0, 1),
            "pass_rate": pass_rate,
            "distribution": distribution,
            "most_failed": most_failed,
            "quiz_breakdown": chart_data["quiz_breakdown"],
            "source_breakdown": source_breakdown,
            "registered_users": User.objects.filter(user_type=2).count(),
            "include_demo": include_demo,
            "days": days,
            "chart_data": chart_data,
        })


class _Echo:
    """A file-like object that just hands back what it's given -- lets
    csv.writer stream rows through StreamingHttpResponse instead of
    building the whole CSV in memory first."""

    def write(self, value):
        return value


@staff_member_required(login_url="adminLogin")
def quiz_analytics_export(request):
    include_demo = request.GET.get("demo") == "1"
    qs = _analytics_base_qs(include_demo).select_related("user", "quiz").order_by("id").iterator()

    def rows():
        writer = csv.writer(_Echo())
        yield writer.writerow([
            "attempt_id", "username", "quiz", "score", "total_questions",
            "percentage", "passed", "started_at", "completed_at", "time_taken_seconds",
        ])
        for a in qs:
            yield writer.writerow([
                a.id, a.user.username, a.quiz.title, a.score, a.total_questions,
                round(a.percentage, 1), a.passed, a.started_at, a.completed_at, a.time_taken_seconds,
            ])

    filename = f"sahyog-quiz-attempts-{timezone.localdate().isoformat()}.csv"
    response = StreamingHttpResponse(rows(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


PARTICIPANTS_PER_PAGE = 25


@method_decorator(staff_member_required(login_url="adminLogin"), name="dispatch")
class ParticipantsListView(View):
    """Every participant who has completed at least one quiz, with
    aggregated stats. Grouped straight off QuizAttempt (its own fields
    only) -- never annotate these aggregates onto User via the reverse FK,
    that's the same join-multiplication trap noted on quiz_breakdown above,
    except worse here since it would also multiply the distinct-quiz count."""

    def get(self, request):
        q = request.GET.get("q", "").strip()

        rows = (
            QuizAttempt.objects.filter(completed_at__isnull=False, is_demo=False)
            .values("user_id", "user__name", "user__mobile", "user__email")
            .annotate(
                attempts=Count("id"),
                quizzes_taken=Count("quiz_id", distinct=True),
                avg_pct=Avg("percentage"),
                passed=Count("id", filter=Q(passed=True)),
                last_attempt=Max("completed_at"),
            )
            .order_by("-last_attempt")
        )

        if q:
            rows = rows.filter(
                Q(user__name__icontains=q) | Q(user__mobile__icontains=q) | Q(user__email__icontains=q)
            )

        rows = list(rows)
        for row in rows:
            row["avg_pct"] = round(row["avg_pct"] or 0, 1)
            row["pass_rate"] = round(row["passed"] / row["attempts"] * 100, 1) if row["attempts"] else 0

        paginator = Paginator(rows, PARTICIPANTS_PER_PAGE)
        page = paginator.get_page(request.GET.get("page"))

        return render(request, "custom_admin/quizzes/quiz_participants.html", {
            "page_obj": page,
            "q": q,
        })


@method_decorator(staff_member_required(login_url="adminLogin"), name="dispatch")
class ParticipantDetailView(View):
    """One participant's full attempt history -- every quiz they've taken,
    not just one. user_type=2 keeps this from ever resolving to an admin
    account by id guess."""

    def get(self, request, user_id):
        participant = get_object_or_404(User, pk=user_id, user_type=2)

        attempts = (
            QuizAttempt.objects.filter(user=participant, completed_at__isnull=False)
            .select_related("quiz")
            .order_by("-completed_at")
        )
        agg = attempts.aggregate(avg_pct=Avg("percentage"), passed=Count("id", filter=Q(passed=True)))
        total = len(attempts)

        return render(request, "custom_admin/quizzes/quiz_participant_detail.html", {
            "participant": participant,
            "attempts": attempts,
            "total": total,
            "avg_pct": round(agg["avg_pct"] or 0, 1),
            "passed": agg["passed"] or 0,
        })


@method_decorator(staff_member_required(login_url="adminLogin"), name="dispatch")
class AdminAttemptDetailView(View):
    """Question-by-question review of a single attempt, for any participant --
    the staff-only counterpart of QuizResultView (which is locked to
    user=request.user). No such lock here; that's the point of this view."""

    def get(self, request, pk):
        attempt = get_object_or_404(
            QuizAttempt.objects.select_related("user", "quiz"), pk=pk, completed_at__isnull=False
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
        for r in responses:
            # question is SET_NULL on delete -- if the admin has since edited
            # the quiz (EditQuizView deletes+recreates Questions), only the
            # snapshotted question TEXT survives, never the option-text
            # snapshot, so a deleted question can only be labeled by number.
            options_by_number = dict(r.question.options_list) if r.question else {}
            rows.append({
                "question_text": r.question_text_snapshot,
                "selected_label": option_label(r.selected_option, options_by_number),
                "correct_label": option_label(r.correct_option, options_by_number),
                "is_correct": r.is_correct,
                "explanation": r.explanation_snapshot,
            })

        return render(request, "custom_admin/quizzes/quiz_attempt_detail.html", {
            "attempt": attempt,
            "rows": rows,
        })


@method_decorator(login_required, name="dispatch")
class MyResultsView(View):
    """Participant's own attempt history. Only ever queries
    user=request.user -- no other participant's name, score, or rank is
    ever rendered here."""

    def get(self, request):
        attempts = (
            # is_demo=False -- excludes the auto-closed stale attempts
            # QuizTakeView._get_or_create_attempt() marks that way (see its
            # docstring): those are abandoned/timed-out rows, not a real
            # completed 0-score quiz, and would otherwise show up here as a
            # fake "Fail" entry for a quiz the participant never actually
            # got to answer a single question on.
            QuizAttempt.objects.filter(user=request.user, completed_at__isnull=False, is_demo=False)
            .select_related("quiz")
            .annotate(
                marks=F("score") * MARKS_PER_QUESTION,
                total_marks=F("total_questions") * MARKS_PER_QUESTION,
            )
            .order_by("-completed_at")
        )
        passed_count = sum(1 for a in attempts if a.passed)
        # Same eligibility rule quiz_result.html uses for its "View
        # Certificate" link -- kept in lockstep so a certificate link never
        # appears here for an attempt that would 404 on quiz_certificate.
        certificates_earned = sum(
            1 for a in attempts
            if a.passed and a.quiz.certificate_enabled and a.percentage >= CERTIFICATE_MIN_PERCENTAGE
        )
        return render(request, "custom_admin/quizzes/my_results.html", {
            "attempts": attempts,
            "total_attempts": len(attempts),
            "passed_count": passed_count,
            "certificates_earned": certificates_earned,
            "certificate_min_percentage": CERTIFICATE_MIN_PERCENTAGE,
        })
