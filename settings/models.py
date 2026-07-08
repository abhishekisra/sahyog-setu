from django.db import models

# Create your models here.


class Settings(models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    info = models.TextField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)