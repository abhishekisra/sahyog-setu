import random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from accounts.models import User
from quizzes.models import QuestionResponse, QuizAttempt, Quizzes

DEMO_USERNAME_PREFIX = "demo_participant_"


class Command(BaseCommand):
    help = (
        "Seed fake QuizAttempt (+ QuestionResponse) rows, marked is_demo=True, "
        "so the /quiz-analytics/ dashboard can be previewed before real traffic "
        "exists. Never attaches attempts to a real (non-demo) user."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=300, help="Number of demo attempts to create.")
        parser.add_argument(
            "--force", action="store_true",
            help="Allow running even when settings.DEBUG is False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "settings.DEBUG is False -- this looks like production. Refusing to seed "
                "demo data. Pass --force if you really mean it."
            )

        count = options["count"]
        if count <= 0:
            raise CommandError("--count must be a positive integer.")

        quizzes = list(Quizzes.objects.prefetch_related("questions").all())
        if not quizzes:
            raise CommandError("No quizzes exist yet -- create at least one quiz before seeding demo attempts.")

        self.stdout.write(f"Seeding {count} demo attempts across {len(quizzes)} quiz(zes)...")

        with transaction.atomic():
            users, created_user_count = self._get_or_create_demo_users(count)
            attempts = self._build_attempts(users, quizzes)

            # bulk_create deliberately used instead of .save() in a loop --
            # QuizAttempt.started_at is auto_now_add, which .save() would
            # silently force to "now" and destroy the backdated spread that
            # makes the daily-attempts chart meaningful. bulk_create bypasses
            # auto_now_add entirely and inserts exactly what's on the instance.
            max_id_before = QuizAttempt.objects.aggregate(m=Max("id"))["m"] or 0
            QuizAttempt.objects.bulk_create(attempts)

            # MySQL has no RETURNING clause, so bulk_create() can't populate
            # real pks back onto the Python objects we just built -- refetch
            # the rows we just inserted by id instead of trusting those
            # in-memory instances (which all still have pk=None here).
            created_attempts = list(
                QuizAttempt.objects.filter(id__gt=max_id_before, is_demo=True).select_related("quiz")
            )

            responses = self._build_responses(created_attempts)
            if responses:
                QuestionResponse.objects.bulk_create(responses)

        completed = sum(1 for a in created_attempts if a.completed_at is not None)
        self.stdout.write(self.style.SUCCESS(
            f"Done -- {len(created_attempts)} demo attempts created ({completed} completed, "
            f"{len(created_attempts) - completed} abandoned), {created_user_count} new demo user(s), "
            f"{len(responses)} demo question responses."
        ))

    def _get_or_create_demo_users(self, count):
        users = []
        created = 0
        for i in range(1, count + 1):
            username = f"{DEMO_USERNAME_PREFIX}{i:03d}"
            # Hard safety backstop: the username is always built from our own
            # prefix + counter here, never looked up from existing accounts,
            # so a demo attempt can never end up attached to a real user.
            assert username.startswith(DEMO_USERNAME_PREFIX)

            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "user_type": 2,
                    "is_active": False,
                    "name": f"Demo Participant {i:03d}",
                },
            )
            if was_created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
                created += 1
            assert not user.is_active and not user.has_usable_password()
            users.append(user)
        return users, created

    def _build_attempts(self, users, quizzes):
        now = timezone.now()
        attempts = []
        for user in users:
            quiz = random.choice(quizzes)
            bank_size = quiz.questions.count()
            total_questions = min(quiz.questions_per_attempt or 10, bank_size) if bank_size else (quiz.questions_per_attempt or 10)

            started = now - timezone.timedelta(
                days=random.randint(0, 89), minutes=random.randint(0, 1439)
            )

            # ~12% abandoned (never submitted) so completed_at__isnull=False
            # filters actually get exercised by the demo data, same as the
            # real world where rural users drop off on network loss.
            abandoned = random.random() < 0.12

            attempt = QuizAttempt(
                user=user,
                quiz=quiz,
                is_demo=True,
                started_at=started,
                total_questions=total_questions,
            )

            if abandoned:
                attempt.score = 0
                attempt.percentage = 0.0
                attempt.passed = False
                attempt.completed_at = None
                attempt.time_taken_seconds = None
            else:
                percentage = max(0.0, min(100.0, random.gauss(62, 18)))
                score = round(percentage / 100 * total_questions) if total_questions else 0
                quiz_minutes = quiz.quiz_time or 15
                taken_seconds = random.randint(30, max(60, quiz_minutes * 60))

                attempt.score = score
                attempt.percentage = percentage
                attempt.passed = percentage >= quiz.pass_threshold
                attempt.completed_at = started + timezone.timedelta(seconds=taken_seconds)
                attempt.time_taken_seconds = taken_seconds

            attempts.append(attempt)
        return attempts

    def _build_responses(self, attempts):
        """One QuestionResponse per question for each COMPLETED attempt,
        sampled from that quiz's real question bank, so the 'most-failed
        questions' analytics panel has something to show under ?demo=1.
        Abandoned attempts get no responses -- they never submitted."""
        responses = []
        for attempt in attempts:
            if attempt.completed_at is None:
                continue
            bank = list(attempt.quiz.questions.all())
            if not bank:
                continue
            sample = random.sample(bank, min(attempt.total_questions, len(bank)))
            # Roughly matches the attempt's own percentage so a low-scoring
            # attempt actually produces mostly-wrong responses, not random noise.
            correct_probability = attempt.percentage / 100
            for question in sample:
                is_correct = random.random() < correct_probability
                correct_option = str(question.correct_option)
                if is_correct:
                    selected_option = correct_option
                else:
                    wrong_choices = [o for o in ("1", "2", "3", "4") if o != correct_option]
                    selected_option = random.choice(wrong_choices)
                responses.append(QuestionResponse(
                    attempt=attempt,
                    question=question,
                    question_text_snapshot=question.question,
                    selected_option=selected_option,
                    correct_option=correct_option,
                    is_correct=is_correct,
                    explanation_snapshot=question.explanation,
                ))
        return responses
