from django.db import models
from django.utils import timezone
from conversion_tracking.models import Conversion  # Conversion modeli ile aynı dosyada değilse

class CallMeLead(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    gclid = models.CharField(max_length=255, blank=True, null=True)
    client_info = models.JSONField(null=True, blank=True)
    page = models.CharField(max_length=255, blank=True, default="Ana Sayfa")
    created_at = models.DateTimeField(auto_now_add=True)
    convert_to_conversion = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.convert_to_conversion and not Conversion.objects.filter(gclid=self.gclid).exists():
            Conversion.objects.create(
                phone_number=self.phone,
                gclid=self.gclid,
                conversion_name="CallMeLead",
                is_qualified=True,
                is_converted=False,
                qualification_time=timezone.now(),
                client_info=self.client_info,
                page="Beni Ara Lead"
            )

    def __str__(self):
        return f"{self.name} - {self.phone}"
