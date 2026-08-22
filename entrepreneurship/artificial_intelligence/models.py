from django.db import models
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language
# Create your models here.

class Artificial_Intelligence(TranslatableMixin, models.Model):
     id : models.AutoField(primary_key=True)
     image = ResizedImageField(upload_to="artifical_intellengence", blank=False, null=False, quality=100, force_format='WEBP')
     link = models.CharField(max_length=255, blank=False, null=False)
     status_type = ((0, 'In Active'), (1, 'Active'))
     status = models.IntegerField(default = 0, choices=status_type)
     title = models.CharField(default="", max_length=255, blank=False, null=False)
     color = models.CharField(default="#000000", max_length=255, blank=False, null=False)
     created_at = models.DateTimeField(auto_now_add= True)
     updated_at = models.DateTimeField(auto_now_add= True)


class ArtificialIntelligenceTranslation(models.Model):
    artificial_intelligence = models.ForeignKey(Artificial_Intelligence, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="artificial_intelligence_translations")
    title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("artificial_intelligence", "language")]
