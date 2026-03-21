# ═══════════════════════════════════════════════════════════════════
# core/urls.py  —  SADECE BU İKİ SATIRI DEĞİŞTİR
# ═══════════════════════════════════════════════════════════════════
#
# ESKİ (hata veriyor):
#   path('soru-cevap/',          include('soru_cevap.urls', namespace='tr-qa')),
#   path('question-and-answer/', include('soru_cevap.urls', namespace='en-qa')),
#
# YENİ (çalışıyor):
#   path('soru-cevap/',          include(('soru_cevap.urls', 'soru_cevap'), namespace='tr-qa')),
#   path('question-and-answer/', include(('soru_cevap.urls', 'soru_cevap'), namespace='en-qa')),
#
# Neden: Django namespace= kullanırken app_name gerektirir.
# Tuple'ın 2. elemanı ('soru_cevap') app_name görevi görür.
# ═══════════════════════════════════════════════════════════════════

from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/",   include("conversion_tracking.urls")),
    path("blog/",  include("blog.urls")),

    # ↓↓↓  TUPLE FORM  ↓↓↓
    path('soru-cevap/',
         include(('soru_cevap.urls', 'soru_cevap'), namespace='tr-qa')),
    path('question-and-answer/',
         include(('soru_cevap.urls', 'soru_cevap'), namespace='en-qa')),
    path("accounts/", include("accounts.urls")),
]

urlpatterns += i18n_patterns(
    path("", include("clinic.urls")),
    prefix_default_language=False,
)