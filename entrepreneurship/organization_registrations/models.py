from django.db import models
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language
# Create your models here.


class Organization_Registration(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    image = ResizedImageField(upload_to="organization_registrations", default="", blank=False, null=False, quality=100, force_format='WEBP')
    title = models.CharField(max_length=255, blank=False, null=False)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    banner = ResizedImageField(upload_to="organization_registrations", default="", blank=True, null=True, quality=100, force_format='WEBP')
    description = models.TextField(null=False, default="", blank=False)
    pdf = models.FileField(upload_to="organization_registrations", default="", null=True, blank=True)
    mode_of_application = models.TextField(max_length=255, default="",  null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class OrganizationRegistrationTranslation(models.Model):
    organization_registration = models.ForeignKey(Organization_Registration, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="organization_registration_translations")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    mode_of_application = models.TextField(blank=True, default="")

    class Meta:
        unique_together = [("organization_registration", "language")]