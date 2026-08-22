from django.db import models
from languages.mixins import TranslatableMixin
from languages.models import Language

# Create your models here.

class Occupations(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default=0, choices=status_type)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class OccupationTranslation(models.Model):
    occupation = models.ForeignKey(Occupations, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="occupation_translations")
    title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("occupation", "language")]
