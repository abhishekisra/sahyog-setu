from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Helplines


# Create your views here.

class HelplinesView(View):

    def get(self, request):
        if request.user.is_authenticated:
            helplines = Helplines.objects.all()
            return render(request, 'custom_admin/helplines.html', {'helplines': helplines})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')

        
    def post(self, request):
        if request.user.is_authenticated:
            helpline =  Helplines()
            helpline.link = request.POST.get('link')
            helpline.status = int(request.POST.get('status'))
            helpline.title = request.POST.get('title')
            helpline.color = request.POST.get('color')
            if request.FILES:
                helpline.image = request.FILES['image']
                helpline.save()
                messages.success(request, "Category added sucessfully")
                return redirect('adminHelplines')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminHelplines')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteHelpline(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        helpline = Helplines.objects.get(id = id) 
        helpline.delete()
        messages.success(request, "Helpline deleted successfully.")
        return redirect('adminHelplines')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateHelpline(request, id):
    if request.user.is_authenticated:
        helpline = Helplines.objects.get(id = id) 
        if request.FILES:
            helpline.image = request.FILES['image']
        helpline.link = request.POST.get('link')
        helpline.status = int(request.POST.get('status'))
        helpline.title = request.POST.get('title')
        helpline.color = request.POST.get('color')
        helpline.save()
        messages.success(request, "Helpline updated successfully.")
        return redirect('adminHelplines')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


