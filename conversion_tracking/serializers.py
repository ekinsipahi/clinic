from rest_framework import serializers
from .models import Conversion
from django.utils import timezone
from clinic.models import CallMeLead


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


class CallMeLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallMeLead
        fields = [
            'id',
            'name',
            'phone',
            'message',
            'gclid',
            'client_info',
            'page',
            'created_at',
            'convert_to_conversion',
        ]
        read_only_fields = ['id', 'created_at', 'convert_to_conversion']

