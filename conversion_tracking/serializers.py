from rest_framework import serializers
from .models import Conversion
from datetime import datetime

class ConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ['gclid', 'conversion_name', 'page']

    def create(self, validated_data):
        gclid = validated_data.get('gclid')
        if gclid and Conversion.objects.filter(gclid=gclid).exists():
            raise serializers.ValidationError({'gclid': 'This GCLID has already been recorded.'})
        
        validated_data['conversion_time'] = datetime.utcnow()  # Google Ads UTC ister
        return super().create(validated_data)
