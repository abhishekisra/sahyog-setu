from tokenize import blank_re
from django.db import models
from django.db.models.deletion import CASCADE
from occupations.models import Occupations
from states.models import States
from django_resized import ResizedImageField
from languages.mixins import TranslatableMixin
from languages.models import Language

# Create your models here.

class Categories(TranslatableMixin, models.Model):
    id : models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, blank=False, null=False)
    image = ResizedImageField(upload_to="categories", blank=False, null=False, quality=100, force_format='WEBP')
    banner = ResizedImageField(upload_to="categories", default="", blank=True, null=True, quality=100, force_format='WEBP')
    status_type = ((0, 'In Active'), (1, 'Active'))
    status = models.IntegerField(default = 0, choices=status_type)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now_add= True)



class Schemes(TranslatableMixin, models.Model):
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

    class Meta:
        # 2026-10-19 (VPS indexing audit): the scheme-count queries filter on
        # status + scheme_type / business_related and were full-scanning the
        # table (performance_schema: up to ~4.6k rows examined per row sent).
        indexes = [
            models.Index(fields=['status', 'scheme_type'], name='scheme_status_type_idx'),
            models.Index(fields=['status', 'business_related'], name='scheme_status_biz_idx'),
        ]


class SchemeTranslation(models.Model):
    scheme = models.ForeignKey(Schemes, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="scheme_translations")
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    eligibility = models.TextField(blank=True, default="")
    required_documents = models.TextField(blank=True, default="")
    mode_of_application = models.TextField(blank=True, default="")
    occupations = models.CharField(max_length=255, blank=True, default="")
    scheme_for = models.CharField(max_length=255, blank=True, default="")
    marital_status = models.CharField(max_length=255, blank=True, default="")
    benificiaries = models.CharField(max_length=255, blank=True, default="")
    religions = models.CharField(max_length=255, blank=True, default="")
    castes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("scheme", "language")]


class CategoryTranslation(models.Model):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name="translations")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name="category_translations")
    title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = [("category", "language")]


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

# ---------------------------------------------------------------------------
# "Mere liye yojanayein" (/my-schemes/, 2026-11-06): a participant's saved
# schemes and the extra eligibility details that are NOT on the signup form
# (age, gender, state and occupation already live on accounts.User). Codes
# are the same ones the admin scheme form and /api/check-eligibility use.
# ---------------------------------------------------------------------------
class SavedScheme(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=CASCADE, related_name="saved_schemes")
    scheme = models.ForeignKey(Schemes, on_delete=CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "scheme"], name="uniq_saved_scheme_per_user")]
        ordering = ["-created_at"]


class SchemeProfile(models.Model):
    """All optional: None = "not told us", which never excludes a scheme."""
    user = models.OneToOneField("accounts.User", on_delete=CASCADE, related_name="scheme_profile")
    family_income = models.PositiveIntegerField(null=True, blank=True)   # annual, rupees
    caste = models.SmallIntegerField(null=True, blank=True)              # 0 General 1 OBC 2 SC 3 ST 4 PVTG
    marital_status = models.SmallIntegerField(null=True, blank=True)     # 0 Married 1 Unmarried 2 Widowed 3 Divorced 4 Separated
    religion = models.SmallIntegerField(null=True, blank=True)           # 0 Hindu .. 7 No religion
    divyang = models.SmallIntegerField(null=True, blank=True)            # 0 Yes 1 No (scheme.divyang 2 = both)
    area = models.SmallIntegerField(null=True, blank=True)               # 0 Urban 1 Rural
    updated_at = models.DateTimeField(auto_now=True)
