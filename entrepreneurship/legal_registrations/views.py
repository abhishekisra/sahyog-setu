from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Legal_Registrations



class LegalRegistrationsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            legal_registrations = Legal_Registrations.objects.all()
            return render(request, "custom_admin/entrepreneurship/legal-registrations/legal-registrations.html", {'legal_registrations': legal_registrations})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class LegalRegistrationView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/entrepreneurship/legal-registrations/new-legal-registration.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                legal_registration = Legal_Registrations()
                legal_registration.title = request.POST.get('title')
                legal_registration.image = request.FILES['image']
                legal_registration.banner = request.FILES['banner']
                legal_registration.status = request.POST.get('status')
               
                legal_registration.description = request.POST.get('description')
                legal_registration.eligibility = request.POST.get('eligibility')
                legal_registration.required_documents = request.POST.get('required_documents')
                legal_registration.web_links = request.POST.get('web_links')
                legal_registration.mode_of_application = request.POST.get('mode_of_application')

                
                legal_registration.save()

                messages.success(request, "Legal RFegistration saved successfully.")
                return redirect('adminLegalRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminLegalRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditLegalRegistrationView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                legal_registration = Legal_Registrations.objects.get(id = id)
                return render(request, "custom_admin/entrepreneurship/legal-registrations/edit-legal-registration.html", {"legal_registration" : legal_registration})
            except Legal_Registrations.DoesNotExist:
                messages.error(request, "Legal reigistration doesn't exists.")
                return redirect('adminImportantDocuments')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                legal_registration = Legal_Registrations.objects.get(id = id)
                legal_registration.title = request.POST.get('title')
                if 'image' in request.FILES:
                    legal_registration.image = request.FILES['image']
                
                if 'banner' in request.FILES:
                    legal_registration.banner = request.FILES['banner']
               
                legal_registration.status = request.POST.get('status')
                
                legal_registration.description = request.POST.get('description')
                legal_registration.eligibility = request.POST.get('eligibility')
                legal_registration.required_documents = request.POST.get('required_documents')
                legal_registration.web_links = request.POST.get('web_links')
                legal_registration.mode_of_application = request.POST.get('mode_of_application')

                legal_registration.save()

                messages.success(request, "Important document saved successfully.")
                return redirect('adminLegalRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminLegalRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteLegalRegistration(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        legal_registration = Legal_Registrations.objects.get(id = id) 
        legal_registration.delete()
        messages.success(request, "Legal registration deleted successfully.")
        return redirect('adminLegalRegistrations')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        