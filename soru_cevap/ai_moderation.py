"""
soru_cevap/ai_moderation.py
GPT-4.1-nano ile otomatik yorum/soru moderasyonu.

Kullanım:
    from .ai_moderation import auto_moderate
    result = auto_moderate(text, content_type='comment')  # 'comment' | 'question'
    # result → 'approved' | 'pending' | 'rejected'
"""

import json
import logging
from functools import lru_cache

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# settings.py'de tanımla:
#   OPENAI_API_KEY = "sk-..."
#   AI_MODERATION_ENABLED = True  (False yaparsan hepsi pending'e düşer)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL          = "gpt-4.1-nano"
TIMEOUT        = 8  # saniye — aşılırsa fallback pending


SYSTEM_PROMPT = """Sen bir diş kliniği forumunun moderatörüsün.
Sana gönderilen metin için sadece şu üç karardan birini ver:

- "approved"  → Normal soru/yorum, uygun, yayınlanabilir
- "rejected"  → Spam, reklam, hakaret, müstehcen, alakasız içerik
- "pending"   → Emin olamadım, insan moderatörüne ilet

SADECE bu JSON formatında cevap ver, başka hiçbir şey yazma:
{"decision": "approved"}
"""

USER_PROMPT_TEMPLATE = """İçerik türü: {content_type}
Metin:
\"\"\"
{text}
\"\"\"
"""


def auto_moderate(text: str, content_type: str = "comment") -> str:
    """
    text: moderasyona gönderilecek içerik
    content_type: 'comment' veya 'question'

    Döner: 'approved' | 'pending' | 'rejected'
    Herhangi bir hata durumunda 'pending' döner (güvenli fallback).
    """
    if not getattr(settings, "AI_MODERATION_ENABLED", False):
        return "pending"

    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("ai_moderation: OPENAI_API_KEY tanımlı değil, pending döndürülüyor.")
        return "pending"

    if not text or not text.strip():
        return "pending"

    payload = {
        "model": MODEL,
        "max_tokens": 30,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    content_type=content_type,
                    text=text[:1000],  # token tasarrufu için kırp
                ),
            },
        ],
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()
            data = json.loads(raw)
            decision = data.get("decision", "pending")
            if decision not in ("approved", "rejected", "pending"):
                decision = "pending"
            return decision

    except httpx.TimeoutException:
        logger.warning("ai_moderation: OpenAI timeout, pending döndürülüyor.")
        return "pending"

    except Exception as exc:
        logger.error("ai_moderation hatası: %s", exc, exc_info=True)
        return "pending"