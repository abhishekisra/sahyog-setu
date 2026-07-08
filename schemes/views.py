from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from occupations.models import Occupations
from states.models import States
from .models import Categories, Scheme_Occupations, Schemes, Scheme_Areas, Scheme_Employements



# Create your views here.

class CategoriesView(View):

    def get(self, request):
        if request.user.is_authenticated:
            categories = Categories.objects.all()
            return render(request, 'custom_admin/manage-schemes/categories.html', {'categories': categories})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')

        
    def post(self, request):
        if request.user.is_authenticated:
            category =  Categories()
            category.title = request.POST.get('title')
            category.status = int(request.POST.get('status'))
            if request.FILES:
                category.image = request.FILES['image']
                category.banner = request.FILES['banner']
                category.save()
                messages.success(request, "Category added sucessfully")
                return redirect('adminSchemeCategories')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminCategories')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteCategory(request):
    if request.user.is_authenticated:
        category_id = request.POST.get('id')
        category = Categories.objects.get(id = category_id) 
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect('adminSchemeCategories')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateCategory(request, id):
    if request.user.is_authenticated:
        category = Categories.objects.get(id = id) 
        if 'image' in request.FILES:
            category.image = request.FILES['image']
        if 'banner' in request.FILES:
            category.banner = request.FILES['banner']
        category.title = request.POST.get('title')
        category.status = int(request.POST.get('status'))
        category.save()
        messages.success(request, "Category updated successfully.")
        return redirect('adminSchemeCategories')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')





# Create your views here.

class SchemesView(View):
    def get(self, request):
        if request.user.is_authenticated:
            schemes = Schemes.objects.all()
            return render(request, "custom_admin/manage-schemes/schemes/schemes.html", {'schemes': schemes})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class SchemeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            occupations = Occupations.objects.all()
            categories = Categories.objects.all()
            states = States.objects.all()
            return render(request, "custom_admin/manage-schemes/schemes/new-scheme.html", {'occupations': occupations, 'categories' : categories, 'states' : states})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                if request.FILES:
                    scheme = Schemes()
                    scheme.title = request.POST.get('title')
                    scheme.banner = request.FILES['banner']
                    scheme.category_id = request.POST.get('category_id')
                    scheme.scheme_type = request.POST.get('scheme_type')
                    scheme.state_id = request.POST.get('state')
                    scheme.dbt = request.POST.get('dbt')
                    scheme.business_related = request.POST.get('business_related')
                    scheme.status = request.POST.get('status')
                    scheme.divyang = request.POST.get('divyang')
                    
                    scheme.description = request.POST.get('description')
                    scheme.eligibility = request.POST.get('eligibility')
                    scheme.required_documents = request.POST.get('required_documents')
                    scheme.web_links = request.POST.get('web_links')
                    scheme.age_max = request.POST.get('age_max')
                    scheme.age_min = request.POST.get('age_min')
                    scheme.income_max = request.POST.get('income_max')
                    scheme.income_min = request.POST.get('income_min')
                    scheme.mode_of_application = request.POST.get('mode_of_application')

                    scheme.castes = ','.join(request.POST.getlist('caste'))
                    scheme.scheme_for = ','.join(request.POST.getlist('scheme_for'))
                    scheme.benificiaries = ','.join(request.POST.getlist('benificiaries'))
                    scheme.marital_status = ','.join(request.POST.getlist('marital_status'))
                    scheme.religions = ','.join(request.POST.getlist('religions'))
                    scheme.save()

                    if scheme.id:
                        Scheme_Occupations.objects.bulk_create([
                            Scheme_Occupations(scheme_id = scheme.id, occupation_id = occupation) for occupation in request.POST.getlist('occupations')
                        ])

                        Scheme_Areas.objects.bulk_create([
                            Scheme_Areas(scheme_id = scheme.id, area = area) for area in request.POST.getlist('areas')
                        ])

                        Scheme_Employements.objects.bulk_create([
                            Scheme_Employements(scheme_id = scheme.id, employment = employment) for employment in request.POST.getlist('employments')
                        ])

                    messages.success(request, "Scheme saved successfully.")
                    return redirect('adminSchemes')
                else:
                    messages.error(request, "Image is required.")
                    return redirect('adminNewScheme')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditSchemeView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                occupations = Occupations.objects.all()
                categories = Categories.objects.all()
                states = States.objects.all()
                scheme = Schemes.objects.get(id = id)
                scheme_occupations = list(Scheme_Occupations.objects.filter(scheme_id = id).values_list('occupation_id', flat=True))
                scheme_occupations = ','.join(map(str, scheme_occupations))
                employments = list(Scheme_Employements.objects.filter(scheme_id = id).values_list('employment', flat=True))
                employments = ','.join(map(str, employments))
                areas = list(Scheme_Areas.objects.filter(scheme_id = id).values_list('area', flat=True))
                areas = ','.join(map(str, areas))
                return render(request, "custom_admin/manage-schemes/schemes/edit-scheme.html", {'occupations': occupations, 'categories' : categories, 'states' : states, 'scheme' : scheme, 'scheme_occupations' : scheme_occupations, "employments" : employments, "areas" : areas})
            except Schemes.DoesNotExist:
                messages.error(request, "Schemes doesn't exists.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                scheme = Schemes.objects.get(id = id)
                scheme.title = request.POST.get('title')
                scheme.category_id = request.POST.get('category_id')
                scheme.scheme_type = request.POST.get('scheme_type')
                scheme.state_id = request.POST.get('state')
                scheme.business_related = request.POST.get('business_related')
                scheme.dbt = request.POST.get('dbt')
                scheme.status = request.POST.get('status')
                scheme.divyang = request.POST.get('divyang')
                
                scheme.description = request.POST.get('description')
                scheme.eligibility = request.POST.get('eligibility')
                scheme.required_documents = request.POST.get('required_documents')
                scheme.web_links = request.POST.get('web_links')
                scheme.age_max = request.POST.get('age_max')
                scheme.age_min = request.POST.get('age_min')
                scheme.income_max = request.POST.get('income_max')
                scheme.income_min = request.POST.get('income_min')
                scheme.mode_of_application = request.POST.get('mode_of_application')

                scheme.castes = ','.join(request.POST.getlist('caste'))
                scheme.scheme_for = ','.join(request.POST.getlist('scheme_for'))
                scheme.benificiaries = ','.join(request.POST.getlist('benificiaries'))
                scheme.marital_status = ','.join(request.POST.getlist('marital_status'))
                scheme.religions = ','.join(request.POST.getlist('religions'))

                if 'banner' in request.FILES:
                    scheme.banner = request.FILES['banner']
                scheme.save()

                if scheme.id:
                    Scheme_Occupations.objects.filter(scheme_id = id).delete()
                    Scheme_Areas.objects.filter(scheme_id = id).delete()
                    Scheme_Employements.objects.filter(scheme_id = id).delete()
                    Scheme_Occupations.objects.bulk_create([
                        Scheme_Occupations(scheme_id = scheme.id, occupation_id = occupation) for occupation in request.POST.getlist('occupations')
                    ])
                    
                    Scheme_Areas.objects.bulk_create([
                        Scheme_Areas(scheme_id = scheme.id, area = area) for area in request.POST.getlist('areas')
                    ])

                    Scheme_Employements.objects.bulk_create([
                        Scheme_Employements(scheme_id = scheme.id, employment = employment) for employment in request.POST.getlist('employments')
                    ])

                messages.success(request, "Scheme saved successfully.")
                return redirect('adminSchemes')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteScheme(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        scheme = Schemes.objects.get(id = id) 
        scheme.delete()
        messages.success(request, "Scheme deleted successfully.")
        return redirect('adminSchemes')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


