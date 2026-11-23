"""Switch a language on (or off) for visitors, in both language lists (quiz + content). 2026-11-23.
A language stays hidden until its machine translations are imported and checked."""
from django.core.management.base import BaseCommand

from languages.models import Language as ContentLanguage
from quizzes.models import Language as QuizLanguage


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("codes", help="comma list, e.g. ta,bn")
        parser.add_argument("--off", action="store_true")

    def handle(self, *a, **o):
        codes = [c.strip() for c in o["codes"].split(",") if c.strip()]
        for M in (ContentLanguage, QuizLanguage):
            n = M.objects.filter(code__in=codes).update(is_active=not o["off"])
            self.stdout.write(f"{M._meta.app_label}: {n} language(s) {'off' if o['off'] else 'on'}")
