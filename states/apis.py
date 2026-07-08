import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import StateSerializer
from .models import States



def states(request):
    states = States.objects.all()
    serializer = StateSerializer(states, many=True)
    return JsonResponse({'states' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


