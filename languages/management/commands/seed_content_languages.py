from django.core.management.base import BaseCommand

from languages.models import Language

# The 22 languages in the Eighth Schedule of the Indian Constitution.
# English is deliberately NOT a row here -- it's the base language on each
# translatable content model itself (title/description/etc.), never a
# translation, so it needs no Language row (see clean_language() in
# languages/utils.py, which always accepts 'en' without a DB lookup).
#
# This list intentionally matches quizzes/management/commands/seed_languages.py
# for consistency, but seeds this app's own separate Language table --
# the quizzes app and its Language table are untouched by this command.
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
    help = "Seed the languages app's Language table with all 22 Eighth Schedule Indian languages (+ implicit English base). Safe to re-run (update_or_create)."

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
