from rest_framework import serializers
from .models import Conversion
from datetime import datetime

class ConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ['gclid', 'conversion_name', 'page']

    def create(self, validated_data):
        validated_data['conversion_time'] = datetime.utcnow()  # Google Ads UTC ister
        return super().create(validated_data)
