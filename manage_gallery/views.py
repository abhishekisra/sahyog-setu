from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .models import Images, Videoes

# Create your views here.

class ImageView(View):
    def get(self, request):
        if request.user.is_authenticated:
            images = Images.objects.all()
            return render(request, "custom_admin/manage-gallery/images.html", {'images' : images})
        else:
            messages.error(request, "You have to login first.")     
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            image = Images()           
            if request.FILES:
                image.status = request.POST.get('status')
                image.image = request.FILES['image']
                image.save()
                messages.success(request, "Image added successfully.")
                return redirect('adminGalleryImages')
            else:
                messages.error(request, "Image is required.")                
                return redirect('adminGalleryImages')
        else:
            messages.error(request, "You have to login first.")  
            return redirect('adminLogin')
        


def deleteImage(request):
    if request.user.is_authenticated:
        image_id = request.POST.get('image_id') 
        image = Images.objects.get(id = image_id)  
        image.delete()
        messages.success(request, "Banner deleted successfully.")
        return redirect('adminGalleryImages')
    else:
        messages.error(request, "You have to login first.")  
        return redirect('adminLogin')    

    
def updateImage(request, id):
    if request.user.is_authenticated:
        image = Images.objects.get(id = id)      
        image.status = int(request.POST.get('status'))
        if request.FILES:
            image.image = request.FILES['image']
        image.save()
        messages.success(request, "Image updated successfully.")
        return redirect('adminGalleryImages')
    else:
        messages.error(request, "You have to login first.")  
        return redirect('adminLogin')
    





class VideoView(View):
    def get(self, request):
        if request.user.is_authenticated:
            videoes = Videoes.objects.all()
            return render(request, "custom_admin/manage-gallery/videoes.html", {'videoes' : videoes})
        else:
            messages.error(request, "You have to login first.")     
            return redirect('adminLogin')
        

    def post(self, request):
        if request.user.is_authenticated:
            video = Videoes()
            video.status = request.POST.get('status')
            video.link = request.POST.get('link')
            video.save()
            messages.success(request, "Image added successfully.")
            return redirect('adminGalleryVideoes')
            
        else:
            messages.error(request, "You have to login first.")  
            return redirect('adminLogin')
        


def deleteVideo(request):
    if request.user.is_authenticated:
        video_id = request.POST.get('video_id') 
        video = Videoes.objects.get(id = video_id)  
        video.delete()
        messages.success(request, "Banner deleted successfully.")
        return redirect('adminGalleryVideoes')
    else:
        messages.error(request, "You have to login first.")  
        return redirect('adminLogin')    

    
def updateVideo(request, id):
    if request.user.is_authenticated:
        video = Videoes.objects.get(id = id)      
        video.status = int(request.POST.get('status'))
        video.link = request.POST.get('link')
        video.save()
        messages.success(request, "Image updated successfully.")
        return redirect('adminGalleryVideoes')
    else:
        messages.error(request, "You have to login first.")  
        return redirect('adminLogin')
    