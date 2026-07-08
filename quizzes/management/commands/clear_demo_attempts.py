from django.core.management.base import BaseCommand

from accounts.models import User
from quizzes.models import QuizAttempt

DEMO_USERNAME_PREFIX = "demo_participant_"


class Command(BaseCommand):
    help = "Delete all demo (is_demo=True) QuizAttempt rows and their demo_participant_* users. Asks for confirmation first."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")

    def handle(self, *args, **options):
        attempts = QuizAttempt.objects.filter(is_demo=True)
        demo_users = User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)

        attempt_count = attempts.count()
        user_count = demo_users.count()

        if attempt_count == 0 and user_count == 0:
            self.stdout.write("Nothing to clear -- no demo attempts or demo users found.")
            return

        self.stdout.write(
            f"This will delete {attempt_count} demo QuizAttempt row(s) (their QuestionResponse "
            f"rows go with them via cascade) and {user_count} demo_participant_* user(s)."
        )

        if not options["yes"]:
            answer = input("Type 'yes' to confirm: ").strip().lower()
            if answer != "yes":
                self.stdout.write("Aborted -- nothing deleted.")
                return

        attempts.delete()
        demo_users.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {attempt_count} demo attempt(s) and {user_count} demo user(s)."
        ))
