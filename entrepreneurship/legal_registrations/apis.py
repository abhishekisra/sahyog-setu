import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import LegalRegistrationSerializer
from .models import Legal_Registrations



def legalRegistrations(request):
    legal_registrations = Legal_Registrations.objects.filter(status = 1)
    serializer = LegalRegistrationSerializer(legal_registrations, many=True)
    return JsonResponse({'legal_registrations' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def legalRegistration(request, id):
    try:
        legal_registration = Legal_Registrations.objects.get(status = 1, id = id)
        serializer = LegalRegistrationSerializer(legal_registration, many=False)
        return JsonResponse({'legal_registration' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)