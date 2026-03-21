from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Hesap Yönetimi"

    def ready(self):
        # Signal'ları kaydet — User kaydedilince otomatik UserProfile oluştur
        import accounts.signals  # noqa: F401