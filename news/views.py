from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import News, NewsTranslation
from languages.utils import clean_language, available_languages_for
from custom_admin.translation_views import TranslationsPickerView, EditTranslationView

# Create your views here.

class NewsView(View):

    def get(self, request):
        if request.user.is_authenticated:
            news = News.objects.all()
            return render(request, 'custom_admin/news.html', {'news': news})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            news =  News()
            news.news = request.POST.get('news')
            news.status = int(request.POST.get('status'))
            news.link = request.POST.get('link')
            news.save()
            messages.success(request, "News added sucessfully")
            return redirect('adminNews')
        else:
             messages.error(request, "you have to login first.")
             return redirect('adminLogin')



        
def deleteNews(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        news = News.objects.get(id = id) 
        news.delete()
        messages.success(request, "News deleted successfully.")
        return redirect('adminNews')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateNews(request, id):
    if request.user.is_authenticated:
        news = News.objects.get(id = id)
        news.news = request.POST.get('news')
        news.status = int(request.POST.get('status'))
        news.link = request.POST.get('link')
        news.save()
        messages.success(request, "News updated successfully.")
        return redirect('adminNews')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')


def news_finder(request):
    """Public, no login -- replaces the old SPA's /news page. Only 7 rows
    today, so a flat card grid is enough: no pagination/search-light
    machinery like the bigger *_finder pages. Each card is just the
    translated headline + an outbound link -- no detail overlay needed."""
    lang = clean_language(request.GET.get("lang", "en"))
    items = list(News.objects.filter(status=1).order_by("-id"))
    for n in items:
        n.display_news = n.field_for("news", lang)
        n.is_url = (n.link or "").startswith("http")
    languages, _ = available_languages_for(NewsTranslation.objects.all(), field="news")
    return render(request, "custom_admin/news/news_finder.html", {
        "news_items": items,
        "languages": languages,
        "lang": lang,
    })


class NewsTranslationsView(TranslationsPickerView):
    model = News
    translation_model = NewsTranslation
    fk_name = "news_item"
    fields = ["news"]
    object_label = "news"
    list_url_name = "adminNews"
    list_label = "News"
    edit_url_name = "adminNewsEditTranslation"


class NewsEditTranslationView(EditTranslationView):
    model = News
    translation_model = NewsTranslation
    fk_name = "news_item"
    fields = [("news", "Headline", "textarea")]
    object_label = "news"
    picker_url_name = "adminNewsTranslations"

