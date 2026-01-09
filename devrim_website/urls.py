from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("conversion_tracking.urls")),
    path("blog/", include("blog.urls")),  # sadece TR
]

urlpatterns += i18n_patterns(
    path("", include("clinic.urls")),
    prefix_default_language=False,  # 🔥 EN KRİTİK SATIR
)
