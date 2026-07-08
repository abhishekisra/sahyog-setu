from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Business_Plans


# Create your views here.

class BusinessPlansView(View):

    def get(self, request):
        if request.user.is_authenticated:
            business_plans = Business_Plans.objects.all()
            return render(request, 'custom_admin/entrepreneurship/business-plans/business-plans.html', {'business_plans': business_plans})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminBusinessPlans')

        
    def post(self, request):
        if request.user.is_authenticated:
            business_plan =  Business_Plans()
            business_plan.pdf = request.FILES['pdf']
            business_plan.status = int(request.POST.get('status'))
            business_plan.title = request.POST.get('title')
            business_plan.image = request.FILES['image']
            business_plan.save()
            messages.success(request, "Business Plan added sucessfully")
            return redirect('adminBusinessPlans')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteBusinessPlan(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        business_plan = Business_Plans.objects.get(id = id) 
        business_plan.delete()
        messages.success(request, "Business plan deleted successfully.")
        return redirect('adminBusinessPlans')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateBusinessPlan(request, id):
    if request.user.is_authenticated:
        business_plan = Business_Plans.objects.get(id = id) 
        if 'image' in request.FILES:
            business_plan.image = request.FILES['image']
        if 'pdf' in request.FILES:
            business_plan.pdf = request.FILES['pdf']
        business_plan.status = int(request.POST.get('status'))
        business_plan.title = request.POST.get('title')
        business_plan.save()
        messages.success(request, "Business pplan updated successfully.")
        return redirect('adminBusinessPlans')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


