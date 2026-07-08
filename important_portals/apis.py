import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import ImportantPortalSerializer
from .models import Important_Portals



def importantPortals(request):
    important_portals = Important_Portals.objects.filter(status = 1)
    serializer = ImportantPortalSerializer(important_portals, many=True)
    return JsonResponse({'important_portals' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def importantPortal(request, id):
    try:
        important_portal = Important_Portals.objects.get(status = 1, id = id)
        serializer = ImportantPortalSerializer(important_portal, many=False)
        return JsonResponse({'important_portal' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)