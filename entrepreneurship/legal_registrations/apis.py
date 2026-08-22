import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import LegalRegistrationSerializer
from .models import Legal_Registrations
from languages.utils import clean_language



def legalRegistrations(request):
    legal_registrations = Legal_Registrations.objects.filter(status = 1)
    serializer = LegalRegistrationSerializer(legal_registrations, many=True)
    return JsonResponse({'legal_registrations' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def legalRegistration(request, id):
    # Optional ?lang= -- absent (the untouched legacy SPA never sends it)
    # gives byte-identical output to before.
    try:
        legal_registration = Legal_Registrations.objects.get(status = 1, id = id)
        serializer = LegalRegistrationSerializer(legal_registration, many=False)
        data = dict(serializer.data)
        lang = clean_language(request.GET.get('lang', 'en'))
        if lang != 'en':
            data['title'] = legal_registration.field_for('title', lang)
            data['description'] = legal_registration.field_for('description', lang)
            data['eligibility'] = legal_registration.field_for('eligibility', lang)
            data['required_documents'] = legal_registration.field_for('required_documents', lang)
            data['mode_of_application'] = legal_registration.field_for('mode_of_application', lang)
        return JsonResponse({'legal_registration' : data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)