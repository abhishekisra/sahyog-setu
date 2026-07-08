import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import SchemeAnnouncementSerializer
from .models import Scheme_Announcements



def schemeAnnouncements(request):
    scheme_announcements = Scheme_Announcements.objects.filter(status = 1)
    serializer = SchemeAnnouncementSerializer(scheme_announcements, many=True)
    return JsonResponse({'scheme_announcements' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
