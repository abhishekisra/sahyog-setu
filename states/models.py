from django.db import models
from django_resized import ResizedImageField

# Create your models here.

class States(models.Model):
    id : models.AutoField(primary_key=True)
    state = models.CharField(max_length=255, blank=False, null=False)
    # Culturally-representative photo used on the State Govt Scheme card
    # grid (state_category_finder.html) -- blank/null since existing rows
    # predate this field; the card grid falls back to a plain accent block
    # for any state without one.
    image = ResizedImageField(upload_to="states", blank=True, null=True, quality=90, force_format='WEBP')
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class District(models.Model):
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
