from rest_framework import serializers
from .models import Conversion
from django.utils import timezone


class ConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ['gclid', 'conversion_name', 'page', 'client_info']

    def create(self, validated_data):
        gclid = validated_data.get('gclid')
        device_info = validated_data.get('client_info', {})
        print("New device:", device_info)

        validated_data['conversion_time'] = timezone.now()
        validated_data['client_info'] = device_info

        # Eğer aynı GCLID varsa kaydı güncelle
        print("kayıt güncelleniyor")
        existing = Conversion.objects.filter(gclid=gclid).first()
        if existing:
            for attr, value in validated_data.items():
                setattr(existing, attr, value)
            existing.save()
            return existing

        # Yoksa yeni kayıt oluştur
        return super().create(validated_data)
