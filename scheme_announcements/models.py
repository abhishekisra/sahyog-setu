from django.db import models
from django.db.models.deletion import CASCADE
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language

class Scheme_Announcements(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    # size=[2000,2000] explicit -- without it this silently fell back to the
    # package's own default of 1920x1080 (no DJANGORESIZED_DEFAULT_SIZE set
    # in settings.py). No crop: ResizedImageField's img.thumbnail() only
    # scales DOWN to fit within the box, preserving aspect ratio -- a
    # non-square upload is never cropped, and an already-smaller image is
    # left as-is (never upscaled).
    image = ResizedImageField(upload_to="scheme_announcements", size=[2000, 2000], default="", blank=False, null=False, quality=100, force_format='WEBP')
    title = models.CharField(max_length=255, blank=False, null=False)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    link = models.CharField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class SchemeAnnouncementTranslation(models.Model):
    scheme_announcement = models.ForeignKey(Scheme_Announcements, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="scheme_announcement_translations")
    title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("scheme_announcement", "language")]

