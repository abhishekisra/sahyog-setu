import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import OccupationSerializer
from .models import Occupations



def occupations(request):
    occupations = Occupations.objects.filter(status = 1)
    serializer = OccupationSerializer(occupations, many=True)
    return JsonResponse({'occupations' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


