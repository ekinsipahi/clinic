from django.shortcuts import render

# Create your views here.

def homepage(request):
    return render(request, 'clinic/index.html')


def randevu_al(request):
    return render(request, 'clinic/randevu-al.html')


def whatsapp_yonlendir(request):
    return render(request, 'clinic/whatsapp-yonlendir.html')

def telefon_yonlendir(request):
    return render(request, 'clinic/telefon-yonlendir.html')