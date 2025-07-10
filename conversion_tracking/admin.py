from django.contrib import admin
from .models import Conversion


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
            obj.conversion_time.strftime('%Y-%m-%d %H:%M:%S'),
            f'{obj.conversion_value:.2f}',
            obj.currency
        ])

    return response


@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ('gclid', 'conversion_name', 'conversion_value', 'currency', 'page', 'is_converted', 'phone_number', 'timestamp')
    list_filter = ('is_converted', 'page', 'currency')
    search_fields = ('gclid', 'phone_number', 'conversion_name')
    ordering = ('-timestamp',)
    
    actions = [export_selected_to_csv]



