import re
from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Helplines


# Create your views here.

def helpline_finder(request):
    """Public, no login -- replaces the old SPA's /helplines page (plain
    blue gradient cards with the toll-free number baked into a design
    graphic, no separate text). Same *_finder.html card look as Important
    Portals -- number now real text (Helplines.number, backfilled from the
    16 existing graphics), with a tel: Call Now action plus a secondary
    "More Info" link when `link` is a real URL rather than a bare number."""
    helplines = list(Helplines.objects.filter(status=1).order_by('title'))
    for h in helplines:
        # tel: only wants digits -- "100/112" etc. use the first number.
        digits = re.split(r'[^0-9]+', h.number or '')
        h.tel_number = next((d for d in digits if d), '')
        h.is_url = (h.link or '').startswith('http')
    return render(request, "custom_admin/helplines/helpline_finder.html", {
        "helplines": helplines,
    })

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
            helpline.number = request.POST.get('number', '')
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
        helpline.number = request.POST.get('number', '')
        helpline.save()
        messages.success(request, "Helpline updated successfully.")
        return redirect('adminHelplines')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


