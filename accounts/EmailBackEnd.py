from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.backends import get_user_model
from django.db.models import Q
from .models import User

class EmailBackEnd(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(Q(Q(mobile=username) | Q(email = username))  & Q(Q(user_type = 2) | Q(user_type = 1)))
            if user.check_password(password):
                print(user)
                return user
            else:
                return None
        except UserModel.DoesNotExist as e:
            print(e)
            return None
