from django.db import models
from django_resized import ResizedImageField
# Create your models here.

class Testimonials(models.Model):
     id : models.AutoField(primary_key=True)
     image = ResizedImageField(upload_to="testimonials", blank=False, null=False, quality=100, force_format='WEBP')     
     status_type = ((0, 'In Active'), (1, 'Active'))
     status = models.IntegerField(default = 0, choices=status_type)
     created_at = models.DateTimeField(auto_now_add= True)
     updated_at = models.DateTimeField(auto_now_add= True)
