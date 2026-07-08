from django.db import models
from django_resized import ResizedImageField
# Create your models here.


class Organization_Registration(models.Model):
    id : models.AutoField(primary_key=True)
    image = ResizedImageField(upload_to="organization_registrations", default="", blank=False, null=False, quality=100, force_format='WEBP')     
    title = models.CharField(max_length=255, blank=False, null=False)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    banner = ResizedImageField(upload_to="organization_registrations", default="", blank=True, null=True, quality=100, force_format='WEBP')    
    description = models.TextField(null=False, default="", blank=False)
    pdf = models.FileField(upload_to="organization_registrations", default="", null=True, blank=True)
    mode_of_application = models.TextField(max_length=255, default="",  null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)