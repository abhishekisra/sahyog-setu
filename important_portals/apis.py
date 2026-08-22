import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import ImportantPortalSerializer
from .models import Important_Portals
from languages.utils import clean_language



def importantPortals(request):
    important_portals = Important_Portals.objects.filter(status = 1)
    serializer = ImportantPortalSerializer(important_portals, many=True)
    return JsonResponse({'important_portals' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def importantPortal(request, id):
    # Optional ?lang= -- absent (the untouched legacy SPA never sends it)
    # gives byte-identical output to before; only overwrites the
    # translatable fields when a real translation exists.
    try:
        important_portal = Important_Portals.objects.get(status = 1, id = id)
        serializer = ImportantPortalSerializer(important_portal, many=False)
        data = dict(serializer.data)
        lang = clean_language(request.GET.get('lang', 'en'))
        if lang != 'en':
            data['title'] = important_portal.field_for('title', lang)
            data['description'] = important_portal.field_for('description', lang)
            data['mode_of_application'] = important_portal.field_for('mode_of_application', lang)
        return JsonResponse({'important_portal' : data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)