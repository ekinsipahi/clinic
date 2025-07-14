from rest_framework import serializers
from .models import Conversion
from datetime import datetime

class ConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ['gclid', 'conversion_name', 'page', 'client_info']

    def create(self, validated_data):
        gclid = validated_data.get('gclid')
        device_info = validated_data.get('client_info', {})
        print("New device:", device_info) # Debugging line to check device info
        if gclid and Conversion.objects.filter(gclid=gclid).exists():
            raise serializers.ValidationError({'gclid': 'This GCLID has already been recorded.'})
        
        validated_data['conversion_time'] = datetime.utcnow()  # Google Ads UTC ister
        validated_data['client_info'] = device_info
        return super().create(validated_data)
