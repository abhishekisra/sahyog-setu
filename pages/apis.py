import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import PageSerializer
from .models import Pages
from django.db.models import Q


def pages(request):
    pages = Pages.objects.filter(status = 1)
    serializer = PageSerializer(pages, many=True)
    return JsonResponse({'pages' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


def page(request, id):
    page = Pages.objects.get(status = 1, id = id)
    serializer = PageSerializer(page, many=False)
    return JsonResponse({'page' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
