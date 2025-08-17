from django.contrib import admin, messages
from django.utils.html import format_html
from .models import CallMeLead, ArrivalConfirmation

@admin.register(CallMeLead)
class CallMeLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "created_at", "convert_to_conversion")
    list_filter = ("convert_to_conversion",)
    search_fields = ("name", "phone")
    ordering = ("-created_at",)  # <-- En yeni en üstte görünür

    readonly_fields = ("gclid", "page", "created_at", "client_info", "message")  # <-- Bunlar düzenlenemez


@admin.register(ArrivalConfirmation)
class ArrivalConfirmationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "full_name", "phone", "gclid", "page", "matched_link", "converted_at", "convert_button")
    list_filter = ("created_at", "page")
    search_fields = ("full_name", "phone", "gclid", "page")
    actions = ["action_convert_to_conversion"]
    readonly_fields = ("matched_conversion", "converted_at")

    def matched_link(self, obj):
        if obj.matched_conversion_id:
            # app label'ı kendi projenle değiştir (örn. conversion_tracking/conversion)
            return format_html('<a href="/admin/conversion_tracking/conversion/{}/change/">#{}</a>',
                               obj.matched_conversion_id, obj.matched_conversion_id)
        return "—"
    matched_link.short_description = "Conversion"

    def convert_button(self, obj):
        if obj.matched_conversion_id:
            return "Done"
        return format_html('<a class="button" href="{}">Dönüştür</a>', f"./{obj.pk}/convert/")
    convert_button.short_description = "Tek Tuş"

    # tekil buton için custom url
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        def wrap(view): return self.admin_site.admin_view(view)
        return [path("<int:pk>/convert/", wrap(self.convert_single), name="arrival_convert_single")] + urls

    def convert_single(self, request, pk, *args, **kwargs):
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(request, "Kayıt bulunamadı.", level=messages.ERROR)
            from django.shortcuts import redirect
            return redirect("..")
        conv, created = obj.convert()
        msg = f"Conversion #{conv.id} " + ("OLUŞTURULDU" if created else "GÜNCELLENDİ")
        self.message_user(request, msg, level=messages.SUCCESS)
        from django.shortcuts import redirect
        return redirect(f"/admin/conversion_tracking/conversion/{conv.id}/change/")

    # toplu action
    def action_convert_to_conversion(self, request, queryset):
        cnt = 0
        for obj in queryset:
            obj.convert()
            cnt += 1
        self.message_user(request, f"{cnt} kayıt dönüştürüldü.", level=messages.SUCCESS)
    action_convert_to_conversion.short_description = "Seçilenleri Conversion'a dönüştür"
