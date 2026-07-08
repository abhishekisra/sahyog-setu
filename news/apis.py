import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import NewsSerializer
from .models import News



def news(request):
    news = News.objects.filter(status = 1)
    serializer = NewsSerializer(news, many=True)
    return JsonResponse({'news' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
