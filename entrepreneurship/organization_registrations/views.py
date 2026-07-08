from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import Organization_Registration




class OrganizationRegistrationsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            organization_registrations = Organization_Registration.objects.all()
            return render(request, "custom_admin/entrepreneurship/organization-registrations/organization-registrations.html", {'organization_registrations': organization_registrations})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class OrganizationRegistrationView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/entrepreneurship/organization-registrations/new-organization-registration.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                organization_registration = Organization_Registration()
                organization_registration.title = request.POST.get('title')
                organization_registration.status = request.POST.get('status')
                organization_registration.description = request.POST.get('description')
                organization_registration.image = request.FILES['image']
                organization_registration.banner = request.FILES['banner']
                organization_registration.mode_of_application = request.POST.get('mode_of_application')
                if 'pdf' in request.FILES:
                    organization_registration.pdf = request.FILES['pdf']
                organization_registration.save()
                messages.success(request, "Organization registration saved successfully.")
                return redirect('adminOrganizationRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminOrganizationRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditOrganizationRegistrationView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                organization_registration = Organization_Registration.objects.get(id = id)
                return render(request, "custom_admin/entrepreneurship/organization-registrations/edit-organization-registration.html", {'organization_registration' : organization_registration})
            except Organization_Registration.DoesNotExist:
                messages.error(request, "Organization registration doesn't exists.")
                return redirect('adminOrganizationRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                organization_registration = Organization_Registration.objects.get(id = id)
                organization_registration.title = request.POST.get('title')
                organization_registration.status = request.POST.get('status')
                organization_registration.description = request.POST.get('description')
                organization_registration.mode_of_application = request.POST.get('mode_of_application')
                if 'image' in request.FILES:
                    organization_registration.image = request.FILES['image']
                if 'banner' in request.FILES:
                    organization_registration.banner = request.FILES['banner']
                if 'pdf' in request.FILES:
                    organization_registration.pdf = request.FILES['pdf']
                organization_registration.save()
                messages.success(request, "Organization registration saved successfully.")
                return redirect('adminOrganizationRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminOrganizationRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteOrganizationRegistration(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        organization_registration = Organization_Registration.objects.get(id = id) 
        organization_registration.delete()
        messages.success(request, "Organization registration deleted successfully.")
        return redirect('adminOrganizationRegistrations')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        