from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Scheme_Announcements


# Create your views here.

class SchemeAnnouncementsView(View):

    def get(self, request):
        if request.user.is_authenticated:
            scheme_announcements = Scheme_Announcements.objects.all()
            return render(request, 'custom_admin/scheme-announcements.html', {'scheme_announcements': scheme_announcements})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminSchemeAnnouncements')

        
    def post(self, request):
        if request.user.is_authenticated:
            scheme_announcement =  Scheme_Announcements()
            scheme_announcement.link = request.POST.get('link')
            scheme_announcement.status = int(request.POST.get('status'))
            scheme_announcement.title = request.POST.get('title')
            if request.FILES:
                scheme_announcement.image = request.FILES['image']
                scheme_announcement.save()
                messages.success(request, "Scheme announcement added sucessfully")
                return redirect('adminSchemeAnnouncements')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminSchemeAnnouncements')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        
def deleteSchemeAnnouncement(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        scheme_announcement = Scheme_Announcements.objects.get(id = id) 
        scheme_announcement.delete()
        messages.success(request, "Scheme announcement deleted successfully.")
        return redirect('adminSchemeAnnouncements')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateSchemeAnnouncement(request, id):
    if request.user.is_authenticated:
        scheme_announcement = Scheme_Announcements.objects.get(id = id) 
        if request.FILES:
            scheme_announcement.image = request.FILES['image']
        scheme_announcement.status = int(request.POST.get('status'))
        scheme_announcement.title = request.POST.get('title')
        scheme_announcement.link = request.POST.get('link')
        scheme_announcement.save()
        messages.success(request, "Scheme announcement updated successfully.")
        return redirect('adminSchemeAnnouncements')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def scheme_announcement_finder(request):
    """Public, no login -- Scheme Announcements in the Scheme Viewer's own
    style, "direct" mode: no description field at all, just image + title +
    link -- a card click opens the link straight in a new tab, no detail
    overlay (same shape/treatment as Marketing/Artificial Intelligence,
    minus their accent color field)."""
    total = Scheme_Announcements.objects.filter(status=1).count()
    return render(request, "custom_admin/scheme_announcement_finder.html", {
        "total_scheme_announcements": total,
    })


@csrf_exempt
def scheme_announcement_search_light(request):
    """Paginated search -- same reasoning as sibling *_search_light views."""
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    items = Scheme_Announcements.objects.filter(status=1)
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
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })


