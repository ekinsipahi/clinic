from django.contrib import admin
from .models import CallMeLead

@admin.register(CallMeLead)
class CallMeLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "created_at", "convert_to_conversion")
    list_filter = ("convert_to_conversion",)
    search_fields = ("name", "phone")
    ordering = ("-created_at",)  # <-- En yeni en üstte görünür

    readonly_fields = ("gclid", "page", "created_at", "client_info", "message")  # <-- Bunlar düzenlenemez
