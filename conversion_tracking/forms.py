from django import forms
from django.core.exceptions import ValidationError
from .models import Conversion
import re


class ConversionForm(forms.ModelForm):
    class Meta:
        model = Conversion
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()

        is_converted = cleaned_data.get('is_converted')
        is_qualified = cleaned_data.get('is_qualified')
        qualification_time = cleaned_data.get('qualification_time')
        conversion_value = cleaned_data.get('conversion_value')
        phone_number = cleaned_data.get('phone_number')
        conversion_time = cleaned_data.get('conversion_time')

        instance = self.instance  # Mevcut kayıt

        errors = []

        # Önceden True yapıldıysa, geri alınamaz
        if instance.pk:
            if instance.is_qualified and not is_qualified:
                errors.append("❌ 'Qualified' bir kez işaretlendikten sonra kaldırılamaz.")
            if instance.is_converted and not is_converted:
                errors.append("❌ 'Converted' bir kez işaretlendikten sonra kaldırılamaz.")

        # Qualified ise zaman zorunlu
        if is_qualified and not qualification_time:
            errors.append("❌ Qualified olarak işaretleyebilmek için bir 'Qualification Time' girilmelidir.")

        # Converted için kontroller
        if is_converted:
            if not is_qualified:
                errors.append("❌ Converted olarak işaretleyebilmek için önce 'Qualified' kutucuğunu seçmelisiniz.")
            if not qualification_time:
                errors.append("❌ Converted olarak işaretleyebilmek için 'Qualification Time' da girilmiş olmalıdır.")
            if not conversion_value or conversion_value <= 0:
                errors.append("❌ Converted olarak işaretlemeden önce geçerli bir 'Conversion Value' girin (örn. 1000).")
            if not phone_number or not phone_number.strip():
                errors.append("❌ Converted olarak işaretlemeden önce geçerli bir telefon numarası girilmelidir.")
            else:
                # Telefon numarası regex doğrulama
                pattern = re.compile(r'^\+?[0-9]{10,15}$')
                if not pattern.match(phone_number.strip()):
                    errors.append("❌ Telefon numarası geçersiz formatta. Örn: +905055771883 veya 05055771883")

        # Ek kontrol: Converted işaretliyse ama conversion_time girilmemişse
        if is_converted and not conversion_time:
            errors.append("❌ 'Converted' olarak işaretleyebilmek için 'Conversion Time' girilmiş olmalıdır.")

        # Ek kontrol: conversion_time varsa converted işaretli olmalı
        if conversion_time and not is_converted:
            errors.append("❌ 'Conversion Time' girilmiş ancak 'Converted' kutucuğu işaretlenmemiş.")

        if errors:
            raise ValidationError(errors)

        return cleaned_data
