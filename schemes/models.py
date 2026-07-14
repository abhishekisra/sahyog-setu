from tokenize import blank_re
from django.db import models
from django.db.models.deletion import CASCADE
from occupations.models import Occupations
from states.models import States
from django_resized import ResizedImageField

# Create your models here.

class Categories(models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    image = ResizedImageField(upload_to="categories", blank=False, null=False, quality=100, force_format='WEBP')
    banner = ResizedImageField(upload_to="categories", default="", blank=True, null=True, quality=100, force_format='WEBP')
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)



class Schemes(models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    # Set only for schemes imported from myscheme.gov.in -- lets the import
    # command re-run without creating duplicates (skips any slug already
    # present) and is never touched by the manual admin CRUD forms, which
    # don't have a field for it. Null for every hand-entered scheme.
    myscheme_slug = models.CharField(max_length=255, blank=True, null=True, unique=True)
    banner = ResizedImageField(upload_to="schemes", default="", blank=True, null=True, quality=100, force_format='WEBP')
    types = ((0, 'Central'), (1, 'State'))
    scheme_type = models.IntegerField(default = 0, choices=types)
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    business_related = models.IntegerField(default = 0, choices=((0, 'No'), (1, 'Yes')))
    dbt = models.IntegerField(default = 0, choices=((0, 'No'), (1, 'Yes')))
    category = models.ForeignKey(Categories, blank=False, null=False, on_delete=CASCADE, related_name='scheme_category')
    state = models.ForeignKey(States, blank=True, null=True, default ="", on_delete=CASCADE, related_name='scheme_category')
    income_max = models.IntegerField(default=0, null=False, blank=False)
    income_min = models.IntegerField(default=0, null=False, blank=False)
    divyang = models.IntegerField(default=0, null=False, blank=False)
    description = models.TextField(null=False, blank=False)
    eligibility = models.TextField(null=False, blank=False)
    required_documents = models.TextField(null=False, blank=False)
    web_links = models.TextField(max_length=255, null=False, blank=False)
    mode_of_application = models.TextField(max_length=255, null=False, blank=False)
    occupations = models.CharField(max_length=255, null=False, blank=False)
    age_max = models.IntegerField(blank=False, null=False)
    age_min = models.IntegerField(blank=False, null=False)
    scheme_for = models.CharField(max_length=255, blank=False, null=False)
    marital_status = models.CharField(max_length=255, blank=False, null=False)
    benificiaries = models.CharField(max_length=255, blank = False, null=False)
    religions = models.CharField(max_length=255, blank = False, null=False)
    castes = models.CharField(max_length=255, blank = False, null=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)




class Scheme_Occupations(models.Model):
    id : models.AutoField(primary_key=True)
    scheme = models.ForeignKey(Schemes, blank=False, null=False, on_delete=CASCADE, related_name='scheme_occupations')
    occupation = models.ForeignKey(Occupations, blank=False, null=False, on_delete=CASCADE, related_name='scheme_occupation')
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class Scheme_Areas(models.Model):
    id : models.AutoField(primary_key=True)
    scheme = models.ForeignKey(Schemes, blank=False, null=False, on_delete=CASCADE, related_name='scheme_areas')
    area = models.IntegerField(default="", blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)


class Scheme_Employements(models.Model):
    id : models.AutoField(primary_key=True)
    scheme = models.ForeignKey(Schemes, blank=False, null=False, on_delete=CASCADE, related_name='scheme_employment')
    employment = models.IntegerField(default="", blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)