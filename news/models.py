from django.db import models
from languages.mixins import TranslatableMixin
from languages.models import Language

# Create your models here.

class News(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    news = models.CharField(max_length=255, blank=False, null=False)
    link = models.CharField(max_length=255, blank=True, null=True, default="")
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default=0, choices=status_type)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class NewsTranslation(models.Model):
    news_item = models.ForeignKey(News, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="news_translations")
    news = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("news_item", "language")]
