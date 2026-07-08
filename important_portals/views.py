from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import Important_Portals




class ImportantPortalsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            important_portals = Important_Portals.objects.all()
            return render(request, "custom_admin/important-portals/important-portals.html", {'important_portals': important_portals})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class ImportantPortalView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/important-portals/new-important-portal.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                important_portal = Important_Portals()
                important_portal.title = request.POST.get('title')
                important_portal.status = request.POST.get('status')
                important_portal.description = request.POST.get('description')
                important_portal.image = request.FILES['image']
                important_portal.banner = request.FILES['banner']
                important_portal.mode_of_application = request.POST.get('mode_of_application')
                important_portal.save()
                messages.success(request, "Pmportant portal saved successfully.")
                return redirect('adminImportantPotals')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditImportantPortalView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                important_portal = Important_Portals.objects.get(id = id)
                return render(request, "custom_admin/important-portals/edit-important-portal.html", {'important_portal' : important_portal})
            except Important_Portals.DoesNotExist:
                messages.error(request, "Important Portal doesn't exists.")
                return redirect('adminImportantPotals')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                important_portal = Important_Portals.objects.get(id = id)
                important_portal.title = request.POST.get('title')
                important_portal.status = request.POST.get('status')
                important_portal.description = request.POST.get('description')
                important_portal.mode_of_application = request.POST.get('mode_of_application')
                if 'image' in request.FILES:
                    important_portal.image = request.FILES['image']
                if 'banner' in request.FILES:
                    important_portal.banner = request.FILES['banner']
                important_portal.save()
                messages.success(request, "Important portal saved successfully.")
                return redirect('adminImportantPotals')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminImportantPotals')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteImportantPortal(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        important_portal = Important_Portals.objects.get(id = id) 
        important_portal.delete()
        messages.success(request, "Important Portal deleted successfully.")
        return redirect('adminImportantPotals')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        