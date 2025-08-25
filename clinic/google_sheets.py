# sheets_conversions.py
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "sheets-service-account-key.json"

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES,
)
client = gspread.authorize(credentials)

HEADERS = ["Conversion_Time", "Hashed_Phone_Number", "Conversion_Value", "Conversion_Currency"]

# ---------- helpers ----------
def _normalize_tr_phone(p: str) -> str:
    if not p:
        return ""
    digits = "".join(ch for ch in p if ch.isdigit())
    if not digits:
        return ""
    # TR kuralları:
    # +90xxx -> bırak; 90xxxxx -> +90xxxxx; 0xxxxxxxxx -> +90xxxxxxxxx
    if p.strip().startswith("+90"):
        return f"+{digits}"
    if digits.startswith("90"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+90{digits[1:]}"
    if len(digits) == 10:
        return f"+90{digits}"
    return f"+{digits}"

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest() if s else ""

def _rfc3339_istanbul(dt: datetime | None) -> str:
    tz = ZoneInfo("Europe/Istanbul")
    x = (dt or datetime.now(tz)).astimezone(tz)
    return x.isoformat(timespec="seconds")  # "YYYY-MM-DDTHH:MM:SS+03:00"

def _parse_rfc3339(s: str) -> datetime | None:
    try:
        # Python 3.11+: datetime.fromisoformat destekli (offset’li)
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _ensure_headers(ws):
    values = ws.get_all_values()
    if not values:
        ws.append_row(HEADERS, value_input_option="USER_ENTERED")
        return
    first = values[0]
    if first != HEADERS:
        # İstersen burada otomatik düzeltme yapabilirsin; şimdilik zorunlu başlık bekleyelim:
        # ws.update('A1', [HEADERS])  # başlıkları zorla güncelle
        pass

# ---------- main ----------
def push_conversion_row(sheet_id: str,
                        phone_raw: str,
                        when_dt: datetime | None = None,
                        value: float = 0.0,
                        currency: str = "TRY",
                        dedupe_window_minutes: int = 1440) -> bool:
    """
    GCLID olmayan senaryo için satır ekler.
    - phone_raw -> E.164 normalize -> SHA-256 hash
    - when_dt -> RFC3339 (Europe/Istanbul)
    - Dedupe: aynı hashed_phone + (when_dt +/- pencere) varsa ekleme
    Dönüş: True (eklendi) / False (eklenmedi)
    """
    ws = client.open_by_key(sheet_id).sheet1
    _ensure_headers(ws)

    phone_e164 = _normalize_tr_phone(phone_raw)
    hashed_phone = _sha256_hex(phone_e164)
    conv_time = _rfc3339_istanbul(when_dt)

    # Dedupe: sadece gerekli kolonları çek
    # get_all_records() ile dict listesi çekmek kolay:
    records = ws.get_all_records()  # [{Conversion_Time: ..., Hashed_Phone_Number: ...}, ...]
    if hashed_phone:
        try:
            # Zaman penceresi
            target_dt = _parse_rfc3339(conv_time)
            lo = target_dt - timedelta(minutes=dedupe_window_minutes) if target_dt else None
            hi = target_dt + timedelta(minutes=dedupe_window_minutes) if target_dt else None

            for row in records:
                if row.get("Hashed_Phone_Number") == hashed_phone:
                    existing_ts = _parse_rfc3339(row.get("Conversion_Time", ""))
                    if existing_ts and target_dt:
                        if lo <= existing_ts <= hi:
                            # Aynı hash aynı gün/pencerede var → yazma
                            return False
        except Exception:
            # Her ihtimale karşı dedupla başaramazsak, yazmaya devam edelim
            pass

    # Satırı yaz
    ws.append_row([conv_time, hashed_phone, value, currency],
                  value_input_option="USER_ENTERED")
    return True
