from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

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


def business_plan_finder(request):
    """Public, no login -- Business Plans in the Scheme Viewer's own style,
    but "direct" mode: this model has no description at all (just image +
    title + pdf), so a card click opens the PDF straight in a new tab --
    no detail overlay."""
    total = Business_Plans.objects.filter(status=1).count()
    return render(request, "custom_admin/entrepreneurship/business_plan_finder.html", {
        "total_business_plans": total,
    })


@csrf_exempt
def business_plan_search_light(request):
    """Paginated search -- same reasoning as sibling *_search_light views,
    even though this model's dataset is small: keeps the search/pagination
    behaviour consistent across all "*_finder.html" pages."""
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    items = Business_Plans.objects.filter(status=1)
    if body.get("searched_text"):
        items = items.filter(title__icontains=body["searched_text"])
    items = items.order_by("-id")

    total = items.count()
    page = max(1, int(body.get("page") or 1))
    paginator = Paginator(items, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for r in page_obj.object_list:
        results.append({
            "id": r.id,
            "title": r.title,
            "image": r.image.url if r.image else "",
            "pdf": r.pdf.url if r.pdf else "",
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })


