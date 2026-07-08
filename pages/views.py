from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Pages



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
        