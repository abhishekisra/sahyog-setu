import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import ImportantDocumentSerializer
from .models import Important_Documents



def importantDocuments(request):
    important_documents = Important_Documents.objects.filter(status = 1)
    serializer = ImportantDocumentSerializer(important_documents, many=True)
    return JsonResponse({'important_documents' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def importantDocument(request, id):
    try:
        important_document = Important_Documents.objects.get(status = 1, id = id)
        serializer = ImportantDocumentSerializer(important_document, many=False)
        return JsonResponse({'important_document' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)