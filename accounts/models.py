from django.db import models
from django.db.models.deletion import CASCADE
from django.db.models.fields import AutoField, CharField, DateField
from django.contrib.auth.models import AbstractUser
# from . import manager

# Create your models here.

class User(AbstractUser):
    user_type_data = ((1, 'Admin'), (2, 'User'))
    user_type = models.IntegerField(default =2, choices=user_type_data)
    email = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null = True)
    profile_pic = models.CharField(max_length=255, blank=True, null = True)
    client_id = models.CharField(max_length=255, blank=True, null=True)
    