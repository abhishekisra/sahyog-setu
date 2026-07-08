import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import MarketingSerializer
from .models import Marketing



def marketing(request):
    marketing = Marketing.objects.filter(status = 1)
    serializer = MarketingSerializer(marketing, many=True)
    return JsonResponse({'marketing' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
