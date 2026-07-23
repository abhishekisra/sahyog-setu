import html as html_module
import json

from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.utils.html import strip_tags
from django.utils.text import Truncator

from occupations.models import Occupations
from states.models import States
from .models import Categories, Scheme_Occupations, Schemes, Scheme_Areas, Scheme_Employements

# Every valid code for each CSV-stored eligibility field (see edit-scheme.html
# select options) -- a scheme "open to everyone" on that dimension has ALL of
# these codes present in its comma-separated field, same convention the
# myscheme.gov.in import already uses for the vast majority of schemes.
SCHEME_FOR_ALL = ['0', '1', '2']
CASTES_ALL = ['0', '1', '2', '3', '4']
RELIGIONS_ALL = ['0', '1', '2', '3', '4', '5', '6', '7']
MARITAL_ALL = ['0', '1', '2', '3', '4']
BENIFICIARIES_ALL = ['0', '1', '2', '3', '4', '5', '6']

def _open_to_all_ids(qs, field, codes):
    """IDs of schemes whose CSV `field` contains every code in `codes` --
    i.e. not restricted on that dimension. codes/field are always from the
    fixed lists above (never user input), so the raw FIND_IN_SET is safe."""
    for code in codes:
        qs = qs.extra(where=[f"FIND_IN_SET({code}, {field})"])
    return qs.values_list('id', flat=True)



# Create your views here.

class CategoriesView(View):

    def get(self, request):
        if request.user.is_authenticated:
            categories = Categories.objects.all()
            return render(request, 'custom_admin/manage-schemes/categories.html', {'categories': categories})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')

        
    def post(self, request):
        if request.user.is_authenticated:
            category =  Categories()
            category.title = request.POST.get('title')
            category.status = int(request.POST.get('status'))
            if request.FILES:
                category.image = request.FILES['image']
                category.banner = request.FILES['banner']
                category.save()
                messages.success(request, "Category added sucessfully")
                return redirect('adminSchemeCategories')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminCategories')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteCategory(request):
    if request.user.is_authenticated:
        category_id = request.POST.get('id')
        category = Categories.objects.get(id = category_id) 
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect('adminSchemeCategories')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateCategory(request, id):
    if request.user.is_authenticated:
        category = Categories.objects.get(id = id) 
        if 'image' in request.FILES:
            category.image = request.FILES['image']
        if 'banner' in request.FILES:
            category.banner = request.FILES['banner']
        category.title = request.POST.get('title')
        category.status = int(request.POST.get('status'))
        category.save()
        messages.success(request, "Category updated successfully.")
        return redirect('adminSchemeCategories')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')





# Create your views here.

class SchemesView(View):
    def get(self, request):
        if request.user.is_authenticated:
            schemes = Schemes.objects.select_related('category').order_by('-id')

            status = request.GET.get('status', '')
            if status in ('0', '1'):
                schemes = schemes.filter(status=int(status))

            source = request.GET.get('source', '')
            if source == 'myscheme':
                schemes = schemes.filter(myscheme_slug__isnull=False)
            elif source == 'manual':
                schemes = schemes.filter(myscheme_slug__isnull=True)

            category_id = request.GET.get('category', '')
            if category_id:
                schemes = schemes.filter(category_id=category_id)

            # Key-point eligibility filters -- lets an admin spot-check exactly
            # the fields most likely to wrongly exclude someone if guessed
            # wrong (gender/caste/religion), plus a catch-all "other" for
            # marital status/beneficiary-type/divyang/age/income, each as a
            # simple "has any restriction at all" vs "open to everyone" toggle
            # rather than filtering to one specific code (the combinations are
            # too numerous -- 16+ distinct caste combos alone -- to be a
            # useful dropdown; what actually matters for review is "did we
            # narrow this at all").
            gender_filter = request.GET.get('gender', '')
            if gender_filter in ('restricted', 'open'):
                open_ids = _open_to_all_ids(schemes, 'scheme_for', SCHEME_FOR_ALL)
                schemes = schemes.filter(id__in=open_ids) if gender_filter == 'open' else schemes.exclude(id__in=open_ids)

            caste_filter = request.GET.get('caste', '')
            if caste_filter in ('restricted', 'open'):
                open_ids = _open_to_all_ids(schemes, 'castes', CASTES_ALL)
                schemes = schemes.filter(id__in=open_ids) if caste_filter == 'open' else schemes.exclude(id__in=open_ids)

            religion_filter = request.GET.get('religion', '')
            if religion_filter in ('restricted', 'open'):
                open_ids = _open_to_all_ids(schemes, 'religions', RELIGIONS_ALL)
                schemes = schemes.filter(id__in=open_ids) if religion_filter == 'open' else schemes.exclude(id__in=open_ids)

            age_filter = request.GET.get('age', '')
            if age_filter == 'restricted':
                schemes = schemes.exclude(age_min=0, age_max=100)
            elif age_filter == 'open':
                schemes = schemes.filter(age_min=0, age_max=100)

            # Catch-all "other" -- marital status/beneficiary-type/divyang/income,
            # each open only if every code is present (or, for divyang/income,
            # the specific sentinel meaning "no restriction" -- divyang=2 is
            # "Both" per the existing eligibility-checker convention, and
            # income_max=0 is how every uncapped myscheme.gov.in import is
            # stored, matching 3798/4485 schemes).
            other_filter = request.GET.get('other', '')
            if other_filter in ('restricted', 'open'):
                open_ids = set(_open_to_all_ids(schemes, 'marital_status', MARITAL_ALL))
                open_ids &= set(_open_to_all_ids(schemes, 'benificiaries', BENIFICIARIES_ALL))
                open_ids &= set(schemes.filter(divyang=2).values_list('id', flat=True))
                open_ids &= set(schemes.filter(income_max=0).values_list('id', flat=True))
                schemes = schemes.filter(id__in=open_ids) if other_filter == 'open' else schemes.exclude(id__in=open_ids)

            paginator = Paginator(schemes, 50)
            page_obj = paginator.get_page(request.GET.get('page'))

            querystring = request.GET.copy()
            querystring.pop('page', None)

            return render(request, "custom_admin/manage-schemes/schemes/schemes.html", {
                'page_obj': page_obj,
                'categories': Categories.objects.all(),
                'selected_status': status,
                'selected_source': source,
                'selected_category': category_id,
                'selected_gender': gender_filter,
                'selected_caste': caste_filter,
                'selected_religion': religion_filter,
                'selected_age': age_filter,
                'selected_other': other_filter,
                'querystring': querystring.urlencode(),
                'total_count': paginator.count,
            })
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')


class BulkActivateSchemesView(View):
    """Activates every Schemes row matching the SAME filters currently applied
    on the list page (not just the current page's 50 rows) -- lets an admin
    approve, say, "all myScheme-imported Education schemes" in one action
    after skimming them, rather than 50-at-a-time or one-by-one via the edit
    form. Only ever flips status -- never touches any other field."""

    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')

        schemes = Schemes.objects.all()

        status = request.POST.get('status', '')
        if status in ('0', '1'):
            schemes = schemes.filter(status=int(status))

        source = request.POST.get('source', '')
        if source == 'myscheme':
            schemes = schemes.filter(myscheme_slug__isnull=False)
        elif source == 'manual':
            schemes = schemes.filter(myscheme_slug__isnull=True)

        category_id = request.POST.get('category', '')
        if category_id:
            schemes = schemes.filter(category_id=category_id)

        updated = schemes.update(status=1)
        messages.success(request, f"{updated} scheme(s) activated.")
        return redirect(request.META.get('HTTP_REFERER') or 'adminSchemes')




class SchemeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            occupations = Occupations.objects.all()
            categories = Categories.objects.all()
            states = States.objects.all()
            return render(request, "custom_admin/manage-schemes/schemes/new-scheme.html", {'occupations': occupations, 'categories' : categories, 'states' : states})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                if request.FILES:
                    scheme = Schemes()
                    scheme.title = request.POST.get('title')
                    scheme.banner = request.FILES['banner']
                    scheme.category_id = request.POST.get('category_id')
                    scheme.scheme_type = request.POST.get('scheme_type')
                    scheme.state_id = request.POST.get('state')
                    scheme.dbt = request.POST.get('dbt')
                    scheme.business_related = request.POST.get('business_related')
                    scheme.status = request.POST.get('status')
                    scheme.divyang = request.POST.get('divyang')
                    
                    scheme.description = request.POST.get('description')
                    scheme.eligibility = request.POST.get('eligibility')
                    scheme.required_documents = request.POST.get('required_documents')
                    scheme.web_links = request.POST.get('web_links')
                    scheme.age_max = request.POST.get('age_max')
                    scheme.age_min = request.POST.get('age_min')
                    scheme.income_max = request.POST.get('income_max')
                    scheme.income_min = request.POST.get('income_min')
                    scheme.mode_of_application = request.POST.get('mode_of_application')

                    scheme.castes = ','.join(request.POST.getlist('caste'))
                    scheme.scheme_for = ','.join(request.POST.getlist('scheme_for'))
                    scheme.benificiaries = ','.join(request.POST.getlist('benificiaries'))
                    scheme.marital_status = ','.join(request.POST.getlist('marital_status'))
                    scheme.religions = ','.join(request.POST.getlist('religions'))
                    scheme.save()

                    if scheme.id:
                        Scheme_Occupations.objects.bulk_create([
                            Scheme_Occupations(scheme_id = scheme.id, occupation_id = occupation) for occupation in request.POST.getlist('occupations')
                        ])

                        Scheme_Areas.objects.bulk_create([
                            Scheme_Areas(scheme_id = scheme.id, area = area) for area in request.POST.getlist('areas')
                        ])

                        Scheme_Employements.objects.bulk_create([
                            Scheme_Employements(scheme_id = scheme.id, employment = employment) for employment in request.POST.getlist('employments')
                        ])

                    messages.success(request, "Scheme saved successfully.")
                    return redirect('adminSchemes')
                else:
                    messages.error(request, "Image is required.")
                    return redirect('adminNewScheme')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditSchemeView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                occupations = Occupations.objects.all()
                categories = Categories.objects.all()
                states = States.objects.all()
                scheme = Schemes.objects.get(id = id)
                scheme_occupations = list(Scheme_Occupations.objects.filter(scheme_id = id).values_list('occupation_id', flat=True))
                scheme_occupations = ','.join(map(str, scheme_occupations))
                employments = list(Scheme_Employements.objects.filter(scheme_id = id).values_list('employment', flat=True))
                employments = ','.join(map(str, employments))
                areas = list(Scheme_Areas.objects.filter(scheme_id = id).values_list('area', flat=True))
                areas = ','.join(map(str, areas))
                return render(request, "custom_admin/manage-schemes/schemes/edit-scheme.html", {'occupations': occupations, 'categories' : categories, 'states' : states, 'scheme' : scheme, 'scheme_occupations' : scheme_occupations, "employments" : employments, "areas" : areas})
            except Schemes.DoesNotExist:
                messages.error(request, "Schemes doesn't exists.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                scheme = Schemes.objects.get(id = id)
                scheme.title = request.POST.get('title')
                scheme.category_id = request.POST.get('category_id')
                scheme.scheme_type = request.POST.get('scheme_type')
                scheme.state_id = request.POST.get('state')
                scheme.business_related = request.POST.get('business_related')
                scheme.dbt = request.POST.get('dbt')
                scheme.status = request.POST.get('status')
                scheme.divyang = request.POST.get('divyang')
                
                scheme.description = request.POST.get('description')
                scheme.eligibility = request.POST.get('eligibility')
                scheme.required_documents = request.POST.get('required_documents')
                scheme.web_links = request.POST.get('web_links')
                scheme.age_max = request.POST.get('age_max')
                scheme.age_min = request.POST.get('age_min')
                scheme.income_max = request.POST.get('income_max')
                scheme.income_min = request.POST.get('income_min')
                scheme.mode_of_application = request.POST.get('mode_of_application')

                scheme.castes = ','.join(request.POST.getlist('caste'))
                scheme.scheme_for = ','.join(request.POST.getlist('scheme_for'))
                scheme.benificiaries = ','.join(request.POST.getlist('benificiaries'))
                scheme.marital_status = ','.join(request.POST.getlist('marital_status'))
                scheme.religions = ','.join(request.POST.getlist('religions'))

                if 'banner' in request.FILES:
                    scheme.banner = request.FILES['banner']
                scheme.save()

                if scheme.id:
                    Scheme_Occupations.objects.filter(scheme_id = id).delete()
                    Scheme_Areas.objects.filter(scheme_id = id).delete()
                    Scheme_Employements.objects.filter(scheme_id = id).delete()
                    Scheme_Occupations.objects.bulk_create([
                        Scheme_Occupations(scheme_id = scheme.id, occupation_id = occupation) for occupation in request.POST.getlist('occupations')
                    ])
                    
                    Scheme_Areas.objects.bulk_create([
                        Scheme_Areas(scheme_id = scheme.id, area = area) for area in request.POST.getlist('areas')
                    ])

                    Scheme_Employements.objects.bulk_create([
                        Scheme_Employements(scheme_id = scheme.id, employment = employment) for employment in request.POST.getlist('employments')
                    ])

                messages.success(request, "Scheme saved successfully.")
                return redirect('adminSchemes')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteScheme(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        scheme = Schemes.objects.get(id = id)
        scheme.delete()
        messages.success(request, "Scheme deleted successfully.")
        return redirect('adminSchemes')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def admin_scheme_detail(request, id):
    """Admin-only (login required) preview JSON for the "View" button on
    the Manage Schemes list -- NOT the public /api/scheme/<id>, which
    filters status=1 and so 400s on an inactive/draft scheme an admin is
    specifically trying to check before activating it."""
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Login required"}, status=403)
    try:
        scheme = Schemes.objects.get(id=id)
    except Schemes.DoesNotExist:
        return JsonResponse({"message": "Invalid scheme id"}, status=404)
    return JsonResponse({"scheme": {
        "title": scheme.title,
        "description": scheme.description,
        "eligibility": scheme.eligibility,
        "required_documents": scheme.required_documents,
    }})


def central_category_finder(request):
    """Public, no login -- replaces the old SPA's Central Govt Schemes
    category-grid landing page (/schemes-and-services/central), which used
    plain image+title+"Click Here" cards in the old design. Each card here
    links straight to scheme_finder's own ?category=<id> deep link (already
    fully supported there: banner, dropdown pre-selection, filtered count)
    instead of the old /schemes/central/<id> intermediate route."""
    categories = list(Categories.objects.filter(status=1).order_by('title'))
    counts = {
        row['category_id']: row['count']
        for row in Schemes.objects.filter(status=1, scheme_type=0, category_id__in=[c.id for c in categories])
            .values('category_id').annotate(count=Count('id'))
    }
    for c in categories:
        c.scheme_count = counts.get(c.id, 0)
    return render(request, "custom_admin/schemes/central_category_finder.html", {
        "categories": categories,
    })


def scheme_finder(request):
    """Public, no login -- the "Scheme Viewer" finder. Filtering hits
    scheme_search_light below (NOT the existing /api/schemes -- see there
    for why), and opening a card's detail view hits the existing, already-
    small /api/scheme/<id>. This view just renders the page shell and a
    couple of real counts for the hero stats."""
    total_schemes = Schemes.objects.filter(status=1).count()
    total_categories = Categories.objects.filter(status=1).count()
    return render(request, "custom_admin/schemes/scheme_finder.html", {
        "total_schemes": total_schemes,
        "total_categories": total_categories,
    })


@csrf_exempt
def scheme_search_light(request):
    """Filtered scheme search for the Scheme Viewer page -- deliberately
    NOT reusing the existing /api/schemes (schemes.apis.searchSchemes): that
    endpoint returns the FULL SchemeSerializer (description, eligibility,
    required_documents, web_links, mode_of_application -- every long-text
    field) for EVERY matching row with no pagination at all. A plain,
    no-filter page load matched 710 schemes and shipped ~4MB of JSON before
    a single card could render, which is what made the page feel like it
    hung on load, especially on the slow mobile connections most of this
    site's real visitors are on.

    Same filter semantics as searchSchemes (scheme_type, category, age,
    family_income, marital_status, religion, caste, divyang_category,
    searched_text), but returns only list-card-sized fields, paginated at
    PAGE_SIZE, so a page load/filter change only ever ships the ~8-16
    schemes actually about to be shown. Full detail (all those long-text
    fields) loads separately, on demand, via the existing /api/scheme/<id>
    when a visitor actually opens a card -- that response is already small
    since it's a single scheme, not a whole result set.
    """
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    schemes = Schemes.objects.filter(status=1, scheme_type=int(body.get('scheme_type') or 0))

    if body.get('category'):
        schemes = schemes.filter(category_id=body['category'])
    if body.get('state'):
        schemes = schemes.filter(state_id=body['state'])
    if body.get('divyang_category') not in (None, ''):
        from django.db.models import Q
        schemes = schemes.filter(Q(divyang=body['divyang_category']) | Q(divyang=2))
    if body.get('caste') not in (None, ''):
        schemes = schemes.extra(where=['FIND_IN_SET(%s, castes)' % int(body['caste'])])
    if body.get('marital_status') not in (None, ''):
        schemes = schemes.extra(where=['FIND_IN_SET(%s, marital_status)' % int(body['marital_status'])])
    if body.get('religion') not in (None, ''):
        schemes = schemes.extra(where=['FIND_IN_SET(%s, religions)' % int(body['religion'])])
    if body.get('gender') not in (None, ''):
        schemes = schemes.extra(where=['FIND_IN_SET(%s, scheme_for)' % int(body['gender'])])
    # `not in (None, '')` rather than truthiness -- age=0 (a real, selectable
    # slider position, for infant-eligibility schemes) and family_income=0
    # are valid filter values that a plain `if body.get(...)` would silently
    # skip, since both are falsy in Python.
    if body.get('age') not in (None, ''):
        schemes = schemes.filter(age_min__lte=body['age'], age_max__gte=body['age'])
    if body.get('family_income') not in (None, ''):
        from django.db.models import Q
        schemes = schemes.filter(income_min__lte=body['family_income']).filter(
            Q(income_max__gte=body['family_income']) | Q(income_max=0))
    if body.get('searched_text'):
        schemes = schemes.filter(title__icontains=body['searched_text'])

    schemes = schemes.select_related('state').order_by('-id')
    total = schemes.count()
    page = max(1, int(body.get('page') or 1))
    paginator = Paginator(schemes, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for s in page_obj.object_list:
        desc = html_module.unescape(strip_tags(s.description or ""))
        results.append({
            "id": s.id,
            "title": s.title,
            "state": s.state.state if s.state_id else "",
            "short_description": Truncator(desc.strip()).chars(130),
            "age_min": s.age_min,
            "age_max": s.age_max,
            "income_max": s.income_max,
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })


def business_related_scheme_finder(request):
    """Public, no login -- Business Development Schemes (Schemes rows with
    business_related=1) in the Scheme Viewer's own style, replacing the old
    SPA page that showed a title + bare "Click Here" button with no image
    at all for every single card (Schemes has no image field to begin
    with -- unlike Important_Portals etc., this was never a missing-data
    problem, just a page with no visual treatment). No filter sidebar --
    search box + icon-accented card grid + the same detail overlay
    scheme_finder.html uses (these ARE real Schemes rows, with the same
    description/eligibility/required_documents/web_links content)."""
    total = Schemes.objects.filter(status=1, business_related=1).count()
    return render(request, "custom_admin/schemes/business_related_scheme_finder.html", {
        "total_business_schemes": total,
    })


@csrf_exempt
def business_related_scheme_search_light(request):
    """Paginated search for Business Development Schemes -- same reasoning
    as scheme_search_light above, filtered to business_related=1. Detail
    is fetched on demand from the existing /api/scheme/<id>, same as the
    main Scheme Viewer."""
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    schemes = Schemes.objects.filter(status=1, business_related=1)
    if body.get('searched_text'):
        schemes = schemes.filter(title__icontains=body['searched_text'])
    schemes = schemes.order_by('-id')

    total = schemes.count()
    page = max(1, int(body.get('page') or 1))
    paginator = Paginator(schemes, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for s in page_obj.object_list:
        desc = html_module.unescape(strip_tags(s.description or ""))
        results.append({
            "id": s.id,
            "title": s.title,
            "short_description": Truncator(desc.strip()).chars(130),
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })


