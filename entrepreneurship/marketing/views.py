from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

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


def marketing_finder(request):
    """Public, no login -- Marketing resources in the Scheme Viewer's own
    style, "direct" mode: no description field at all, just image + title
    + link + the row's own accent color -- a card click opens the link
    straight in a new tab, no detail overlay."""
    total = Marketing.objects.filter(status=1).count()
    return render(request, "custom_admin/entrepreneurship/marketing_finder.html", {
        "total_marketing": total,
    })


@csrf_exempt
def marketing_search_light(request):
    """Paginated search -- same reasoning as sibling *_search_light views."""
    PAGE_SIZE = 8
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    items = Marketing.objects.filter(status=1)
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
            "link": r.link,
            "color": r.color,
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })


