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

from .models import Legal_Registrations



class LegalRegistrationsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            legal_registrations = Legal_Registrations.objects.all()
            return render(request, "custom_admin/entrepreneurship/legal-registrations/legal-registrations.html", {'legal_registrations': legal_registrations})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class LegalRegistrationView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/entrepreneurship/legal-registrations/new-legal-registration.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                legal_registration = Legal_Registrations()
                legal_registration.title = request.POST.get('title')
                legal_registration.image = request.FILES['image']
                legal_registration.banner = request.FILES['banner']
                legal_registration.status = request.POST.get('status')
               
                legal_registration.description = request.POST.get('description')
                legal_registration.eligibility = request.POST.get('eligibility')
                legal_registration.required_documents = request.POST.get('required_documents')
                legal_registration.web_links = request.POST.get('web_links')
                legal_registration.mode_of_application = request.POST.get('mode_of_application')

                
                legal_registration.save()

                messages.success(request, "Legal RFegistration saved successfully.")
                return redirect('adminLegalRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminLegalRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditLegalRegistrationView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                legal_registration = Legal_Registrations.objects.get(id = id)
                return render(request, "custom_admin/entrepreneurship/legal-registrations/edit-legal-registration.html", {"legal_registration" : legal_registration})
            except Legal_Registrations.DoesNotExist:
                messages.error(request, "Legal reigistration doesn't exists.")
                return redirect('adminImportantDocuments')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                legal_registration = Legal_Registrations.objects.get(id = id)
                legal_registration.title = request.POST.get('title')
                if 'image' in request.FILES:
                    legal_registration.image = request.FILES['image']
                
                if 'banner' in request.FILES:
                    legal_registration.banner = request.FILES['banner']
               
                legal_registration.status = request.POST.get('status')
                
                legal_registration.description = request.POST.get('description')
                legal_registration.eligibility = request.POST.get('eligibility')
                legal_registration.required_documents = request.POST.get('required_documents')
                legal_registration.web_links = request.POST.get('web_links')
                legal_registration.mode_of_application = request.POST.get('mode_of_application')

                legal_registration.save()

                messages.success(request, "Important document saved successfully.")
                return redirect('adminLegalRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminLegalRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteLegalRegistration(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        legal_registration = Legal_Registrations.objects.get(id = id) 
        legal_registration.delete()
        messages.success(request, "Legal registration deleted successfully.")
        return redirect('adminLegalRegistrations')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def admin_legal_registration_detail(request, id):
    """Admin-only (login required) preview JSON for the "View" button on
    the Legal Registrations list -- NOT the public
    /api/entrepreneurship-developement/legal-registration/<id>, which
    filters status=1 and so 400s on an inactive/draft registration an
    admin is specifically trying to check before activating it."""
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Login required"}, status=403)
    try:
        obj = Legal_Registrations.objects.get(id=id)
    except Legal_Registrations.DoesNotExist:
        return JsonResponse({"message": "Invalid id"}, status=404)
    return JsonResponse({"legal_registration": {
        "title": obj.title,
        "description": obj.description,
        "eligibility": obj.eligibility,
        "required_documents": obj.required_documents,
    }})


def legal_registration_finder(request):
    """Public, no login -- Legal Registrations in the Scheme Viewer's own
    style (filter-less, same data shape as Important Documents/Schemes).

    ?registration=<id> renders real per-item Open Graph/Twitter tags
    server-side (see schemes.views.scheme_finder for why)."""
    total = Legal_Registrations.objects.filter(status=1).count()
    share_item = None
    item_id = request.GET.get('registration')
    if item_id:
        share_item = Legal_Registrations.objects.filter(status=1, id=item_id).first()
    og_title = f"{share_item.title} — Sahyog Setu" if share_item else "Legal Compliances — Sahyog Setu"
    og_description = (
        Truncator(strip_tags(share_item.description)).chars(160)
        if share_item else
        f"Search {total}+ legal registrations for starting and running a business in India."
    )
    og_image = request.build_absolute_uri(share_item.image.url) if share_item and share_item.image else None
    return render(request, "custom_admin/entrepreneurship/legal_registration_finder.html", {
        "total_legal_registrations": total,
        "og_title": og_title,
        "og_description": og_description,
        "og_image": og_image,
        "share_url": request.build_absolute_uri(request.path) + (f"?registration={item_id}" if item_id else ""),
    })


@csrf_exempt
def legal_registration_search_light(request):
    """Paginated search -- same reasoning as important_documents.views.document_search_light."""
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    items = Legal_Registrations.objects.filter(status=1)
    if body.get("searched_text"):
        items = items.filter(title__icontains=body["searched_text"])
    items = items.order_by("-id")

    total = items.count()
    page = max(1, int(body.get("page") or 1))
    paginator = Paginator(items, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for r in page_obj.object_list:
        desc = html_module.unescape(strip_tags(r.description or ""))
        results.append({
            "id": r.id,
            "title": r.title,
            "image": r.image.url if r.image else "",
            "short_description": Truncator(desc.strip()).chars(130),
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })
