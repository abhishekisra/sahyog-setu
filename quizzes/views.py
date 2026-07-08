import random

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Avg
from .models import Questions, Quizzes, QuizAttempt, QuestionResponse



class QuizzesView(View):

    def get(self, request):
        if request.user.is_authenticated:
            quizzes = Quizzes.objects.all().order_by("-id")
            return render(request,"custom_admin/quizzes/quizzes.html",{"quizzes": quizzes})

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

        return render(request,"custom_admin/quizzes/edit-quiz.html",{"quiz":quiz})


    def post(self, request, id):

        try:
            quiz = Quizzes.objects.get(id=id)

            # Update quiz
            quiz.title = request.POST.get("title")
            quiz.description = request.POST.get("description")
            quiz.certificate_text = request.POST.get("certificate_text")
            quiz.status = request.POST.get("status")
            quiz.quiz_time = request.POST.get("quiz_time")
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
# PARTICIPANT QUIZ FLOW
# ======================================================================

def _session_keys(quiz_id):
    return f"quiz_{quiz_id}_attempt_id", f"quiz_{quiz_id}_question_ids"


@method_decorator(login_required, name='dispatch')
class QuizTakeView(View):

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quizzes, id=quiz_id, status=True)

        if not quiz.is_live:
            messages.error(request, "यह क्विज़ अभी उपलब्ध नहीं है।")
            return redirect("/")

        completed_attempts = QuizAttempt.objects.filter(quiz=quiz, completed_at__isnull=False)

        if quiz.one_attempt_only:
            existing = completed_attempts.filter(user=request.user).order_by('-completed_at').first()
            if existing:
                return redirect("quiz_result", pk=existing.id)

        attempt_key, question_ids_key = _session_keys(quiz.id)

        attempt = None
        attempt_id = request.session.get(attempt_key)
        if attempt_id:
            attempt = QuizAttempt.objects.filter(
                id=attempt_id, user=request.user, quiz=quiz, completed_at__isnull=True
            ).first()

        question_ids = request.session.get(question_ids_key)

        if not attempt or not question_ids:
            # Fresh attempt: lock in a random question set and start the
            # server-side timer now. Reusing an in-progress attempt (above)
            # instead of always creating a new one prevents a participant
            # from resetting their time limit by simply reloading the page.
            bank_ids = list(quiz.questions.values_list("id", flat=True))
            sample_size = min(quiz.questions_per_attempt, len(bank_ids))
            question_ids = random.sample(bank_ids, sample_size) if bank_ids else []

            attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)

            request.session[attempt_key] = attempt.id
            request.session[question_ids_key] = question_ids

        questions_by_id = Questions.objects.in_bulk(question_ids)
        questions = [questions_by_id[qid] for qid in question_ids if qid in questions_by_id]

        avg_percentage = completed_attempts.aggregate(avg=Avg('percentage'))['avg'] or 0

        return render(request, "custom_admin/quizzes/quiz_take.html", {
            "quiz": quiz,
            "questions": questions,
            "total_questions": len(questions),
            "completed_count": completed_attempts.count(),
            "avg_percentage": round(avg_percentage, 1),
        })


@login_required
def quiz_submit(request, quiz_id):
    quiz = get_object_or_404(Quizzes, id=quiz_id, status=True)

    if request.method != "POST":
        return redirect("quiz_take", quiz_id=quiz.id)

    attempt_key, question_ids_key = _session_keys(quiz.id)
    attempt_id = request.session.get(attempt_key)

    if not attempt_id:
        messages.error(request, "आपका क्विज़ सत्र समाप्त हो गया है। कृपया फिर से शुरू करें।")
        return redirect("quiz_take", quiz_id=quiz.id)

    attempt = get_object_or_404(
        QuizAttempt, id=attempt_id, user=request.user, quiz=quiz, completed_at__isnull=True
    )

    question_ids = request.session.get(question_ids_key) or list(
        quiz.questions.values_list("id", flat=True)
    )
    questions_by_id = Questions.objects.in_bulk(question_ids)
    questions = [questions_by_id[qid] for qid in question_ids if qid in questions_by_id]

    # Server-side timer: elapsed time is always derived from when the attempt
    # row was created (started_at), never from anything the client sends.
    elapsed_seconds = (timezone.now() - attempt.started_at).total_seconds()

    total_questions = len(questions)
    score = 0
    responses = []

    for question in questions:
        selected_option = request.POST.get(f"question_{question.id}", "")
        correct_option = str(question.correct_option)
        # A blank selected_option can never equal correct_option, so an
        # unanswered question is always scored wrong -- including when time
        # has run out, which is exactly "mark unanswered questions as wrong"
        # without needing to special-case the timeout.
        is_correct = selected_option == correct_option
        if is_correct:
            score += 1

        responses.append(QuestionResponse(
            question=question,
            question_text_snapshot=question.question,
            selected_option=selected_option,
            correct_option=correct_option,
            is_correct=is_correct,
            explanation_snapshot=question.explanation,
        ))

    percentage = (score / total_questions * 100) if total_questions else 0
    passed = percentage >= quiz.pass_threshold

    attempt.score = score
    attempt.total_questions = total_questions
    attempt.percentage = percentage
    attempt.passed = passed
    attempt.time_taken_seconds = int(elapsed_seconds)
    attempt.completed_at = timezone.now()
    attempt.save()

    for response in responses:
        response.attempt = attempt
    QuestionResponse.objects.bulk_create(responses)

    request.session.pop(attempt_key, None)
    request.session.pop(question_ids_key, None)

    return redirect("quiz_result", pk=attempt.id)


@method_decorator(login_required, name='dispatch')
class QuizResultView(View):

    def get(self, request, pk):
        attempt = get_object_or_404(QuizAttempt, pk=pk, user=request.user)
        responses = attempt.responses.all()
        correct = responses.filter(is_correct=True).count()
        incorrect = attempt.total_questions - correct

        return render(request, "custom_admin/quizzes/quiz_result.html", {
            "attempt": attempt,
            "responses": responses,
            "correct": correct,
            "incorrect": incorrect,
            "percentage": attempt.percentage,
            "pass_threshold": attempt.quiz.pass_threshold,
        })


class QuizLeaderboardView(View):

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quizzes, id=quiz_id)
        is_staff = request.user.is_authenticated and request.user.is_staff

        if not is_staff and not quiz.leaderboard_public:
            messages.error(request, "यह लीडरबोर्ड सार्वजनिक नहीं है।")
            return redirect("quiz_take", quiz_id=quiz.id)

        attempts = QuizAttempt.objects.filter(
            quiz=quiz, completed_at__isnull=False
        ).select_related("user").order_by("-score", "time_taken_seconds")[:100]

        return render(request, "custom_admin/quizzes/quiz_leaderboard.html", {
            "quiz": quiz,
            "attempts": attempts,
        })
