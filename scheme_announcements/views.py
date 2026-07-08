from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Scheme_Announcements


# Create your views here.

class SchemeAnnouncementsView(View):

    def get(self, request):
        if request.user.is_authenticated:
            scheme_announcements = Scheme_Announcements.objects.all()
            return render(request, 'custom_admin/scheme-announcements.html', {'scheme_announcements': scheme_announcements})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminSchemeAnnouncements')

        
    def post(self, request):
        if request.user.is_authenticated:
            scheme_announcement =  Scheme_Announcements()
            scheme_announcement.link = request.POST.get('link')
            scheme_announcement.status = int(request.POST.get('status'))
            scheme_announcement.title = request.POST.get('title')
            if request.FILES:
                scheme_announcement.image = request.FILES['image']
                scheme_announcement.save()
                messages.success(request, "Scheme announcement added sucessfully")
                return redirect('adminSchemeAnnouncements')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminSchemeAnnouncements')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteSchemeAnnouncement(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        scheme_announcement = Scheme_Announcements.objects.get(id = id) 
        scheme_announcement.delete()
        messages.success(request, "Scheme announcement deleted successfully.")
        return redirect('adminSchemeAnnouncements')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateSchemeAnnouncement(request, id):
    if request.user.is_authenticated:
        scheme_announcement = Scheme_Announcements.objects.get(id = id) 
        if request.FILES:
            scheme_announcement.image = request.FILES['image']
        scheme_announcement.status = int(request.POST.get('status'))
        scheme_announcement.title = request.POST.get('title')
        scheme_announcement.link = request.POST.get('link')
        scheme_announcement.save()
        messages.success(request, "Scheme announcement updated successfully.")
        return redirect('adminSchemeAnnouncements')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


