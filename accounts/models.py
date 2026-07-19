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

    # Signup demographic/location fields. state/district are FKs (not free
    # text) so the cascading dropdowns on signup stay backed by a real,
    # queryable hierarchy -- PROTECT (not CASCADE) so an admin can never
    # accidentally delete a district that real users are already
    # registered against.
    GENDER_CHOICES = (("male", "Male"), ("female", "Female"), ("other", "Other"))
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    state = models.ForeignKey("states.States", on_delete=models.PROTECT, related_name="users", blank=True, null=True)
    district = models.ForeignKey("states.District", on_delete=models.PROTECT, related_name="users", blank=True, null=True)
    occupation = models.ForeignKey("occupations.Occupations", on_delete=models.PROTECT, related_name="users", blank=True, null=True)
    # Optional -- most registrants aren't affiliated with an NGO/SHG, and
    # there's no existing NGO/SHG directory in this project to FK against,
    # so this stays a plain optional text field rather than a lookup table.
    ngo_shg_name = models.CharField(max_length=255, blank=True, null=True)

    # Explicit consent to the Privacy Policy / Terms & Conditions, required
    # at signup (SignupForm rejects submission without it) -- a timestamp,
    # not just a boolean, so there's a real record of *when* consent was
    # given if the policy text is ever updated later. Never set retroactively
    # for accounts that signed up before this field existed (stays NULL for
    # those, which is the honest state -- they were never asked).
    consent_accepted_at = models.DateTimeField(null=True, blank=True)
