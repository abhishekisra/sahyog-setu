import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import BannersSerializer
from .models import Banners



def banners(request):
    banners = Banners.objects.filter(status = 1)
    serializer = BannersSerializer(banners, many=True)
    return JsonResponse({'banners' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
