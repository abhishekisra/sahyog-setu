from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import strip_tags
from django.utils.text import Truncator
import html as html_module
import json
from .models import Important_Portals




class ImportantPortalsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            important_portals = Important_Portals.objects.all()
            return render(request, "custom_admin/important-portals/important-portals.html", {'important_portals': important_portals})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class ImportantPortalView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/important-portals/new-important-portal.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                important_portal = Important_Portals()
                important_portal.title = request.POST.get('title')
                important_portal.status = request.POST.get('status')
                important_portal.description = request.POST.get('description')
                important_portal.image = request.FILES['image']
                important_portal.banner = request.FILES['banner']
                important_portal.mode_of_application = request.POST.get('mode_of_application')
                important_portal.save()
                messages.success(request, "Pmportant portal saved successfully.")
                return redirect('adminImportantPotals')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminSchemes')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditImportantPortalView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                important_portal = Important_Portals.objects.get(id = id)
                return render(request, "custom_admin/important-portals/edit-important-portal.html", {'important_portal' : important_portal})
            except Important_Portals.DoesNotExist:
                messages.error(request, "Important Portal doesn't exists.")
                return redirect('adminImportantPotals')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                important_portal = Important_Portals.objects.get(id = id)
                important_portal.title = request.POST.get('title')
                important_portal.status = request.POST.get('status')
                important_portal.description = request.POST.get('description')
                important_portal.mode_of_application = request.POST.get('mode_of_application')
                if 'image' in request.FILES:
                    important_portal.image = request.FILES['image']
                if 'banner' in request.FILES:
                    important_portal.banner = request.FILES['banner']
                important_portal.save()
                messages.success(request, "Important portal saved successfully.")
                return redirect('adminImportantPotals')
            except Exception as e:
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminImportantPotals')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteImportantPortal(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        important_portal = Important_Portals.objects.get(id = id) 
        important_portal.delete()
        messages.success(request, "Important Portal deleted successfully.")
        return redirect('adminImportantPotals')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        

def admin_portal_detail(request, id):
    """Admin-only (login required) preview JSON for the "View" button on
    the Important Portals list -- NOT the public /api/important-portal/
    <id>, which filters status=1 and so 400s on an inactive/draft portal
    an admin is specifically trying to check before activating it."""
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Login required"}, status=403)
    try:
        portal = Important_Portals.objects.get(id=id)
    except Important_Portals.DoesNotExist:
        return JsonResponse({"message": "Invalid id"}, status=404)
    return JsonResponse({"important_portal": {
        "title": portal.title,
        "description": portal.description,
    }})


def portal_finder(request):
    """Public, no login -- Important Portals in the Scheme Viewer's own
    style (filter-less: this model has no category/type field, so it's a
    search box + card grid + detail overlay, no sidebar). Mirrors
    schemes.views.scheme_finder -- this view just renders the shell and a
    real count for the hero stat; portal_search_light below does the
    actual paginated data fetch.

    ?portal=<id> renders real per-portal Open Graph/Twitter tags server-
    side (see schemes.views.scheme_finder for why this has to happen here
    rather than client-side)."""
    total_portals = Important_Portals.objects.filter(status=1).count()
    share_portal = None
    portal_id = request.GET.get('portal')
    if portal_id:
        share_portal = Important_Portals.objects.filter(status=1, id=portal_id).first()
    og_title = f"{share_portal.title} — Sahyog Setu" if share_portal else "Important Portals — Sahyog Setu"
    og_description = (
        Truncator(strip_tags(share_portal.description)).chars(160)
        if share_portal else
        f"Search {total_portals}+ important Indian government portals and go straight to the official site you need."
    )
    og_image = request.build_absolute_uri(share_portal.image.url) if share_portal and share_portal.image else None
    return render(request, "custom_admin/important_portals/portal_finder.html", {
        "total_portals": total_portals,
        "og_title": og_title,
        "og_description": og_description,
        "og_image": og_image,
        "share_url": request.build_absolute_uri(request.path) + (f"?portal={portal_id}" if portal_id else ""),
    })


@csrf_exempt
def portal_search_light(request):
    """Paginated search for the Important Portals page -- same reasoning
    as schemes.views.scheme_search_light: the existing /api/important-portals
    ships every active row's full description/mode_of_application in one
    unfiltered, unpaginated response. This ships only card-sized fields,
    paginated, matching a search box's actual page-at-a-time need."""
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    portals = Important_Portals.objects.filter(status=1)
    if body.get("searched_text"):
        portals = portals.filter(title__icontains=body["searched_text"])
    portals = portals.order_by("-id")

    total = portals.count()
    page = max(1, int(body.get("page") or 1))
    paginator = Paginator(portals, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for p in page_obj.object_list:
        desc = html_module.unescape(strip_tags(p.description or ""))
        results.append({
            "id": p.id,
            "title": p.title,
            "image": p.image.url if p.image else "",
            "short_description": Truncator(desc.strip()).chars(130),
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })
