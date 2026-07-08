from sre_parse import State
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from .models import Testimonials



# Create your views here.

class TestimonialsView(View):

    def get(self, request):
        if request.user.is_authenticated:
            testimonials = Testimonials.objects.all()
            return render(request, 'custom_admin/testimonials.html', {'testimonials': testimonials})
        else:
            messages.error(request, "you have to login first")
            return redirect('adminLogin')

        
    def post(self, request):
        if request.user.is_authenticated:
            testimonial =  Testimonials()
            testimonial.status = int(request.POST.get('status'))
            if request.FILES:
                testimonial.image = request.FILES['image']
                testimonial.save()
                messages.success(request, "Testimonial added sucessfully")
                return redirect('adminTestimonials')
            else:
                messages.error(request, "Image is required.")
                return redirect('adminTestimonials')
        else:
            messages.error(request, "you have to login first.")
            return redirect('adminLogin')


        

def deleteTestimonial(request):
    if request.user.is_authenticated:
        id = request.POST.get('id')
        testimonial = Testimonials.objects.get(id = id) 
        testimonial.delete()
        messages.success(request, "Testimonial deleted successfully.")
        return redirect('adminTestimonials')
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')
        


def updateTestimonial(request, id):
    if request.user.is_authenticated:
        testimonial = Testimonials.objects.get(id = id) 
        if request.FILES:
            testimonial.image = request.FILES['image']
        testimonial.status = int(request.POST.get('status'))
        testimonial.save()
        messages.success(request, "Category updated successfully.")
        return redirect('adminTestimonials')            
    else:
        messages.error(request, "You have to login first.")
        return redirect('adminLogin')




