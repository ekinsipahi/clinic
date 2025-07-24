from django.db import models
from django.utils.timezone import now


class Conversion(models.Model):
    page = models.CharField(max_length=255, null=True, blank=True)
    is_converted = models.BooleanField(default=False)
    is_qualified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Timestamp kaydı
    timestamp = models.DateTimeField(auto_now_add=True)

    # Google Ads için gerekli alanlar
    gclid = models.CharField(max_length=255, null=True, blank=True)
    conversion_name = models.CharField(max_length=255)
    conversion_time = models.DateTimeField(null=True, blank=True)
    qualification_time = models.DateTimeField(null=True, blank=True)
    conversion_value = models.FloatField(default=0.0)
    currency = models.CharField(max_length=10, default='TRY')
    
    # Additional client info
    client_info = models.JSONField(null=True, blank=True)


    def __str__(self):
        return f"{self.gclid} - {self.page}"

    def save_model(self, request, obj, form, change):
        if 'is_converted' in form.changed_data and obj.is_converted:
            obj.conversion_time = now()
        super().save_model(request, obj, form, change)
        

