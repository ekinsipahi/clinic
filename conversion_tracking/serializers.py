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

        existing = Conversion.objects.filter(gclid=gclid).first()
        if existing:
            print("kayıt güncelleniyor")
            for attr, value in validated_data.items():
                setattr(existing, attr, value)
            
            # 👇 timestamp'ı manuel güncelle
            existing.timestamp = timezone.now()
            existing.save()
            return existing

        print("yeni kayıt oluşturuluyor")
        return super().create(validated_data)
