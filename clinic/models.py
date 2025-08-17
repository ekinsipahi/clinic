from django.db import models
from django.utils import timezone
from conversion_tracking.models import Conversion  # Conversion modeli ile aynı dosyada değilse

class CallMeLead(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    gclid = models.CharField(max_length=255, blank=True, null=True)
    client_info = models.JSONField(null=True, blank=True)
    page = models.CharField(max_length=255, blank=True, default="Ana Sayfa")
    created_at = models.DateTimeField(auto_now_add=True)
    convert_to_conversion = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.convert_to_conversion and not Conversion.objects.filter(gclid=self.gclid).exists():
            Conversion.objects.create(
                phone_number=self.phone,
                gclid=self.gclid,
                conversion_name="CallMeLead",
                is_qualified=True,
                is_converted=False,
                qualification_time=timezone.now(),
                client_info=self.client_info,
                page="Beni Ara Lead"
            )

    def __str__(self):
        return f"{self.name} - {self.phone}"


class ArrivalConfirmation(models.Model):
    full_name = models.CharField(max_length=120, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Reklam kimliği (şimdilik gclid; istersen wbraid/gbraid ekleyebiliriz)
    gclid = models.CharField(max_length=255, blank=True, null=True)

    # Tarayıcıdan gelen ham JSON (device, fingerprint vs.)
    client_info = models.JSONField(null=True, blank=True)

    page = models.CharField(max_length=255, blank=True, default="Manuel Onay")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Admin tek tuş için:
    convert_to_conversion = models.BooleanField(default=False)

    # Bağlanan conversion’ı tut (tekrar oluşturmayı engeller)
    matched_conversion = models.ForeignKey(
        Conversion, on_delete=models.SET_NULL, null=True, blank=True, related_name="arrivals"
    )
    converted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["gclid"]),
        ]

    def __str__(self):
        who = self.full_name or self.phone or "—"
        return f"Arrival {self.created_at:%Y-%m-%d %H:%M} | {who}"

    # ---- helpers ----
    @staticmethod
    def _normalize_tr_phone(p: str) -> str:
        if not p:
            return ""
        v = "".join(ch for ch in p if ch.isdigit() or ch == "+")
        if v.startswith("0"):
            v = "+9" + v              # 0XXXXXXXXXX -> +90XXXXXXXXXX
        if not v.startswith("+") and len(v) == 10:
            v = "+90" + v             # 5XXXXXXXXX -> +905XXXXXXXXX
        return v

    def _find_existing_conversion(self):
        """
        Önce gclid ile; yoksa normalize telefonla (son 30 gün en yeni) bir Conversion bul.
        """
        # 1) gclid
        if self.gclid:
            conv = Conversion.objects.filter(gclid=self.gclid).order_by("-timestamp").first()
            if conv:
                return conv

        # 2) phone (opsiyonel)
        phone = self._normalize_tr_phone(self.phone or "")
        if phone:
            cutoff = timezone.now() - timezone.timedelta(days=30)
            conv = (Conversion.objects
                    .filter(phone_number=phone, timestamp__gte=cutoff)
                    .order_by("-timestamp").first())
            if conv:
                return conv
        return None

    def convert(self, *, conversion_name: str = "ArrivalConfirmation", value: float = 0.0):
        """
        Tek tuşla dönüşüm:
        - Mevcut Conversion varsa günceller
        - Yoksa oluşturur
        - is_qualified=True, conversion_time'e dokunmayız (arama vs. ayrı)
        """
        now = timezone.now()

        # Zaten eşleşmişse onu kullan
        conv = self.matched_conversion or self._find_existing_conversion()
        created = False

        if not conv:
            conv = Conversion(
                page=self.page or "Manuel Onay",
                conversion_name=conversion_name,
                conversion_value=value,
                currency="TRY",
                gclid=(self.gclid or None),
                phone_number=(self._normalize_tr_phone(self.phone or "") or None),
                client_info=(self.client_info or {}),
            )
            created = True
        else:
            # Alanları doldur/güncelle (boş olanları tamamla, çakışanı ezme)
            if not conv.gclid and self.gclid:
                conv.gclid = self.gclid
            if not conv.phone_number and self.phone:
                conv.phone_number = self._normalize_tr_phone(self.phone)
            # client_info merge (mevcut bozulmasın)
            base = conv.client_info or {}
            newc = self.client_info or {}
            if isinstance(base, dict) and isinstance(newc, dict):
                base.update({k: v for k, v in newc.items() if k not in base})
                conv.client_info = base

        # Flags
        conv.is_qualified = True
        if not conv.qualification_time:
            conv.qualification_time = now
        if not conv.page:
            conv.page = self.page or "Manuel Onay"

        conv.save()

        # Arrival işaretleri
        self.matched_conversion = conv
        self.converted_at = now
        # Tekrarı önlemek için checkbox’ı geri düşürelim
        self.convert_to_conversion = False
        super().save(update_fields=["matched_conversion", "converted_at", "convert_to_conversion"])

        return conv, created

    def save(self, *args, **kwargs):
        """
        Admin'de 'convert_to_conversion' işaretlenip kaydedilince otomatik dönüştür.
        """
        super().save(*args, **kwargs)
        if self.convert_to_conversion and not self.matched_conversion:
            # Dönüştür ve checkbox'ı kapat
            self.convert()
