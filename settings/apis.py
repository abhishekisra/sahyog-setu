import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from accounts.models import User
from .models import Settings

def info(request):
    users = len(User.objects.all())
    info_settings = Settings.objects.all()
    last_updated =""
    if info_settings[1].info:
        users = users + int(info_settings[1].info)

    if info_settings[0].info:
        last_updated = info_settings[0].info
    return JsonResponse({'visitors' : users, 'last_updated' : last_updated, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)