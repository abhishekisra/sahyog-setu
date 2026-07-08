from tokenize import blank_re
from django.db import models
from django.db.models.deletion import CASCADE
from django_resized import ResizedImageField

class Pages(models.Model):
    id : models.AutoField(primary_key=True) 
    title = models.CharField(max_length=255, blank=False, null=False)
    image = ResizedImageField(upload_to="pages", default="", blank=False, null=False, quality=100, force_format='WEBP')     
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    description = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


