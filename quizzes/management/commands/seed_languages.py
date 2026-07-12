from django.core.management.base import BaseCommand

from quizzes.models import Language

# The 22 languages in the Eighth Schedule of the Indian Constitution.
# English is deliberately NOT a row here -- it's the base language on
# Quizzes/Questions themselves (title/question/option_1.../explanation),
# never a translation, so it needs no Language row (see clean_language()
# in quizzes/views.py, which always accepts 'en' without a DB lookup).
LANGUAGES = [
    ("as", "Assamese", "অসমীয়া"),
    ("bn", "Bengali", "বাংলা"),
    ("brx", "Bodo", "बड़ो"),
    ("doi", "Dogri", "डोगरी"),
    ("gu", "Gujarati", "ગુજરાતી"),
    ("hi", "Hindi", "हिन्दी"),
    ("kn", "Kannada", "ಕನ್ನಡ"),
    ("ks", "Kashmiri", "کٲشُر"),
    ("kok", "Konkani", "कोंकणी"),
    ("mai", "Maithili", "मैथिली"),
    ("ml", "Malayalam", "മലയാളം"),
    ("mni", "Manipuri", "মৈতৈলোন্"),
    ("mr", "Marathi", "मराठी"),
    ("ne", "Nepali", "नेपाली"),
    ("or", "Odia", "ଓଡ଼ିଆ"),
    ("pa", "Punjabi", "ਪੰਜਾਬੀ"),
    ("sa", "Sanskrit", "संस्कृतम्"),
    ("sat", "Santali", "ᱥᱟᱱᱛᱟᱲᱤ"),
    ("sd", "Sindhi", "سنڌي"),
    ("ta", "Tamil", "தமிழ்"),
    ("te", "Telugu", "తెలుగు"),
    ("ur", "Urdu", "اردو"),
]


class Command(BaseCommand):
    help = "Seed the Language table with English + all 22 Eighth Schedule Indian languages. Safe to re-run (update_or_create)."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for i, (code, name, native_name) in enumerate(LANGUAGES):
            obj, was_created = Language.objects.update_or_create(
                code=code,
                defaults={"name": name, "native_name": native_name, "sort_order": i},
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Languages seeded: {created} created, {updated} already existed (updated)."
        ))
