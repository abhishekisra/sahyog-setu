from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    use_in_migrations = True


    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is require')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  
        user.save()  
        return user  

    
    def create_superuser(self, email, password, **extra_fields):  
        """  
        Create and save a SuperUser with the given email and password.  
        """  
        extra_fields.setdefault('user_type', 1)  
        extra_fields.setdefault('is_superuser', 1)  
        extra_fields.setdefault('is_active', 1)  
  
        if extra_fields.get('is_superuser') is not True:  
            raise ValueError(('Superuser must have is_superuser=True.'))  
        return self.create_user(email, password, **extra_fields)