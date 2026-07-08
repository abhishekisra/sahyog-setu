from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import Settings

# Create your views here.

class SettingsView(View):

    def get(self, request):
        if request.user.is_authenticated:
            settings = Settings.objects.all()
            return render(request, 'custom_admin/settings.html', {'settings': settings})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')
        

        


def updateSettings(request, id):
    if request.user.is_authenticated:
        setting = Settings.objects.get(id = id) 
        setting.info = request.POST.get('info')
        setting.save()
        messages.success(request, "News updated successfully.")
        return redirect('adminSettings')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')

