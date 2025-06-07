from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('randevu-al/', views.randevu_al, name='randevu-als'),
]

from django.views.generic import TemplateView

urlpatterns += [
    path('robots.txt', TemplateView.as_view(template_name="clinic/robots.txt", content_type="text/plain")),
    path('sitemap.xml', TemplateView.as_view(template_name="clinic/sitemap.xml", content_type="application/xml")),
]
