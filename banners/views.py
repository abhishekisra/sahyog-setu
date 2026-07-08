from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import Banners

# Create your views here.

class BannerView(View):
    def get(self, request):
        if request.user.is_authenticated:
            banners = Banners.objects.all()
            return render(request, "custom_admin/banners.html", {'banners' : banners})
        else:
            messages.error(request, "You have to login first.")     
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            banner = Banners()           
            if request.FILES:
                banner.status = request.POST.get('status')
                banner.image = request.FILES['image']
                banner.save()
                messages.success(request, "Banner added successfully.")
                return redirect('adminBanners')
            else:
                messages.error(request, "Image is required.")                
                return redirect('adminBanners')
        else:
            messages.error(request, "You have to login first.")  
            return redirect('adminLogin')
        


def deleteBanner(request):
    if request.user.is_authenticated:
        banner_id = request.POST.get('banner_id') 
        banner = Banners.objects.get(id = banner_id)  
        banner.delete()
        messages.success(request, "Banner deleted successfully.")
        return redirect('adminBanners')
    else:
        messages.error(request, "You have to login first.")  
        return redirect('adminLogin')    

    
def updateBanner(request, id):
    if request.user.is_authenticated:
        banner = Banners.objects.get(id = id)      
        banner.status = int(request.POST.get('status'))
        if request.FILES:
            banner.image = request.FILES['image']
        banner.save()
        messages.success(request, "Banner updated successfully.")
        return redirect('adminBanners')
    else:
        messages.error(request, "You have to login first.")  
        return redirect('adminLogin')
    