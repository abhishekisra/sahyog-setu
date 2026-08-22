from django.db import models
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language
# Create your models here.


class Important_Portals(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    image = ResizedImageField(upload_to="important_portals", default="", blank=False, null=False, quality=100, force_format='WEBP')
    banner = ResizedImageField(upload_to="important_portals", default="", blank=True, null=True, quality=100, force_format='WEBP')
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    description = models.TextField(null=False, blank=False)
    mode_of_application = models.TextField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class ImportantPortalTranslation(models.Model):
    important_portal = models.ForeignKey(Important_Portals, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="important_portal_translations")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    mode_of_application = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("important_portal", "language")]