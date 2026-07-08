from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Artificial_Intelligence


# Create your views here.

class ArtificialIntelligenceView(View):

    def get(self, request):
        if request.user.is_authenticated:
            artificial_intelligence = Artificial_Intelligence.objects.all()
            return render(request, 'custom_admin/entrepreneurship/artificial-intelligence/artificial-intelligence.html', {'artificial_intelligence': artificial_intelligence})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')

        
    def post(self, request):
        if request.user.is_authenticated:
            artificial_intelligence =  Artificial_Intelligence()
            artificial_intelligence.link = request.POST.get('link')
            artificial_intelligence.status = int(request.POST.get('status'))
            artificial_intelligence.title = request.POST.get('title')
            artificial_intelligence.color = request.POST.get('color')
            if request.FILES:
                artificial_intelligence.image = request.FILES['image']
                artificial_intelligence.save()
                messages.success(request, "Artificial intelligence added sucessfully")
                return redirect('adminArtificialIntelligence')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminArtificialIntelligence')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteArtificialIntelligence(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        artificial_intelligence = Artificial_Intelligence.objects.get(id = id) 
        artificial_intelligence.delete()
        messages.success(request, "Artificial intelligence deleted successfully.")
        return redirect('adminArtificialIntelligence')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateArtificialIntelligence(request, id):
    if request.user.is_authenticated:
        artificial_intelligence = Artificial_Intelligence.objects.get(id = id) 
        if request.FILES:
            artificial_intelligence.image = request.FILES['image']
        artificial_intelligence.link = request.POST.get('link')
        artificial_intelligence.status = int(request.POST.get('status'))
        artificial_intelligence.title = request.POST.get('title')
        artificial_intelligence.color = request.POST.get('color')
        artificial_intelligence.save()
        messages.success(request, "Artificial intelligence updated successfully.")
        return redirect('adminArtificialIntelligence')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


