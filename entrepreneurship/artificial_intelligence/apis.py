import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import ArtificialIntelligenceSerializer
from .models import Artificial_Intelligence



def artificialIntelligence(request):
    artificial_intelligence = Artificial_Intelligence.objects.filter(status = 1)
    serializer = ArtificialIntelligenceSerializer(artificial_intelligence, many=True)
    return JsonResponse({'artificial_intelligence' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
