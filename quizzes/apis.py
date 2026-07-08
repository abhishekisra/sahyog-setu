import datetime
import json
import os
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import QuizzesSerializer, QuizSerializer
from .models import Quizzes, QuizAttempt, QuestionResponse
from accounts.models import User
from django.db.models import Count

from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Frame
from reportlab.lib import colors

pdfmetrics.registerFont(
    TTFont("CinzelBold", os.path.join(settings.BASE_DIR, "quizzes/fonts/Cinzel-Bold.ttf"))
)

pdfmetrics.registerFont(
    TTFont("GreatVibes", os.path.join(settings.BASE_DIR, "quizzes/fonts/GreatVibes-Regular.ttf"))
)

pdfmetrics.registerFont(
    TTFont("Cormorant", os.path.join(settings.BASE_DIR, "quizzes/fonts/Cormorant-Regular.ttf"))
)

def quizzes(request):
    quizzes = Quizzes.objects.filter(status = 1).annotate(
        total_questions=Count("questions")
    )
    serializer = QuizzesSerializer(quizzes, many=True)
    return JsonResponse({'quizzes' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def quiz(request, id):
    try:
        quiz = Quizzes.objects.annotate(
            total_questions=Count("questions")
        ).get(id = id)
        serializer = QuizSerializer(quiz, many=False)
        return JsonResponse({'quiz' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Quizzes.DoesNotExist:
        return JsonResponse({'message' : "Quiz doesn't exists.", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
def submitQuiz(request, id):
    """Mobile quiz submission — scoring happens here, server-side, against
    the real correct_option values. The client only ever sends its picked
    options, never a score, so there is nothing for it to spoof. Mirrors
    the web quiz_submit view's logic (see quizzes/views.py)."""

    if request.method != "POST":
        return JsonResponse({'message': 'Invalid request', 'status': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    try:
        request_data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'message': 'Invalid JSON body', 'status': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    client_id = request_data.get("client_id")
    answers = request_data.get("answers") or {}

    if not client_id:
        return JsonResponse({'message': 'client_id is required', 'status': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    try:
        quiz = Quizzes.objects.get(id=id, status=True)
    except Quizzes.DoesNotExist:
        return JsonResponse({'message': "Quiz doesn't exist.", 'status': status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

    try:
        user = User.objects.get(client_id=client_id, user_type=2)
    except User.DoesNotExist:
        return JsonResponse({'message': 'Unknown client_id — register via /api/user first.', 'status': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    if quiz.one_attempt_only and QuizAttempt.objects.filter(quiz=quiz, user=user, completed_at__isnull=False).exists():
        return JsonResponse({'message': 'You have already attempted this quiz.', 'status': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    questions = list(quiz.questions.all())
    total_questions = len(questions)
    score = 0
    responses = []

    for question in questions:
        selected_option = str(answers.get(str(question.id), ""))
        correct_option = str(question.correct_option)
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

    attempt = QuizAttempt.objects.create(
        user=user,
        quiz=quiz,
        score=score,
        total_questions=total_questions,
        percentage=percentage,
        passed=passed,
        completed_at=timezone.now(),
    )

    for response in responses:
        response.attempt = attempt
    QuestionResponse.objects.bulk_create(responses)

    return JsonResponse({
        'attempt_id': attempt.id,
        'score': score,
        'total_questions': total_questions,
        'percentage': round(percentage, 1),
        'passed': passed,
        'status': status.HTTP_200_OK,
    }, status=status.HTTP_200_OK)



@csrf_exempt
def generateCertificate(request):
    """Certificate PDF is only ever built from a verified, completed,
    passed QuizAttempt row — never from client-submitted name/score.
    (Previously trusted a raw `score` field straight from the request
    body, so anyone could generate a certificate claiming any score.)"""

    if request.method != "POST":
        return HttpResponse("Invalid request", status=400)

    request_data = json.loads(request.body)

    attempt_id = request_data.get("attempt_id")
    quiz_id = request_data.get("quiz_id")

    if not attempt_id or not quiz_id:
        return HttpResponse("attempt_id and quiz_id are required", status=400)

    try:
        attempt = QuizAttempt.objects.select_related("user", "quiz").get(
            id=attempt_id, quiz_id=quiz_id, completed_at__isnull=False
        )
    except QuizAttempt.DoesNotExist:
        return HttpResponse("Attempt not found or not completed", status=404)

    if not attempt.passed:
        return HttpResponse("Certificate is only available for a passed attempt.", status=403)

    quiz = attempt.quiz
    name = attempt.user.get_full_name().strip() or attempt.user.username
    score = round(attempt.percentage)

    buffer = BytesIO()

    width, height = landscape(A4)
    center = width / 2

    p = canvas.Canvas(buffer, pagesize=(width, height))

    # =====================================================
    # BACKGROUND
    # =====================================================

    p.setFillColor(HexColor("#faf8ef"))
    p.rect(0, 0, width, height, fill=1)

    # outer border
    p.setStrokeColor(HexColor("#C8A951"))
    p.setLineWidth(10)
    p.rect(30, 30, width-60, height-60)

    # inner border
    p.setStrokeColor(HexColor("#222222"))
    p.setLineWidth(1.5)
    p.rect(50, 50, width-100, height-100)

    # =====================================================
    # LOGOS
    # =====================================================

    logo_size = 80

    if quiz.logo_1 and os.path.exists(quiz.logo_1.path):
        logo = ImageReader(quiz.logo_1.path)
        p.drawImage(logo, 90, height-140, width=logo_size, height=logo_size, mask="auto")

    if quiz.logo_2 and os.path.exists(quiz.logo_2.path):
        logo = ImageReader(quiz.logo_2.path)
        p.drawImage(logo, width-170, height-140, width=logo_size, height=logo_size, mask="auto")

    # =====================================================
    # TITLE
    # =====================================================

    p.setFillColor(colors.black)

    p.setFont("CinzelBold", 52)
    p.drawCentredString(center, height-120, "CERTIFICATE")

    p.setFont("CinzelBold", 24)
    p.drawCentredString(center, height-155, "OF ACHIEVEMENT")

    p.setStrokeColor(HexColor("#C8A951"))
    p.setLineWidth(2)
    p.line(center-90, height-170, center+90, height-170)

    # =====================================================
    # PRESENTED TEXT
    # =====================================================

    presented_y = height - 240

    p.setFont("Cormorant", 20)
    p.drawCentredString(center, presented_y, "This Certificate is Proudly Presented To")

    # =====================================================
    # NAME
    # =====================================================

    name_length = len(name)

    if name_length <= 15:
        name_size = 38
    elif name_length <= 25:
        name_size = 32
    elif name_length <= 35:
        name_size = 28
    else:
        name_size = 24

    name_y = presented_y - 65

    p.setFont("GreatVibes", name_size)
    p.setFillColor(HexColor("#1e2820"))
    p.drawCentredString(center, name_y, name)

    # divider
    p.setStrokeColor(HexColor("#C8A951"))
    p.setLineWidth(1.5)
    p.line(center-200, name_y-10, center+200, name_y-10)

    # =====================================================
    # CERTIFICATE DESCRIPTION
    # =====================================================

    text_content = quiz.certificate_text or \
        f"For successfully completing '{quiz.title}' with a score of {score}%."

    style = ParagraphStyle(
        name="certificate",
        fontName="Cormorant",
        fontSize=18,
        alignment=1,
        leading=26,
        textColor=colors.black
    )

    paragraph = Paragraph(text_content, style)

    frame = Frame(
        200,
        name_y-110,
        width-400,
        80,
        showBoundary=0
    )

    frame.addFromList([paragraph], p)

    # =====================================================
    # SIGNATURES
    # =====================================================

    sign_y = 170

    sign_width = 120
    sign_height = 60

    p.setFillColor(colors.black)

    # Authority 1
    if quiz.authority1_sign_image and os.path.exists(quiz.authority1_sign_image.path):
        sign = ImageReader(quiz.authority1_sign_image.path)
        p.drawImage(sign, 160, sign_y, width=sign_width, height=sign_height, mask="auto")

    p.line(150, sign_y-10, 350, sign_y-10)

    p.setFont("CinzelBold", 16)
    p.drawCentredString(250, sign_y-35, quiz.authority1_name)

    p.setFont("Cormorant", 14)
    p.drawCentredString(250, sign_y-55, quiz.authority1_designation)

    # Authority 2
    if quiz.authority2_sign_image and os.path.exists(quiz.authority2_sign_image.path):
        sign = ImageReader(quiz.authority2_sign_image.path)
        p.drawImage(sign, width-280, sign_y, width=sign_width, height=sign_height, mask="auto")

    p.line(width-350, sign_y-10, width-150, sign_y-10)

    p.setFont("CinzelBold", 16)
    p.drawCentredString(width-250, sign_y-35, quiz.authority2_name)

    p.setFont("Cormorant", 14)
    p.drawCentredString(width-250, sign_y-55, quiz.authority2_designation)

    # =====================================================
    # ISSUE DATE (FOOTER)
    # =====================================================

    issue_date = timezone.now().strftime('%d %B %Y')

    p.setFont("Cormorant", 16)
    p.setFillColor(colors.black)

    p.drawCentredString(center, 90, f"Issued on {issue_date}")

    # =====================================================

    p.showPage()
    p.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{name}_certificate.pdf"'

    return response