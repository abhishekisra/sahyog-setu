from django.db import models
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language

# Create your models here.

class States(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    state = models.CharField(max_length=255, blank=False, null=False)
    # Culturally-representative photo used on the State Govt Scheme card
    # grid (state_category_finder.html) -- blank/null since existing rows
    # predate this field; the card grid falls back to a plain accent block
    # for any state without one.
    image = ResizedImageField(upload_to="states", blank=True, null=True, quality=90, force_format='WEBP')
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class District(TranslatableMixin, models.Model):
    """One row per district, scoped to its state -- signup's District
    dropdown is populated by AJAX-filtering on state_id so it only ever
    shows districts that actually belong to the state the user already
    picked."""
    state = models.ForeignKey(States, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("state", "name")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.state.state})"


class StateTranslation(models.Model):
    state = models.ForeignKey(States, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="state_translations")
    state_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("state", "language")]


class DistrictTranslation(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="district_translations")
    name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("district", "language")]
