from django.db import models

class Conversion(models.Model):
    page = models.CharField(max_length=255, null=True, blank=True)
    is_converted = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Timestamp kaydı
    timestamp = models.DateTimeField(auto_now_add=True)

    # Google Ads için gerekli alanlar
    gclid = models.CharField(max_length=255, null=True, blank=True)
    conversion_name = models.CharField(max_length=255)
    conversion_time = models.DateTimeField(auto_now_add=True)  # aynı değeri alacak
    conversion_value = models.FloatField(default=0.0)
    currency = models.CharField(max_length=10, default='TRY')

    def __str__(self):
        return f"{self.gclid} - {self.page}"
