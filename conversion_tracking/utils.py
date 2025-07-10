import csv
from django.utils.timezone import localtime
from conversion_tracking.models import Conversion

def export_conversions_to_csv(filepath='converted_conversions.csv'):
    queryset = Conversion.objects.filter(is_converted=True)

    with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Google_Click_ID', 'Conversion_Name', 'Conversion_Time', 'Conversion_Value', 'Conversion_Currency'])

        for obj in queryset:
            writer.writerow([
                obj.gclid or '',
                obj.conversion_name,
                obj.conversion_time.strftime('%Y-%m-%d %H:%M:%S'),
                f'{obj.conversion_value:.2f}',
                obj.currency
            ])
    return filepath
