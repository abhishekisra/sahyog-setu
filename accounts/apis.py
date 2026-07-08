import datetime
import json
import random
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from .models import User



@csrf_exempt
def user(request):
    request_data = json.loads(request.body)
    try:
        user = User.objects.get(client_id = request_data['client_id'], user_type = 2)
    except User.DoesNotExist:
        user = User()
        username = ''.join((random.choice('1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(6)))
        user.username = 'user-' + username
    
    user.user_type = 2
    user.name = request_data['name']
    user.email = request_data['email']
    user.client_id = request_data['client_id']
    user.profile_pic = request_data['profile_pic']
    user.save()
    return JsonResponse({'message' : "User added.", 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
