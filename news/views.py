from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import News

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

