from django.db import models
from django.db.models.deletion import CASCADE
from django_resized import ResizedImageField


class Business_Plans(models.Model):
    id : models.AutoField(primary_key=True)
    image = ResizedImageField(upload_to="business_plans", default="", blank=False, null=False, quality=100, force_format='WEBP')     
    title = models.CharField(max_length=255, blank=False, null=False)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    pdf = models.FileField(upload_to="business_plans", default="", blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)

