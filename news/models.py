from django.db import models

# Create your models here.

class News(models.Model):
    id : models.AutoField(primary_key=True)
    news = models.CharField(max_length=255, blank=False, null=False)
    link = models.CharField(max_length=255, blank=True, null=True, default="")
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default=0, choices=status_type)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)
