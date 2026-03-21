# soru_cevap/apps.py
# Mevcut dosyanı bu şekilde güncelle

from django.apps import AppConfig


class SoruCevapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "soru_cevap"
    verbose_name       = "Soru & Cevap"

    def ready(self):
        from . import notifications  # noqa — signal'ları kayıt eder