import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import TestimonialSerializer
from .models import Testimonials



def testimonials(request):
    testimonials = Testimonials.objects.filter(status = 1)
    serializer = TestimonialSerializer(testimonials, many=True)
    return JsonResponse({'testimonials' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)


