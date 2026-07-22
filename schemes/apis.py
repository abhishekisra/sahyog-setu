import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import SchemeSerializer, CategorySerializer
from .models import Schemes, Categories
from django.db.models import Q


def _safe_int(value):
    """int(value) or None -- used before any value reaches a raw
    FIND_IN_SET(...) SQL fragment. request_data['x'] here was previously
    string-concatenated straight into .extra(where=[...]) with no cast at
    all in searchSchemes(): a JSON number (TypeError, unhandled -- 500) or
    any non-numeric string (reaches raw SQL unescaped) both got through.
    Only a genuine int's string form (digits, optional leading '-') can
    ever reach the SQL fragment this way."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def globalSearch(request):
    """Search across everything a citizen might be looking for on the
    portal -- schemes, helplines, important portals/documents, and scheme
    announcements -- by title, in one call. Returns a flat, ranked-by-type
    list so a single search bar (see index.html's injected search widget)
    can cover the whole site instead of citizens having to know which
    section a scheme/helpline/document lives in."""
    from helplines.models import Helplines
    from important_portals.models import Important_Portals
    from important_documents.models import Important_Documents
    from scheme_announcements.models import Scheme_Announcements

    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'results': [], 'status': status.HTTP_200_OK}, status=status.HTTP_200_OK)

    results = []

    for s in Schemes.objects.filter(status=1, title__icontains=q)[:8]:
        results.append({
            'type': 'scheme',
            'type_label': 'Central Scheme' if s.scheme_type == 0 else 'State Scheme',
            'title': s.title,
            'url': '/scheme/%d' % s.id,
        })

    for h in Helplines.objects.filter(status=1, title__icontains=q)[:5]:
        results.append({
            'type': 'helpline', 'type_label': 'Helpline',
            'title': h.title, 'url': h.link or '/helplines',
        })

    for p in Important_Portals.objects.filter(status=1, title__icontains=q)[:5]:
        results.append({
            'type': 'portal', 'type_label': 'Important Portal',
            'title': p.title, 'url': '/important-portals',
        })

    for d in Important_Documents.objects.filter(status=1, title__icontains=q)[:5]:
        results.append({
            'type': 'document', 'type_label': 'Important Document',
            'title': d.title, 'url': '/important-documents',
        })

    for a in Scheme_Announcements.objects.filter(status=1, title__icontains=q)[:5]:
        results.append({
            'type': 'announcement', 'type_label': 'Scheme Announcement',
            'title': a.title, 'url': a.link or '/scheme-announcements',
        })

    return JsonResponse({'results': results, 'status': status.HTTP_200_OK}, status=status.HTTP_200_OK)


def schemeCounts(request):
    """Active-record counts for every homepage quick-link card that lists
    something (Central/State Schemes, Helplines, Important Portals,
    Important Documents, Scheme Announcements) -- the React SPA build on
    this box has no source available to wire these up itself, so
    public_base.html's home-counts script (see index.html) fetches this
    single endpoint and injects the numbers directly into each card's DOM."""
    from helplines.models import Helplines
    from important_portals.models import Important_Portals
    from important_documents.models import Important_Documents
    from scheme_announcements.models import Scheme_Announcements

    return JsonResponse({
        'central_schemes': Schemes.objects.filter(status=1, scheme_type=0).count(),
        'state_schemes': Schemes.objects.filter(status=1, scheme_type=1).count(),
        'helplines': Helplines.objects.filter(status=1).count(),
        'important_portals': Important_Portals.objects.filter(status=1).count(),
        'important_documents': Important_Documents.objects.filter(status=1).count(),
        'scheme_announcements': Scheme_Announcements.objects.filter(status=1).count(),
        'status': status.HTTP_200_OK,
    }, status=status.HTTP_200_OK)


def schemesServices(request):
    categories = Categories.objects.filter(status = 1)
    serializer = CategorySerializer(categories, many=True)
    return JsonResponse({'categories' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)

def category(request, id):
    category = Categories.objects.get(status = 1, id = id)
    serializer = CategorySerializer(category, many=False)
    return JsonResponse({'category' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


def stateSchemes(request, state):
    schemes = Schemes.objects.filter(status = 1, scheme_type = 1, state_id = state)
    serializer = SchemeSerializer(schemes, many=True)
    return JsonResponse({'schemes' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


def businessRelatedSchemes(request):
    schemes = Schemes.objects.filter(status = 1, business_related = 1)
    serializer = SchemeSerializer(schemes, many=True)
    return JsonResponse({'schemes' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


def centralSchemes(request, id):
    schemes = Schemes.objects.filter(status = 1, scheme_type = 0, category_id = id)
    serializer = SchemeSerializer(schemes, many=True)
    return JsonResponse({'schemes' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


@csrf_exempt
def searchSchemes(request):
    try:
        request_data = json.loads(request.body)
        schemes = Schemes.objects.filter(status = 1, scheme_type = request_data.get('scheme_type') or 0)

        # `not in (None, '')` rather than truthiness throughout below --
        # dbt=0 ('No'), divyang_category/beneficiary/caste/gender/
        # marital_status/religion=0, age=0, and family_income=0 are all
        # real, legitimate values (see e.g. schemes/views.py's own code
        # for the 0-indexed choice lists) that a plain `if request_data['x']`
        # silently treated as "not provided" and skipped filtering on --
        # concretely, a citizen with zero household income (a very real,
        # common case for exactly the people this site serves) got no
        # income filtering applied at all.
        if request_data.get('category') not in (None, ''):
            schemes = schemes.filter(category_id = request_data['category'])

        if request_data.get('state') not in (None, ''):
            schemes = schemes.filter(state_id = request_data['state'])

        if request_data.get('dbt') not in (None, ''):
            schemes = schemes.filter(dbt = request_data['dbt'])

        if request_data.get('divyang_category') not in (None, ''):
            schemes = schemes.filter(Q(divyang = request_data['divyang_category']) | Q(divyang = 2))

        # FIND_IN_SET fields -- previously string-concatenated straight into
        # raw SQL with no cast at all (beneficiary/caste/gender/
        # marital_status) or just str() (religion), so a JSON number crashed
        # with an uncaught TypeError (this whole view had no try/except),
        # and any non-numeric string reached raw SQL unescaped. _safe_int()
        # both prevents the crash and closes the injection: only a genuine
        # int's own string form can reach the SQL fragment below.
        if request_data.get('beneficiary') not in (None, ''):
            v = _safe_int(request_data['beneficiary'])
            if v is not None:
                schemes = schemes.extra(where=['FIND_IN_SET(%d, benificiaries)' % v])

        if request_data.get('caste') not in (None, ''):
            v = _safe_int(request_data['caste'])
            if v is not None:
                schemes = schemes.extra(where=['FIND_IN_SET(%d, castes)' % v])

        if request_data.get('gender') not in (None, ''):
            v = _safe_int(request_data['gender'])
            if v is not None:
                schemes = schemes.extra(where=['FIND_IN_SET(%d, scheme_for)' % v])

        if request_data.get('marital_status') not in (None, ''):
            v = _safe_int(request_data['marital_status'])
            if v is not None:
                schemes = schemes.extra(where=['FIND_IN_SET(%d, marital_status)' % v])

        if request_data.get('religion') not in (None, ''):
            v = _safe_int(request_data['religion'])
            if v is not None:
                schemes = schemes.extra(where=['FIND_IN_SET(%d, religions)' % v])

        # A scheme with NO area/employment/occupation tag at all (every
        # myscheme.gov.in-imported scheme, since that source has no equivalent
        # taxonomy) means "not tagged", not "excludes everyone" -- same principle
        # as divyang's Q(divyang=2) "Both" above. A plain .filter() here is an
        # inner join that would otherwise silently drop every untagged scheme
        # the moment a user picks ANY value for these three fields.
        if request_data.get('area') not in (None, ''):
            schemes = schemes.filter(Q(scheme_areas__area = request_data['area']) | Q(scheme_areas__isnull=True)).distinct()

        if request_data.get('employment') not in (None, ''):
            schemes = schemes.filter(Q(scheme_employment__employment = request_data['employment']) | Q(scheme_employment__isnull=True)).distinct()

        if request_data.get('occupation') not in (None, ''):
            schemes = schemes.filter(Q(scheme_occupations__occupation_id = request_data['occupation']) | Q(scheme_occupations__isnull=True)).distinct()

        if request_data.get('age') not in (None, ''):
            schemes = schemes.filter(age_min__lte = request_data['age'], age_max__gte = request_data['age'])

        # income_max=0 is how 3,798 of 4,485 myscheme.gov.in-imported schemes
        # store "no income cap" (never set on import) -- a plain income_max__gte
        # comparison treats that literally, so a plain .filter() here would
        # silently exclude the vast majority of schemes for any citizen with
        # income > 0, same "untagged means excluded" bug already fixed above
        # for area/employment/occupation.
        if request_data.get('family_income') not in (None, ''):
            schemes = schemes.filter(income_min__lte = request_data['family_income']).filter(
                Q(income_max__gte = request_data['family_income']) | Q(income_max = 0))

        if request_data.get('searched_text'):
            schemes = schemes.filter(title__icontains = request_data['searched_text'])

        serializer = SchemeSerializer(schemes, many=True)
        return JsonResponse({'schemes' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except (ValueError, TypeError, KeyError) as e:
        return JsonResponse({'message': 'Invalid request', 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)


def scheme(request, id):
    try:
        scheme = Schemes.objects.get(status = 1, id = id)
        serializer = SchemeSerializer(scheme, many=False)
        return JsonResponse({'scheme' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
def checkEligibility(request):
    try:
        request_data = json.loads(request.body)
        state_schemes = Schemes.objects.filter(status = 1, scheme_type = 1)
        central_schemes = Schemes.objects.filter(status = 1, scheme_type = 0)

        # `not in (None, '')` rather than truthiness throughout below -- see
        # searchSchemes()'s comment for why (0 is a real value for several
        # of these fields, not "not provided").
        if request_data.get('state') not in (None, ''):
            state_schemes = state_schemes.filter(state_id = request_data['state'])

        # Age was collected on the form (it's a required question) but never
        # actually sent to this endpoint or filtered on here at all -- every
        # scheme matched regardless of the stated age range, so an 18-40
        # scheme would show up for a 59-year-old and a 60+ scheme for a
        # 40-year-old. Same age_min/age_max range check searchSchemes() uses.
        if request_data.get('age') not in (None, ''):
            state_schemes = state_schemes.filter(age_min__lte = request_data['age'], age_max__gte = request_data['age'])
            central_schemes = central_schemes.filter(age_min__lte = request_data['age'], age_max__gte = request_data['age'])

        # See searchSchemes() above -- income_max=0 means "no cap" for most
        # imported schemes, so it has to match rather than exclude.
        if request_data.get('family_income') not in (None, ''):
            state_schemes = state_schemes.filter(income_min__lte = request_data['family_income']).filter(
                Q(income_max__gte = request_data['family_income']) | Q(income_max = 0))
            central_schemes = central_schemes.filter(income_min__lte = request_data['family_income']).filter(
                Q(income_max__gte = request_data['family_income']) | Q(income_max = 0))

        if request_data.get('divyang_category') not in (None, ''):
            state_schemes = state_schemes.filter(Q(divyang = request_data['divyang_category']) | Q(divyang = 2))
            central_schemes = central_schemes.filter(Q(divyang = request_data['divyang_category']) | Q(divyang = 2))

        # FIND_IN_SET fields -- str() alone (the previous cast here) avoids
        # a TypeError but doesn't sanitize: a non-numeric string still
        # reaches raw SQL unescaped. _safe_int() both validates and closes
        # that off -- see searchSchemes() above for the full explanation.
        if request_data.get('beneficiary') not in (None, ''):
            v = _safe_int(request_data['beneficiary'])
            if v is not None:
                state_schemes = state_schemes.extra(where=['FIND_IN_SET(%d, benificiaries)' % v])
                central_schemes = central_schemes.extra(where=['FIND_IN_SET(%d, benificiaries)' % v])

        if request_data.get('caste') not in (None, ''):
            v = _safe_int(request_data['caste'])
            if v is not None:
                state_schemes = state_schemes.extra(where=['FIND_IN_SET(%d, castes)' % v])
                central_schemes = central_schemes.extra(where=['FIND_IN_SET(%d, castes)' % v])

        if request_data.get('gender') not in (None, ''):
            v = _safe_int(request_data['gender'])
            if v is not None:
                state_schemes = state_schemes.extra(where=['FIND_IN_SET(%d, scheme_for)' % v])
                central_schemes = central_schemes.extra(where=['FIND_IN_SET(%d, scheme_for)' % v])

        if request_data.get('marital_status') not in (None, ''):
            v = _safe_int(request_data['marital_status'])
            if v is not None:
                state_schemes = state_schemes.extra(where=['FIND_IN_SET(%d, marital_status)' % v])
                central_schemes = central_schemes.extra(where=['FIND_IN_SET(%d, marital_status)' % v])

        if request_data.get('religion') not in (None, ''):
            v = _safe_int(request_data['religion'])
            if v is not None:
                state_schemes = state_schemes.extra(where=['FIND_IN_SET(%d, religions)' % v])
                central_schemes = central_schemes.extra(where=['FIND_IN_SET(%d, religions)' % v])

        # See searchSchemes() above for why an untagged scheme has to match
        # rather than be excluded -- every myscheme.gov.in import has no
        # area/employment/occupation tags at all (no equivalent taxonomy on
        # that source), so a plain inner-join filter here would make all
        # 4,485 imported schemes invisible on this page forever, the moment
        # a real user picks any value for these three (required) fields.
        if request_data.get('area') not in (None, ''):
            state_schemes = state_schemes.filter(Q(scheme_areas__area = request_data['area']) | Q(scheme_areas__isnull=True)).distinct()
            central_schemes = central_schemes.filter(Q(scheme_areas__area = request_data['area']) | Q(scheme_areas__isnull=True)).distinct()

        if request_data.get('employment') not in (None, ''):
            state_schemes = state_schemes.filter(Q(scheme_employment__employment = request_data['employment']) | Q(scheme_employment__isnull=True)).distinct()
            central_schemes = central_schemes.filter(Q(scheme_employment__employment = request_data['employment']) | Q(scheme_employment__isnull=True)).distinct()

        if request_data.get('occupation') not in (None, ''):
            state_schemes = state_schemes.filter(Q(scheme_occupations__occupation_id = request_data['occupation']) | Q(scheme_occupations__isnull=True)).distinct()
            central_schemes = central_schemes.filter(Q(scheme_occupations__occupation_id = request_data['occupation']) | Q(scheme_occupations__isnull=True)).distinct()

        state_serializer = SchemeSerializer(state_schemes, many=True)
        central_serializer = SchemeSerializer(central_schemes, many=True)
        return JsonResponse({'state_schemes' : state_serializer.data, 'central_schemes' : central_serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except (ValueError, TypeError, KeyError) as e:
        # Previously: `except Exception: print(e)` with no return at all --
        # any exception here (including the SQL errors this same fix
        # closes off above) fell through to an implicit `None`, which
        # Django itself then crashes on ("view didn't return an
        # HttpResponse") -- a worse, more opaque failure than a normal
        # error response, and the real error was only ever printed to
        # stdout, never actually logged.
        return JsonResponse({'message': 'Invalid request', 'status': status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)