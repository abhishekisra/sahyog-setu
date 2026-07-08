import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import HelplinesSerializer
from .models import Helplines



def helplines(request):
    helplines = Helplines.objects.filter(status = 1)
    serializer = HelplinesSerializer(helplines, many=True)
    return JsonResponse({'helplines' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
