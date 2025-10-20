from django.urls import path, re_path
from . import views
from django.views.generic import TemplateView

from django.contrib import admin
from django.urls import path, include


from django.contrib.sitemaps.views import sitemap as django_sitemap

from clinic.sitemaps import AutoURLSitemap, CategorySitemap, PostSitemap

sitemaps = {
    "static-auto": AutoURLSitemap,     # parametresiz named URL’ler
    "blog-categories": CategorySitemap,
    "blog-posts": PostSitemap,
}


urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('randevu-al/', views.randevu_al, name='randevu-al'),
    path('whatsapp-yonlendirme/', views.whatsapp_yonlendir, name='whatsapp-yonlendirme'),
    path('telefon-yonlendirme/', views.telefon_yonlendir, name='telefon-yonlendirme'),
    path('maps-yonlendirme/', views.maps_yonlendir, name='maps-yonlendirme'),
    path('instagram-yonlendirme/', views.instagram_yonlendir, name='instagram-yonlendirme'),
    path('kvkk/', views.kvkk, name="kvkk-bilgilendirme"),
    path('tesekkur/', views.tesekkurler, name='tesekkurler'),
    
    # yeni:
    path('onay/', views.onay, name='onay'),
    path('onay-tesekkur/', views.onay_tesekkur, name='onay-tesekkur'),
]


urlpatterns += [
    path('robots.txt', TemplateView.as_view(template_name="clinic/robots.txt", content_type="text/plain")),
    path('llms.txt', TemplateView.as_view(template_name="clinic/llms.txt", content_type="text/plain")),
    path("sitemap.xml", django_sitemap, {"sitemaps": sitemaps}, name="django-sitemap"),
]


# ---- 404 yapılandırma (önerilen) ----
# Bu satır ROOT URLCONF'ta olmalı. Bu dosya root ise burada kalabilir.
handler404 = 'clinic.views.page_not_found_view'

# ---- (Opsiyonel) App-scope catch-all ----
# Bu, sadece BU app’in altında kalan “eşleşmeyen” yolları 404 sayfana düşürür.
# Root’ta başka app’lerin önüne geçmemesi için en sonda kalsın.
urlpatterns += [
    re_path(r'^.*/$', views.page_not_found_view),  # status=404 döndüğü için SEO güvenli
]
