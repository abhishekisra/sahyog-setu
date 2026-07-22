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

from .models import Important_Documents



class ImportantDocumentsView(View):
    def get(self, request):
        if request.user.is_authenticated:
            important_documents = Important_Documents.objects.all()
            return render(request, "custom_admin/important-documents/important-documents.html", {'important_documents': important_documents})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class ImportantDocumentView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/important-documents/new-important-document.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                important_document = Important_Documents()
                important_document.title = request.POST.get('title')
                important_document.image = request.FILES['image']
                important_document.banner = request.FILES['banner']
                important_document.status = request.POST.get('status')
               
                important_document.description = request.POST.get('description')
                important_document.eligibility = request.POST.get('eligibility')
                important_document.required_documents = request.POST.get('required_documents')
                important_document.web_links = request.POST.get('web_links')
                important_document.mode_of_application = request.POST.get('mode_of_application')

                
                important_document.save()

                messages.success(request, "Important document saved successfully.")
                return redirect('adminImportantDocuments')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminImportantDocuments')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditImportantDocumentView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                important_document = Important_Documents.objects.get(id = id)
                return render(request, "custom_admin/important-documents/edit-important-document.html", {"important_document" : important_document})
            except Important_Documents.DoesNotExist:
                messages.error(request, "Important document doesn't exists.")
                return redirect('adminImportantDocuments')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                important_document = Important_Documents.objects.get(id = id)
                important_document.title = request.POST.get('title')
                if 'image' in request.FILES:
                    important_document.image = request.FILES['image']
                
                if 'banner' in request.FILES:
                    important_document.banner = request.FILES['banner']
               
                important_document.status = request.POST.get('status')
                
                important_document.description = request.POST.get('description')
                important_document.eligibility = request.POST.get('eligibility')
                important_document.required_documents = request.POST.get('required_documents')
                important_document.web_links = request.POST.get('web_links')
                important_document.mode_of_application = request.POST.get('mode_of_application')

                important_document.save()

                messages.success(request, "Important document saved successfully.")
                return redirect('adminImportantDocuments')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminImportantDocuments')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deleteImportantDocument(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        important_document = Important_Documents.objects.get(id = id) 
        important_document.delete()
        messages.success(request, "Important document deleted successfully.")
        return redirect('adminImportantDocuments')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def document_finder(request):
    """Public, no login -- Important Documents in the Scheme Viewer's own
    style (filter-less: this model has no category/type field, so it's a
    search box + card grid + detail overlay). Mirrors
    important_portals.views.portal_finder."""
    total_documents = Important_Documents.objects.filter(status=1).count()
    return render(request, "custom_admin/important_documents/document_finder.html", {
        "total_documents": total_documents,
    })


@csrf_exempt
def document_search_light(request):
    """Paginated search for the Important Documents page -- same reasoning
    as important_portals.views.portal_search_light: the existing
    /api/important-documents ships every active row's full description/
    eligibility/required_documents in one unfiltered, unpaginated response."""
    PAGE_SIZE = 8
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        body = {}

    documents = Important_Documents.objects.filter(status=1)
    if body.get("searched_text"):
        documents = documents.filter(title__icontains=body["searched_text"])
    documents = documents.order_by("-id")

    total = documents.count()
    page = max(1, int(body.get("page") or 1))
    paginator = Paginator(documents, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for d in page_obj.object_list:
        desc = html_module.unescape(strip_tags(d.description or ""))
        results.append({
            "id": d.id,
            "title": d.title,
            "image": d.image.url if d.image else "",
            "short_description": Truncator(desc.strip()).chars(130),
        })

    return JsonResponse({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "num_pages": paginator.num_pages,
    })
