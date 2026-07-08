from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Marketing


# Create your views here.

class MarketingView(View):

    def get(self, request):
        if request.user.is_authenticated:
            marketing = Marketing.objects.all()
            return render(request, 'custom_admin/entrepreneurship/marketing/marketing.html', {'marketing': marketing})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')

        
    def post(self, request):
        if request.user.is_authenticated:
            marketing =  Marketing()
            marketing.link = request.POST.get('link')
            marketing.status = int(request.POST.get('status'))
            marketing.title = request.POST.get('title')
            marketing.color = request.POST.get('color')
            if request.FILES:
                marketing.image = request.FILES['image']
                marketing.save()
                messages.success(request, "Marketing added sucessfully")
                return redirect('adminMarketing')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminMarketing')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteMarketing(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        marketing = Marketing.objects.get(id = id) 
        marketing.delete()
        messages.success(request, "Marketing deleted successfully.")
        return redirect('adminMarketing')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateMarketing(request, id):
    if request.user.is_authenticated:
        marketing = Marketing.objects.get(id = id) 
        if request.FILES:
            marketing.image = request.FILES['image']
        marketing.link = request.POST.get('link')
        marketing.status = int(request.POST.get('status'))
        marketing.title = request.POST.get('title')
        marketing.color = request.POST.get('color')
        marketing.save()
        messages.success(request, "Marketing updated successfully.")
        return redirect('adminMarketing')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


