import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import BusinessPlanSerializer
from .models import Business_Plans



def businessPlans(request):
    business_plans = Business_Plans.objects.filter(status = 1)
    serializer = BusinessPlanSerializer(business_plans, many=True)
    return JsonResponse({'business_plans' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
