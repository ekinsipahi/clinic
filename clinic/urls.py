from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('randevu-al/', views.randevu_al, name='randevu-al'),
    path('whatsapp-yonlendirme/', views.whatsapp_yonlendir, name='whatsapp-yonlendirme'),
    path('telefon-yonlendirme/', views.telefon_yonlendir, name='telefon-yonlendirme'),
]

from django.views.generic import TemplateView

urlpatterns += [
    path('robots.txt', TemplateView.as_view(template_name="clinic/robots.txt", content_type="text/plain")),
    path('llms.txt', TemplateView.as_view(template_name="clinic/llms.txt", content_type="text/plain")),
    path('sitemap.xml', TemplateView.as_view(template_name="clinic/sitemap.xml", content_type="application/xml")),
]
