from tokenize import blank_re
from django.db import models
from django.db.models.deletion import CASCADE
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language

class Pages(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    image = ResizedImageField(upload_to="pages", default="", blank=False, null=False, quality=100, force_format='WEBP')
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    description = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class PageTranslation(models.Model):
    page = models.ForeignKey(Pages, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="page_translations")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("page", "language")]


