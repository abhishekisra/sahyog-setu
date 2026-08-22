import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import OrganizationRegistrationSerializer
from .models import Organization_Registration
from languages.utils import clean_language



def organizationRegistrations(request):
    organization_registrations = Organization_Registration.objects.filter(status = 1)
    serializer = OrganizationRegistrationSerializer(organization_registrations, many=True)
    return JsonResponse({'organization_registrations' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def organizationRegistration(request, id):
    # Optional ?lang= -- absent (the untouched legacy SPA never sends it)
    # gives byte-identical output to before.
    try:
        organization_registration = Organization_Registration.objects.get(status = 1, id = id)
        serializer = OrganizationRegistrationSerializer(organization_registration, many=False)
        data = dict(serializer.data)
        lang = clean_language(request.GET.get('lang', 'en'))
        if lang != 'en':
            data['title'] = organization_registration.field_for('title', lang)
            data['description'] = organization_registration.field_for('description', lang)
            data['mode_of_application'] = organization_registration.field_for('mode_of_application', lang)
        return JsonResponse({'organization_registration' : data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid organization registration id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)