import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .serializers import ImportantDocumentSerializer
from .models import Important_Documents
from languages.utils import clean_language



def importantDocuments(request):
    important_documents = Important_Documents.objects.filter(status = 1)
    serializer = ImportantDocumentSerializer(important_documents, many=True)
    return JsonResponse({'important_documents' : serializer.data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)



def importantDocument(request, id):
    # Optional ?lang= -- absent (the untouched legacy SPA never sends it)
    # gives byte-identical output to before.
    try:
        important_document = Important_Documents.objects.get(status = 1, id = id)
        serializer = ImportantDocumentSerializer(important_document, many=False)
        data = dict(serializer.data)
        lang = clean_language(request.GET.get('lang', 'en'))
        if lang != 'en':
            data['title'] = important_document.field_for('title', lang)
            data['description'] = important_document.field_for('description', lang)
            data['eligibility'] = important_document.field_for('eligibility', lang)
            data['required_documents'] = important_document.field_for('required_documents', lang)
            data['mode_of_application'] = important_document.field_for('mode_of_application', lang)
        return JsonResponse({'important_document' : data, 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'message' : "Invalid scheme id", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)