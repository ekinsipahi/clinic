"""
accounts/admin.py

Admin özellikleri:
  • "Onay Bekleyen Doktorlar" filtresi — tek tık ile görünür
  • approve_doctors ve reject_doctors bulk action
  • Onay/Red sebebi inline düzenleme
  • User admin'e ProfileInline eklendi
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.html import format_html
from .models import UserProfile

User = get_user_model()


# ── Custom filter ─────────────────────────────────────────────────────────────
class DoctorApprovalFilter(admin.SimpleListFilter):
    title = "Doktor Durumu"
    parameter_name = "doctor_status"

    def lookups(self, request, model_admin):
        return [
            ("pending",  "⏳ Onay Bekleyen"),
            ("approved", "✓ Onaylı Doktor"),
            ("rejected", "✗ Reddedilen"),
            ("patient",  "Hasta / Kullanıcı"),
        ]

    def queryset(self, request, qs):
        if self.value() == "pending":
            return qs.filter(role="doctor", doctor_approved=False,
                             doctor_rejection_reason="")
        if self.value() == "approved":
            return qs.filter(role="doctor", doctor_approved=True)
        if self.value() == "rejected":
            return qs.filter(role="doctor", doctor_approved=False).exclude(
                doctor_rejection_reason="")
        if self.value() == "patient":
            return qs.filter(role="patient")
        return qs


# ── UserProfile admin ─────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "get_display_name", "user_email", "role",
        "doctor_status_display", "title",
        "doctor_approval_requested_at", "doctor_approved_at",
    )
    list_filter  = (DoctorApprovalFilter, "role")
    search_fields = ("display_name", "user__username", "user__email", "title")
    list_select_related = ("user",)
    readonly_fields = (
        "doctor_approval_requested_at", "doctor_approved_at", "profile_slug"
    )
    actions = ["approve_doctors", "reject_doctors"]

    fieldsets = (
        ("Kullanıcı & Rol", {
            "fields": ("user", "role"),
        }),
        ("Doktor Onay Sistemi", {
            "fields": (
                "doctor_approved",
                "doctor_approval_requested_at",
                "doctor_approved_at",
                "doctor_rejection_reason",
            ),
            "description": (
                "role=Doktor seçili kullanıcılar için geçerlidir. "
                "doctor_approved=True yapılmadan forum'da doktor rozeti çıkmaz "
                "ve JSON-LD'de Person schema gönderilmez."
            ),
        }),
        ("Doktor Profil Bilgisi", {
            "fields": (
                "display_name", "title", "bio",
                "profile_slug", "avatar_url",
                "website", "sameAs_urls",
            ),
            "classes": ("collapse",),
            "description": "Yalnızca onaylı doktorlar için doldurun.",
        }),
    )

    @admin.display(description="E-posta")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Durum")
    def doctor_status_display(self, obj):
        if obj.role != "doctor":
            return format_html('<span style="color:#6b7280">—</span>')
        if obj.doctor_approved:
            return format_html('<span style="color:#16a34a;font-weight:700">✓ Onaylı</span>')
        if obj.doctor_rejection_reason:
            return format_html('<span style="color:#dc2626;font-weight:700">✗ Reddedildi</span>')
        return format_html('<span style="color:#d97706;font-weight:700">⏳ Bekliyor</span>')

    @admin.display(description="Ad")
    def get_display_name(self, obj):
        return obj.get_display_name()

    # ── Bulk actions ──────────────────────────────────────────────────────────

    @admin.action(description="✓ Seçilen doktorları onayla")
    def approve_doctors(self, request, queryset):
        updated = 0
        for profile in queryset.filter(role="doctor"):
            profile.doctor_approved = True
            profile.doctor_rejection_reason = ""
            profile.save()
            updated += 1
        self.message_user(request, f"{updated} doktor onaylandı.")

    @admin.action(description="✗ Seçilen doktor başvurularını reddet")
    def reject_doctors(self, request, queryset):
        updated = 0
        for profile in queryset.filter(role="doctor", doctor_approved=False):
            profile.doctor_rejection_reason = "Admin tarafından reddedildi."
            profile.save()
            updated += 1
        self.message_user(request, f"{updated} başvuru reddedildi.")


# ── User admin — inline profile ───────────────────────────────────────────────
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "Forum Profili"
    fields = (
        "role", "doctor_approved", "doctor_rejection_reason",
        "display_name", "title", "avatar_url",
    )
    readonly_fields = ("doctor_approval_requested_at",)


class UserAdmin(BaseUserAdmin):
    inlines = (*BaseUserAdmin.inlines, UserProfileInline)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)