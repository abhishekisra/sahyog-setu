
import random
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from accounts.EmailBackEnd import EmailBackEnd
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from accounts.models import User
from django.template.loader import render_to_string 
from django.utils.html import strip_tags 
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.decorators import method_decorator
from django.db.models import Exists, OuterRef, Sum, Q, F, Subquery, Case, When, Value, FloatField, CharField

from occupations.models import Occupations
from schemes.models import Categories, Schemes
from important_documents.models import Important_Documents
from important_portals.models import Important_Portals
from scheme_announcements.models import Scheme_Announcements
from testimonials.models import Testimonials

from entrepreneurship.artificial_intelligence.models import Artificial_Intelligence
from entrepreneurship.business_plans.models import Business_Plans
from entrepreneurship.legal_registrations.models import Legal_Registrations
from entrepreneurship.marketing.models import Marketing
from entrepreneurship.organization_registrations.models import Organization_Registration
from helplines.models import Helplines

@method_decorator(csrf_exempt, name='post')
class LoginView(View):
    def get(self, request):
         return render(request, 'custom_admin/login.html')


    def post(self, request):
        emailId = request.POST['emailId']
        password = request.POST['password']
        user = EmailBackEnd().authenticate(request, username = emailId, password =password)
        if user is not None:
            if user.user_type == 1:
                login(request, user)
                return redirect('adminDashboard')
            else:
                return render(request, 'custom_admin/login.html', {'error' : "Invalid email Id or password"})
        else:
            return render(request, 'custom_admin/login.html', {'error' : "Invalid email Id or password"})




def dashboard(request):
    occupations = len(Occupations.objects.all())
    categories = len(Categories.objects.all())
    state_schemes = len(Schemes.objects.filter(scheme_type = 1))
    central_schemes = len(Schemes.objects.filter(scheme_type = 0))
    important_documents = len(Important_Documents.objects.all())
    important_portals = len(Important_Portals.objects.all())
    scheme_announcements = len(Scheme_Announcements.objects.all())
    testimonials = len(Testimonials.objects.all())
    visitors = len(User.objects.filter(user_type = 2))
    artificial_intelligence = len(Artificial_Intelligence.objects.all())
    business_plans = len(Business_Plans.objects.all())
    legal_registrations = len(Legal_Registrations.objects.all())
    marketing = len(Marketing.objects.all())
    organization_registration = len(Organization_Registration.objects.all())
    helplines = len(Helplines.objects.all())
    return render(request, 'custom_admin/dashboard.html', {'organization_registration' : organization_registration, 'marketing' : marketing, 'legal_registrations': legal_registrations, 'business_plans' : business_plans, 'artificial_intelligence' : artificial_intelligence, 'occupations' : occupations, 'categories' : categories, 'state_schemes' : state_schemes, 'central_schemes' : central_schemes, 'important_documents' : important_documents, 'important_portals' : important_portals, 'scheme_announcements' : scheme_announcements, 'testimonials' : testimonials, 'visitors' : visitors, 'helplines' : helplines})





def resetPassword(request):
    return render(request, 'custom_admin/reset-password/reset_password.html')



    
@csrf_exempt
def requestOtp(request):
    try:     
        user = User.objects.get(email = request.POST.get('email')  )        
        otp = ''.join((random.choice('1234567890') for i in range(4)))
        request.session['otp'] = otp
        request.session['user_id'] = user.id  
        subject = "Try On Trends OTP request"
        to_email = [user.email]
        html_template = render_to_string("custom_admin/reset-password/otp-template.html", {'logo' : settings.LOGO_URL, 'name' : user.name,  'otp' : otp})    
        text_content = strip_tags(html_template)  
        email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, to_email)
        email.attach_alternative(html_template, "text/html")
        email.send()
        return JsonResponse({'message' : "OTP sent to registered Email", 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return JsonResponse({'message' : "OTP unable to sent.", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse({'message' : "Something went wrong. Please try again later.", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
def verifyOtp(request):     
    otp = request.POST.get('otp')
    if(otp == request.session['otp']):
        return JsonResponse({'message' : "OTP Matched", 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    else:
        return JsonResponse({'message' : "OTP Not Matched", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)

        
@csrf_exempt
def changePassword(request):
    try:
        password = request.POST.get('password')
        user = User.objects.get(id = request.session['user_id'])
        user.set_password(password)
        user.save()
        return JsonResponse({'message':"password changed succesfully", 'status':status.HTTP_200_OK}, safe=False, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return JsonResponse({'message':"User does't exist", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        return JsonResponse({'message':"Something went wrong. Please try again later.", 'status':status.HTTP_400_BAD_REQUEST}, safe=False, status=status.HTTP_400_BAD_REQUEST)
    
  

class LogoutView(View):

    def get(self, request):
        logout(request)
        return redirect('adminLogin')