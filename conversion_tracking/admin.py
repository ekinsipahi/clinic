from django.contrib import admin
from .models import Conversion
from .forms import ConversionForm
from django.utils.timezone import now
from django.utils.html import format_html

from django.contrib.admin import SimpleListFilter
from django.utils import timezone


class TodayFilter(SimpleListFilter):
    title = 'Bugün'
    parameter_name = 'today'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Sadece Bugün'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'today':
            today = timezone.now().date()
            return queryset.filter(timestamp__date=today)
        return queryset



@admin.action(description="Seçilenleri CSV olarak dışa aktar")
def export_selected_to_csv(modeladmin, request, queryset):
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="conversions_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['Google Click ID', 'Conversion Name', 'Conversion Time', 'Conversion Value', 'Conversion Currency'])

    for obj in queryset.filter(is_converted=True):
        writer.writerow([
            obj.gclid or '',
            obj.conversion_name,
            obj.conversion_time.isoformat(),  # ISO 8601 format for Google Ads
            f'{obj.conversion_value:.2f}',
            obj.currency
        ])

    return response

@admin.action(description="Seçilenleri Google Sheet'e gönder")
def export_to_google_sheets(modeladmin, request, queryset):
    from .google_sheets import push_to_sheet
    import hashlib

    CONVERTED_SHEET_ID = "1UWdGRcGii3WHzeIyPQeI_zaub3M0s4iKZ1_J6WUlf1Q"
    QUALIFIED_SHEET_ID = "1MdpVbMAcP-JDilGXHqqYAhmkiWH9TCB0VRet_ofbNZ0"

    for obj in queryset:
        hashed_phone = ''
        if obj.phone_number:
            hashed_phone = hashlib.sha256(obj.phone_number.encode()).hexdigest()

        # Gönderilecek satırları hazırla
        qualified_row = [
            obj.gclid or '',
            obj.qualification_time.isoformat() if obj.qualification_time else '',
            f"{obj.conversion_value}",
            obj.currency,
            hashed_phone
        ]

        converted_row = [
            obj.gclid or '',
            obj.conversion_time.isoformat() if obj.conversion_time else '',
            f"{obj.conversion_value}",
            obj.currency,
            hashed_phone
        ]

        # Her biri için ayrı kontrol yap
        if obj.is_qualified:
            push_to_sheet(QUALIFIED_SHEET_ID, qualified_row)

        if obj.is_converted:
            push_to_sheet(CONVERTED_SHEET_ID, converted_row)



@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    form = ConversionForm
    list_display = (
        'timestamp',
        'gclid', 'conversion_name', 'conversion_value', 'currency',
        'is_qualified', 'is_converted', 'phone_number', 'display_client_info'
    )
    list_filter = ('is_converted', 'page', 'currency', TodayFilter, 'is_qualified')
    search_fields = ('gclid', 'phone_number',)
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'display_client_info', 'gclid', 'page', 'conversion_name', 'currency',)
    exclude = ('client_info',)
    actions = [export_selected_to_csv, export_to_google_sheets]

    def display_client_info(self, obj):
        if not obj.client_info:
            return "—"
        device = obj.client_info.get('device_type', 'unknown device')
        low_power = obj.client_info.get('low_power_mode', False)
        return f"{device} | Low Power Mode: {'✅' if low_power else '❌'}"
    display_client_info.short_description = "Cihaz Bilgisi"



    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
