import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import SchemeSerializer, CategorySerializer
from .models import Schemes, Categories
from django.db.models import Q


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
    request_data = json.loads(request.body)
    schemes = Schemes.objects.filter(status = 1, scheme_type = request_data['scheme_type'])

    if request_data['category']:
        schemes = schemes.filter(category_id = request_data['category'])

    if request_data['state']:
        schemes = schemes.filter(state_id = request_data['state'])

    if request_data['dbt']:
        schemes = schemes.filter(dbt = request_data['dbt'])


    if request_data['divyang_category']:
        schemes = schemes.filter(Q(divyang = request_data['divyang_category']) | Q(divyang = 2))
    
    if request_data['beneficiary']:
        schemes = schemes.extra(where=['FIND_IN_SET('+request_data['beneficiary']+', benificiaries)'])

    if request_data['caste']:
        schemes = schemes.extra(where=['FIND_IN_SET('+request_data['caste']+', castes)'])

    if request_data['gender']:
        schemes = schemes.extra(where=['FIND_IN_SET('+request_data['gender']+', scheme_for)'])

    if request_data['marital_status']:
        schemes = schemes.extra(where=['FIND_IN_SET('+request_data['marital_status']+', marital_status)'])

    if request_data['religion']:
        schemes = schemes.extra(where=['FIND_IN_SET('+str(request_data['religion'])+', religions)'])
        
    if request_data['area']:
        schemes = schemes.filter(scheme_areas__area = request_data['area'])

    if request_data['employment']:
        schemes = schemes.filter(scheme_employment__employment = request_data['employment'])

    if request_data['occupation']:
        schemes = schemes.filter(scheme_occupations__occupation_id = request_data['occupation'])

    if request_data['age']:
        schemes = schemes.filter(age_min__lte = request_data['age'], age_max__gte = request_data['age'])

    if request_data['family_income']:
        schemes = schemes.filter(income_min__lte = request_data['family_income'], income_max__gte = request_data['family_income'])
    
    if request_data['searched_text']:
        schemes = schemes.filter(title__icontains = request_data['searched_text'])

    serializer = SchemeSerializer(schemes, many=True)
    return JsonResponse({'schemes' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


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

        if request_data['state']:
            state_schemes = state_schemes.filter(state_id = request_data['state'])

        if request_data['family_income']:
            state_schemes = state_schemes.filter(income_min__lte = request_data['family_income'], income_max__gte = request_data['family_income'])
            central_schemes = central_schemes.filter(income_min__lte = request_data['family_income'], income_max__gte = request_data['family_income'])

        if request_data['divyang_category']:
            state_schemes = state_schemes.filter(Q(divyang = request_data['divyang_category']) | Q(divyang = 2))
            central_schemes = central_schemes.filter(Q(divyang = request_data['divyang_category']) | Q(divyang = 2))
        
        if request_data['beneficiary']:
            state_schemes = state_schemes.extra(where=['FIND_IN_SET(' + str(request_data['beneficiary']) + ', benificiaries)'])
            central_schemes = central_schemes.extra(where=['FIND_IN_SET(' + str(request_data['beneficiary']) + ', benificiaries)'])

        if request_data['caste']:
            state_schemes = state_schemes.extra(where=['FIND_IN_SET(' + str(request_data['caste'])+', castes)'])
            central_schemes = central_schemes.extra(where=['FIND_IN_SET('+str(request_data['caste'])+', castes)'])

        if request_data['gender']:
            state_schemes = state_schemes.extra(where=['FIND_IN_SET('+str(request_data['gender'])+', scheme_for)'])
            central_schemes = central_schemes.extra(where=['FIND_IN_SET('+str(request_data['gender'])+', scheme_for)'])

        if request_data['marital_status']:
            state_schemes = state_schemes.extra(where=['FIND_IN_SET('+str(request_data['marital_status'])+', marital_status)'])
            central_schemes = central_schemes.extra(where=['FIND_IN_SET('+str(request_data['marital_status'])+', marital_status)'])

        if request_data['religion']:
            state_schemes = state_schemes.extra(where=['FIND_IN_SET('+str(request_data['religion'])+', religions)'])
            central_schemes = central_schemes.extra(where=['FIND_IN_SET('+str(request_data['religion'])+', religions)'])
            
        if request_data['area']:
            state_schemes = state_schemes.filter(scheme_areas__area = request_data['area'])
            central_schemes = central_schemes.filter(scheme_areas__area = request_data['area'])

        if request_data['employment']:
            state_schemes = state_schemes.filter(scheme_employment__employment = request_data['employment'])
            central_schemes = central_schemes.filter(scheme_employment__employment = request_data['employment'])

        if request_data['occupation']:
            state_schemes = state_schemes.filter(scheme_occupations__occupation_id = request_data['occupation'])
            central_schemes = central_schemes.filter(scheme_occupations__occupation_id = request_data['occupation'])
        
        state_serializer = SchemeSerializer(state_schemes, many=True)
        central_serializer = SchemeSerializer(central_schemes, many=True)
        return JsonResponse({'state_schemes' : state_serializer.data, 'central_schemes' : central_serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        print(e)