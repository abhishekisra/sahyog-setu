from django.db import models

# Create your models here.

class States(models.Model):
    id : models.AutoField(primary_key=True)
    state = models.CharField(max_length=255, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)
