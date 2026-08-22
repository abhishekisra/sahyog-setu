from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from .models import Pages, PageTranslation
from languages.utils import clean_language, available_languages_for
from custom_admin.translation_views import TranslationsPickerView, EditTranslationView



class PagesView(View):
    def get(self, request):
        if request.user.is_authenticated:
            pages = Pages.objects.all()
            return render(request, "custom_admin/pages/pages.html", {'pages': pages})
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')



class PageView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "custom_admin/pages/new-page.html")
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            try:
                page = Pages()
                page.title = request.POST.get('title')
                page.status = request.POST.get('status')
                page.image = request.FILES['image']
                page.description = request.POST.get('description')
                page.save()
                messages.success(request, "page saved successfully.")
                return redirect('adminPages')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminImportantDocuments')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




class EditPageView(View):
    def get(self, request, id):
        if request.user.is_authenticated:
            try:
                page = Pages.objects.get(id = id)
                return render(request, "custom_admin/pages/edit-page.html", {"page" : page})
            except Pages.DoesNotExist:
                messages.error(request, "Pages doesn't exists.")
                return redirect('adminPages')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')
        

    def post(self, request, id):
        if request.user.is_authenticated:
            try:
                page = Pages.objects.get(id = id)
                page.title = request.POST.get('title')
                page.status = request.POST.get('status')
                page.description = request.POST.get('description')
                if request.FILES['image']:
                    page.image = request.FILES['image']
                page.save()
                messages.success(request, "page saved successfully.")
                return redirect('adminPages')
            except Exception as e:
                print(e)
                messages.error(request, "Something went wrong. Please try again later.")
                return redirect('adminPages')
        else:
            messages.error(request, "You have to login first.")
            return redirect('adminLogin')




def deletePage(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        page = Pages.objects.get(id = id)
        page.delete()
        messages.success(request, "Important page deleted successfully.")
        return redirect('adminPages')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def page_finder(request):
    """Public, no login -- replaces the old SPA's /pages route. Only 5 rows
    today: a flat card grid (title + image), same shape as the other small
    *_finder pages, linking into page_detail for the full description."""
    lang = clean_language(request.GET.get("lang", "en"))
    items = list(Pages.objects.filter(status=1).order_by("title"))
    for p in items:
        p.display_title = p.field_for("title", lang)
    languages, _ = available_languages_for(PageTranslation.objects.all(), field="title")
    return render(request, "custom_admin/pages/page_finder.html", {
        "pages_items": items,
        "languages": languages,
        "lang": lang,
    })


def page_detail(request, id):
    """Full text of one page. Server-rendered (not a JS/DRF overlay like the
    bigger finder pages) since there are only 5 rows -- not worth the
    extra API surface for this few."""
    lang = clean_language(request.GET.get("lang", "en"))
    page = get_object_or_404(Pages, id=id, status=1)
    languages, _ = available_languages_for(PageTranslation.objects.filter(page=page))
    return render(request, "custom_admin/pages/page_detail.html", {
        "page": page,
        "display_title": page.field_for("title", lang),
        "display_description": page.field_for("description", lang),
        "languages": languages,
        "lang": lang,
    })


class PageTranslationsView(TranslationsPickerView):
    model = Pages
    translation_model = PageTranslation
    fk_name = "page"
    fields = ["title", "description"]
    list_url_name = "adminPages"
    list_label = "Pages"
    edit_url_name = "adminPageEditTranslation"


class PageEditTranslationView(EditTranslationView):
    model = Pages
    translation_model = PageTranslation
    fk_name = "page"
    fields = [("title", "Title", "text"), ("description", "Description", "textarea")]
    picker_url_name = "adminPageTranslations"
        