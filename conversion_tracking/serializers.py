from rest_framework import serializers
from .models import Conversion
from rest_framework.serializers import ModelSerializer
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
    
class ConversionActualCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ["actually_called"]  # sadece bu alanı güncelliyoruz
        extra_kwargs = {
            "actually_called": {"required": True},
        }

    def update(self, instance, validated_data):
        # güvenli alım + doğrulama
        if "actually_called" not in validated_data:
            raise serializers.ValidationError({"actually_called": "This field is required."})

        val = validated_data.get("actually_called")

        # DRF normalde bool'a çevirir ama yine de sert kontrol:
        if not isinstance(val, bool):
            # "true"/"false" string geldiyse burada normalize edebilirsin
            raise serializers.ValidationError({"actually_called": "Must be boolean (true/false)."})

        instance.actually_called = val
        instance.timestamp = timezone.now()
        instance.save(update_fields=["actually_called", "timestamp"])
        return instance


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

