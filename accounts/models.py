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

    # Google Sign-In identity (the token's `sub` claim) -- unlike client_id
    # above (client-submitted, unverified, used by the older /api/user sync),
    # this is only ever set after server-side ID token verification in
    # GoogleLoginView, so it's safe to treat as a real, un-spoofable account
    # key. unique+null=True: most existing mobile+password accounts never
    # signed in with Google and must stay NULL, not collide on ''.
    google_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    # Captured once at profile completion (one-time permission prompt, not
    # tracked continuously) -- lets the admin analytics dashboard show a
    # rough geographic spread of participants without a live location feed.
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
