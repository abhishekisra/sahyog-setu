from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

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


def artificial_intelligence_finder(request):
    """Public, no login -- Artificial Intelligence tools in the Scheme
    Viewer's own style, "direct" mode: no description field at all, just
    image + title + link + the row's own accent color -- a card click
    opens the link straight in a new tab, no detail overlay."""
    total = Artificial_Intelligence.objects.filter(status=1).count()
    return render(request, "custom_admin/entrepreneurship/artificial_intelligence_finder.html", {
        "total_artificial_intelligence": total,
    })


@csrf_exempt
def artificial_intelligence_search_light(request):
    """Paginated search -- same reasoning as sibling *_search_light views."""
    PAGE_SIZE = 8
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    items = Artificial_Intelligence.objects.filter(status=1)
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


