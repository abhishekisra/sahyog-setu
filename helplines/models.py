from django.db import models
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language
# Create your models here.

class Helplines(TranslatableMixin, models.Model):
     id : models.AutoField(primary_key=True)
     image = ResizedImageField(upload_to="helplines", blank=False, null=False, quality=100, force_format='WEBP')
     link = models.CharField(max_length=255, blank=False, null=False)
     status_type = ((0, 'In Active'), (1, 'Active'))
     status = models.IntegerField(default = 0, choices=status_type)
     title = models.CharField(default="", max_length=255, blank=False, null=False)
     color = models.CharField(default="#000000", max_length=255, blank=False, null=False)
     # Toll-free number as real text -- previously only baked into `image`
     # as a design graphic (Tollfree_Number_N.webp), so a plain-text card
     # redesign (helpline_finder.html) had no way to show it without an
     # image. Backfilled once from the existing 16 graphics; new entries
     # need it filled in via the admin form same as any other field.
     number = models.CharField(default="", max_length=50, blank=True, null=True)
     created_at = models.DateTimeField(auto_now_add= True)
     updated_at = models.DateTimeField(auto_now_add= True)


class HelplineTranslation(models.Model):
    helpline = models.ForeignKey(Helplines, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="helpline_translations")
    title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("helpline", "language")]
