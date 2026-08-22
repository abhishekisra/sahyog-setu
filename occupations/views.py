from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import Occupations, OccupationTranslation
from custom_admin.translation_views import TranslationsPickerView, EditTranslationView

# Create your views here.

class OccupationsView(View):

    def get(self, request):
        if request.user.is_authenticated:
            occupations = Occupations.objects.all()
            return render(request, 'custom_admin/occupations.html', {'occupations': occupations})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            occupation =  Occupations()
            occupation.title = request.POST.get('title')
            occupation.status = int(request.POST.get('status'))
            occupation.save()
            messages.success(request, "Occupation added sucessfully")
            return redirect('adminOccupations')
        else:
             messages.error("you have to login first.")
             return redirect('adminLogin')



        
def deleteOccupation(request):
    if request.user.is_authenticated:
        occupation_id = request.POST.get('occupation_id')
        occupation = Occupations.objects.get(id = occupation_id) 
        occupation.delete()
        messages.success(request, "Occupation deleted successfully.")
        return redirect('adminOccupations')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateOccupation(request, id):
    if request.user.is_authenticated:
        occupation = Occupations.objects.get(id = id)
        occupation.title = request.POST.get('title')
        occupation.status = int(request.POST.get('status'))
        occupation.save()
        messages.success(request, "Occupation updated successfully.")
        return redirect('adminOccupations')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


class OccupationTranslationsView(TranslationsPickerView):
    model = Occupations
    translation_model = OccupationTranslation
    fk_name = "occupation"
    fields = ["title"]
    list_url_name = "adminOccupations"
    list_label = "Occupations"
    edit_url_name = "adminOccupationEditTranslation"


class OccupationEditTranslationView(EditTranslationView):
    model = Occupations
    translation_model = OccupationTranslation
    fk_name = "occupation"
    fields = [("title", "Title", "text")]
    picker_url_name = "adminOccupationTranslations"

