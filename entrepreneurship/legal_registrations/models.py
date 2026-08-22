from tokenize import blank_re
from django.db import models
from django.db.models.deletion import CASCADE
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language


class Legal_Registrations(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    image = ResizedImageField(upload_to="legal_registrations", default="", blank=False, null=False, quality=100, force_format='WEBP')
    banner = ResizedImageField(upload_to="legal_registrations", default="", blank=True, null=True, quality=100, force_format='WEBP')
    title = models.CharField(max_length=255, blank=False, null=False)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    description = models.TextField(null=False, blank=False)
    eligibility = models.TextField(null=False, blank=False)
    required_documents = models.TextField(null=False, blank=False)
    web_links = models.TextField(max_length=255, null=False, blank=False)
    mode_of_application = models.TextField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class LegalRegistrationTranslation(models.Model):
    legal_registration = models.ForeignKey(Legal_Registrations, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="legal_registration_translations")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    eligibility = models.TextField(blank=True, default="")
    required_documents = models.TextField(blank=True, default="")
    mode_of_application = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("legal_registration", "language")]


