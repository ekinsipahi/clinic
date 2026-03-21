"""
accounts/models.py

UserProfile — Django User extend
──────────────────────────────────────────────────────────────────────────────
Roller ve Onay Akışı:
  patient  → normal kayıt, hemen aktif
  doctor   → kayıt olur ama doctor_approved=False; admin onaylayana kadar
             is_doctor=False, JSON-LD'de Person çıkmaz, forum'da rozet gözükmez
  admin    → sadece yönetim

Doktor onay akışı:
  1. Kullanıcı kayıt olur, role='doctor' seçer
  2. doctor_approved=False → admin panelde "Onay Bekliyor" görünür
  3. Admin doctor_approved=True yapar → artık aktif doktor
  4. Opsiyonel: onay e-postası (signals.py'da tanımlanabilir)
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class UserProfile(models.Model):

    ROLE_CHOICES = [
        ("patient", "Hasta / Kullanıcı"),
        ("doctor",  "Doktor"),
        ("admin",   "Yönetici"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="patient",
        db_index=True
    )

    # ── Doktor Onay Sistemi ───────────────────────────────────────────────────
    doctor_approved = models.BooleanField(
        default=False,
        help_text=(
            "Doktor onayı. Yalnızca admin True yapabilir. "
            "False iken forum'da doktor rozeti ve JSON-LD Person çıkmaz."
        )
    )
    doctor_approval_requested_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Doktor onayı talep tarihi (otomatik)"
    )
    doctor_approved_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Onay tarihi (otomatik)"
    )
    doctor_rejection_reason = models.TextField(
        blank=True,
        help_text="Red sebebi (admin doldurur, kullanıcıya gösterilebilir)"
    )

    # ── Doktor Profil Bilgisi ─────────────────────────────────────────────────
    display_name = models.CharField(
        max_length=150, blank=True,
        help_text="Forum'da görünen ad. Doktorlar için 'Dr. Ad Soyad'"
    )
    title = models.CharField(
        max_length=150, blank=True,
        help_text="Ortodontist, Endodontist, Genel Diş Hekimi..."
    )
    bio = models.TextField(
        blank=True,
        help_text="Doktor profil açıklaması (JSON-LD'de kullanılır)"
    )
    profile_slug = models.SlugField(
        max_length=200, unique=True, blank=True, null=True,
        help_text="Doktor profil URL: /doktor/<slug>/"
    )
    # Google Knowledge Graph, Healthgrades, LinkedIn vb.
    sameAs_urls = models.TextField(
        blank=True,
        help_text="JSON-LD sameAs linkleri — her satıra bir URL"
    )

    # ── Görsel ────────────────────────────────────────────────────────────────
    avatar_url = models.URLField(
        blank=True,
        help_text="Profil fotoğrafı CDN URL"
    )

    # ── İletişim ──────────────────────────────────────────────────────────────
    website = models.URLField(blank=True)

    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"
        indexes = [
            models.Index(fields=["role", "doctor_approved"]),
        ]

    def __str__(self):
        status = ""
        if self.role == "doctor":
            status = " ✓" if self.doctor_approved else " ⏳"
        return f"{self.get_display_name()} [{self.get_role_display()}{status}]"

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_doctor(self) -> bool:
        """
        Gerçek doktor kontrolü: rol=doctor VE admin onaylı.
        Bu property JSON-LD ve forum rozetinde kullanılır.
        """
        return self.role == "doctor" and self.doctor_approved

    @property
    def is_pending_doctor(self) -> bool:
        """Onay bekleyen doktor başvurusu."""
        return self.role == "doctor" and not self.doctor_approved

    @property
    def is_patient(self) -> bool:
        return self.role == "patient"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_display_name(self) -> str:
        return self.display_name or self.user.get_full_name() or self.user.username

    def get_sameAs_list(self) -> list:
        return [u.strip() for u in self.sameAs_urls.splitlines() if u.strip()]

    def get_schema_person(self, base_url: str = "") -> dict:
        """
        JSON-LD Person object.
        Sadece is_doctor=True (approved) iken çağrılmalı.
        """
        data = {
            "@type": "Person",
            "name": self.get_display_name(),
        }
        if self.title:
            data["jobTitle"] = self.title
        if self.bio:
            data["description"] = self.bio[:200]
        if self.avatar_url:
            data["image"] = self.avatar_url
        if self.profile_slug:
            data["url"] = f"{base_url}/doktor/{self.profile_slug}/"
        elif self.website:
            data["url"] = self.website
        same = self.get_sameAs_list()
        if same:
            data["sameAs"] = same
        return data

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        from django.utils import timezone

        # Doktor başvurusu ilk kez yapılıyorsa tarihi kaydet
        if self.role == "doctor" and not self.doctor_approval_requested_at:
            self.doctor_approval_requested_at = timezone.now()

        # Onay verildiyse tarihi otomatik kaydet
        if self.doctor_approved and not self.doctor_approved_at:
            self.doctor_approved_at = timezone.now()

        # Onay kaldırıldıysa tarihi sıfırla
        if not self.doctor_approved:
            self.doctor_approved_at = None

        # Approved doktor için slug oluştur
        if self.is_doctor and not self.profile_slug:
            base = slugify(self.get_display_name())
            slug, i = base, 1
            while UserProfile.objects.filter(
                profile_slug=slug
            ).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"; i += 1
            self.profile_slug = slug

        super().save(*args, **kwargs)