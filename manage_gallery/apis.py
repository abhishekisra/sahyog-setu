import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import ImageSerializer, VideoSerializer
from .models import Images, Videoes



def gallery(request):
    images = list(Images.objects.filter(status = 1).values_list('image', flat=True))
    videoes = Videoes.objects.filter(status = 1)
    video_serializer = VideoSerializer(videoes, many=True)
    return JsonResponse({'images' : images, 'videoes' : video_serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)

