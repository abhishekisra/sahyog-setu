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
from .models import Organization_Registration




class OrganizationRegistrationsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            organization_registrations = Organization_Registration.objects.all()
            return render(request, "custom_admin/entrepreneurship/organization-registrations/organization-registrations.html", {'organization_registrations': organization_registrations})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class OrganizationRegistrationView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/entrepreneurship/organization-registrations/new-organization-registration.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                organization_registration = Organization_Registration()
                organization_registration.title = request.POST.get('title')
                organization_registration.status = request.POST.get('status')
                organization_registration.description = request.POST.get('description')
                organization_registration.image = request.FILES['image']
                organization_registration.banner = request.FILES['banner']
                organization_registration.mode_of_application = request.POST.get('mode_of_application')
                if 'pdf' in request.FILES:
                    organization_registration.pdf = request.FILES['pdf']
                organization_registration.save()
                messages.success(request, "Organization registration saved successfully.")
                return redirect('adminOrganizationRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminOrganizationRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditOrganizationRegistrationView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                organization_registration = Organization_Registration.objects.get(id = id)
                return render(request, "custom_admin/entrepreneurship/organization-registrations/edit-organization-registration.html", {'organization_registration' : organization_registration})
            except Organization_Registration.DoesNotExist:
                messages.error(request, "Organization registration doesn't exists.")
                return redirect('adminOrganizationRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                organization_registration = Organization_Registration.objects.get(id = id)
                organization_registration.title = request.POST.get('title')
                organization_registration.status = request.POST.get('status')
                organization_registration.description = request.POST.get('description')
                organization_registration.mode_of_application = request.POST.get('mode_of_application')
                if 'image' in request.FILES:
                    organization_registration.image = request.FILES['image']
                if 'banner' in request.FILES:
                    organization_registration.banner = request.FILES['banner']
                if 'pdf' in request.FILES:
                    organization_registration.pdf = request.FILES['pdf']
                organization_registration.save()
                messages.success(request, "Organization registration saved successfully.")
                return redirect('adminOrganizationRegistrations')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminOrganizationRegistrations')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteOrganizationRegistration(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        organization_registration = Organization_Registration.objects.get(id = id) 
        organization_registration.delete()
        messages.success(request, "Organization registration deleted successfully.")
        return redirect('adminOrganizationRegistrations')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def admin_organization_registration_detail(request, id):
    """Admin-only (login required) preview JSON for the "View" button on
    the Organization Registrations list -- NOT the public
    /api/entrepreneurship-developement/organization-registration/<id>,
    which filters status=1 and so 400s on an inactive/draft registration
    an admin is specifically trying to check before activating it."""
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Login required"}, status=403)
    try:
        obj = Organization_Registration.objects.get(id=id)
    except Organization_Registration.DoesNotExist:
        return JsonResponse({"message": "Invalid id"}, status=404)
    return JsonResponse({"organization_registration": {
        "title": obj.title,
        "description": obj.description,
    }})


def organization_registration_finder(request):
    """Public, no login -- Organization Registrations in the Scheme
    Viewer's own style. This model has no eligibility/required_documents
    (unlike Legal Registrations), just description + an optional pdf +
    mode_of_application -- the detail overlay shows Overview + an optional
    Download PDF button + the usual Apply-link button."""
    total = Organization_Registration.objects.filter(status=1).count()
    return render(request, "custom_admin/entrepreneurship/organization_registration_finder.html", {
        "total_organization_registrations": total,
    })


@csrf_exempt
def organization_registration_search_light(request):
    """Paginated search -- same reasoning as sibling *_search_light views."""
    PAGE_SIZE = 9
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    items = Organization_Registration.objects.filter(status=1)
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
