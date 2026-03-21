"""
soru_cevap/models.py — v6 FIXED
Yenilikler v5 → v6:
  - ArticleTag: hashtag tarzı konu etiketleri
  - Article.tags: ManyToMany → ArticleTag
  - UserBehavior: session bazlı davranış takibi
      view / like / comment / question / rating + time_spent
  - RecommendationEngine: tag + davranış skoru üzerinden
      kullanıcıya özel makale önerisi
"""

import json
import re
from collections import Counter

from django.db import models
from django.db.models import Avg, Count, Q
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS  (değişmedi)
# ─────────────────────────────────────────────────────────────────────────────

def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    masked_local = local[:2] + "*" * max(3, len(local) - 2)
    parts = domain.rsplit(".", 1)
    if len(parts) == 2:
        dom, tld = parts
        masked_dom = "*" * max(3, len(dom) - 2) + dom[-2:]
        return f"{masked_local}@{masked_dom}.{tld}"
    return f"{masked_local}@***"


def _mask_name(name: str) -> str:
    if not name:
        return "Kullanıcı"
    parts = name.strip().split()
    first = parts[0]
    if len(parts) == 1:
        return first[:2] + "*" * max(3, len(first) - 2)
    last = parts[1]
    return first + " " + last[0] + "*" * max(3, len(last) - 1)


def _mask_identity(email: str, display_name: str) -> str:
    # Artık maskeleme yok — display_name direkt döner (username olarak kaydedilmiş)
    if display_name and display_name.strip():
        return display_name.strip()
    return "Kullanıcı"


def _extract_images_from_html(html: str) -> list:
    return re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)


def _get_author_schema(user, base_url: str = "") -> dict:
    if not user:
        return {"@type": "Organization", "name": "Diş Kliniği", "url": base_url or "https://example.com"}
    if user.is_superuser or user.is_staff:
        name = ""
        try:
            name = user.profile.display_name or user.get_full_name() or user.username
        except Exception:
            name = user.get_full_name() or user.username
        return {"@type": "Person", "name": name or user.username, "url": base_url or "https://example.com"}
    try:
        profile = user.profile
        if profile.is_doctor:
            return profile.get_schema_person(base_url)
    except Exception:
        pass
    return {"@type": "Organization", "name": "Diş Kliniği", "url": base_url or "https://example.com"}


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE TAG
# ─────────────────────────────────────────────────────────────────────────────

class ArticleTag(models.Model):
    """
    Hashtag tarzı konu etiketi.
    Örnek slug'lar: implant, laminat, kompozit, dis-teli, agri,
                   kanal-tedavisi, dis-eti, zirkonyum, beyazlatma
    icon: opsiyonel emoji — template'te pill gösterimi için
    language: "both" = TR ve EN sayfalarında göster
    order: admin'de sıralama
    """
    LANGUAGE_CHOICES = [("tr", "TR"), ("en", "EN"), ("both", "Her İkisi")]

    name     = models.CharField(max_length=80)
    slug     = models.SlugField(unique=True, max_length=100)
    icon     = models.CharField(max_length=8, blank=True, help_text="Emoji: 🦷")
    language = models.CharField(max_length=4, choices=LANGUAGE_CHOICES, default="both")
    order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name        = "Makale Etiketi"
        verbose_name_plural = "Makale Etiketleri"

    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE
# ─────────────────────────────────────────────────────────────────────────────

class Article(models.Model):

    LANGUAGE_CHOICES    = [("tr", "TR"), ("en", "EN")]
    SCHEMA_TYPE_CHOICES = [
        ("Article",        "Article"),
        ("BlogPosting",    "Blog Post"),
        ("MedicalWebPage", "Medical Web Page"),
    ]

    author       = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    title        = models.CharField(max_length=255)
    slug         = models.SlugField(unique=True, max_length=300)
    content      = models.TextField()
    language     = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="tr")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    updated_at   = models.DateTimeField(blank=True, null=True)

    # ── v6: Tag sistemi ──────────────────────────────────────────────────────
    tags = models.ManyToManyField(
        ArticleTag,
        blank=True,
        related_name="articles",
        verbose_name="Etiketler",
    )

    featured_image     = models.URLField(blank=True)
    featured_image_alt = models.CharField(max_length=200, blank=True)

    seo_title       = models.CharField(max_length=70,  blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    seo_keywords    = models.CharField(max_length=500, blank=True)
    canonical_url   = models.URLField(blank=True)

    schema_type      = models.CharField(max_length=50, choices=SCHEMA_TYPE_CHOICES, default="MedicalWebPage")
    json_ld_override = models.TextField(blank=True)

    translation = models.OneToOneField(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="translated_from",
    )

    view_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-published_at"]
        indexes  = [
            models.Index(fields=["language", "is_published", "published_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return f"[{self.language}] {self.title}"

    def get_absolute_url(self):
        prefix = '/question-and-answer' if self.language == 'en' else '/soru-cevap'
        return f'{prefix}/{self.slug}/'

    def get_alternate_url(self):
        t = getattr(self, "translation", None)
        if t:
            return t.get_absolute_url()
        try:
            return self.translated_from.get_absolute_url()
        except Exception:
            return None

    def get_seo_title(self) -> str:
        return self.seo_title or self.title

    def get_seo_description(self) -> str:
        if self.seo_description:
            return self.seo_description
        from django.utils.html import strip_tags
        return strip_tags(self.content)[:155] + "…"

    def get_image_url(self) -> str:
        if self.featured_image:
            return self.featured_image
        imgs = _extract_images_from_html(self.content)
        return imgs[0] if imgs else ""

    def get_all_image_urls(self) -> list:
        urls = []
        if self.featured_image:
            urls.append(self.featured_image)
        for url in _extract_images_from_html(self.content):
            if url not in urls:
                urls.append(url)
        return urls

    def get_avg_rating(self):
        r = self.comments.filter(
            status="approved", rating__isnull=False, parent__isnull=True
        ).aggregate(avg=Avg("rating"))["avg"]
        return round(r, 1) if r else None

    def get_rating_count(self) -> int:
        return self.comments.filter(
            status="approved", rating__isnull=False, parent__isnull=True
        ).count()

    def get_article_json_ld(self, request=None) -> str:
        if self.json_ld_override.strip():
            return self.json_ld_override

        base_url = request.build_absolute_uri("/")[:-1] if request else ""
        abs_url  = self.canonical_url or (base_url + self.get_absolute_url())

        data = {
            "@context": "https://schema.org",
            "@type":    self.schema_type,
            "headline": self.get_seo_title(),
            "description": self.get_seo_description(),
            "inLanguage": self.language,
            "url": abs_url,
            "mainEntityOfPage": {"@type": "WebPage", "@id": abs_url},
            "publisher": {
                "@type": "Organization",
                "name":  "Diş Kliniği",
                "url":   base_url or "https://example.com",
            },
            "author": _get_author_schema(self.author, base_url),
        }

        if self.published_at:
            data["datePublished"] = self.published_at.isoformat()
        if self.updated_at:
            data["dateModified"] = self.updated_at.isoformat()

        imgs = self.get_all_image_urls()
        if imgs:
            data["image"] = imgs if len(imgs) > 1 else imgs[0]

        avg   = self.get_avg_rating()
        count = self.get_rating_count()
        if avg and count:
            data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": avg, "reviewCount": count,
                "bestRating": 5, "worstRating": 1,
            }

        # v6: tags → JSON-LD keywords
        tag_names = list(self.tags.values_list("name", flat=True))
        if tag_names:
            data["keywords"] = ", ".join(tag_names)

        return json.dumps(data, ensure_ascii=False, indent=2)

    def get_faq_json_ld(self) -> str | None:
        qs = self.questions.filter(
            status="approved"
        ).exclude(answer="").exclude(answer__isnull=True).filter(
            answered_by__isnull=False
        ).select_related('answered_by__profile')[:15]

        doctor_qs = []
        for q in qs:
            ab = q.answered_by
            if not ab: continue
            if ab.is_superuser or ab.is_staff:
                doctor_qs.append(q); continue
            try:
                if ab.profile.is_doctor:
                    doctor_qs.append(q)
            except Exception:
                pass

        if not doctor_qs:
            return None

        from django.utils.html import strip_tags
        data = {
            "@context": "https://schema.org",
            "@type":    "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name":  q.title or q.text,
                    "acceptedAnswer": {"@type": "Answer", "text": strip_tags(q.answer)},
                }
                for q in doctor_qs
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def get_review_json_ld(self, base_url: str = "") -> str | None:
        reviews = self.comments.filter(
            status="approved", rating__isnull=False, parent__isnull=True
        ).order_by("-created_at")[:10]
        if not reviews:
            return None

        abs_url = self.canonical_url or (base_url + self.get_absolute_url())
        data = {
            "@context": "https://schema.org",
            "@type":    self.schema_type,
            "name":     self.get_seo_title(),
            "url":      abs_url,
            "review": [
                {
                    "@type": "Review",
                    "reviewRating": {
                        "@type": "Rating",
                        "ratingValue": r.rating, "bestRating": 5, "worstRating": 1,
                    },
                    "author": {"@type": "Person", "name": r.masked_identity},
                    "datePublished": r.created_at.date().isoformat(),
                    "reviewBody":    r.text[:500],
                }
                for r in reviews
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.slug:
            base = slugify(self.title)
            slug, i = base, 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"; i += 1
            self.slug = slug
        if not self.published_at and self.is_published:
            self.published_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION
# ─────────────────────────────────────────────────────────────────────────────

class Question(models.Model):

    LANGUAGE_CHOICES = [("tr", "TR"), ("en", "EN")]
    STATUS_CHOICES   = [
        ("pending",  "Beklemede"),
        ("approved", "Onaylandı"),
        ("rejected", "Reddedildi"),
    ]

    article  = models.ForeignKey(
        Article, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="questions",
    )
    language     = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="tr")
    user         = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    display_name = models.CharField(max_length=100, blank=True)
    email        = models.EmailField(blank=True)

    title = models.CharField(max_length=200, blank=True,
        help_text="Kısa konu başlığı. Boş bırakılırsa text truncate kullanılır.")
    text  = models.TextField()
    slug  = models.SlugField(max_length=300, blank=True, db_index=True)

    answer      = models.TextField(blank=True, null=True)
    answered_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="answered_questions",
    )
    answered_at = models.DateTimeField(null=True, blank=True)

    votes      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # v6.1: Kullanıcı fotoğraf ekleyebilir (URL bazlı — S3/CDN veya direct upload sonrası)
    image = models.TextField(blank=True, help_text="Opsiyonel: soruyla ilgili fotoğraf (base64 veya URL)")

    class Meta:
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["status", "language", "created_at"]),
            models.Index(fields=["article", "status"]),
        ]

    def __str__(self):
        return self.text[:80]

    @property
    def display_title(self) -> str:
        return self.title or (self.text[:70] + ("…" if len(self.text) > 70 else ""))

    @property
    def masked_identity(self) -> str:
        if self.user:
            try:
                name = (self.user.profile.display_name or '').strip()
                if name:
                    return name
            except Exception:
                pass
            username = (self.user.username or '').strip()
            if username:
                return username.split('@')[0] if '@' in username else username
        return (self.display_name or '').strip() or "Kullanıcı"

    def get_absolute_url(self):
        prefix = '/question-and-answer' if self.language == 'en' else '/soru-cevap'
        return f'{prefix}/soru/{self.pk}/{self.slug or "soru"}/'

    def is_answered_by_doctor(self) -> bool:
        if not self.answered_by or not self.answer:
            return False
        if self.answered_by.is_superuser or self.answered_by.is_staff:
            return True
        try:
            return self.answered_by.profile.is_doctor
        except Exception:
            return False

    def get_avg_rating(self):
        r = self.comments.filter(
            status="approved", rating__isnull=False, parent__isnull=True
        ).aggregate(avg=Avg("rating"))["avg"]
        return round(r, 1) if r else None

    def get_rating_count(self) -> int:
        return self.comments.filter(
            status="approved", rating__isnull=False, parent__isnull=True
        ).count()

    def get_json_ld(self, request=None) -> str | None:
        if not self.answer:
            return None
        if not self.is_answered_by_doctor():
            return None

        base_url = request.build_absolute_uri("/")[:-1] if request else ""
        abs_url  = base_url + self.get_absolute_url()

        from django.utils.html import strip_tags
        avg   = self.get_avg_rating()
        count = self.get_rating_count()

        accepted_answer = {
            "@type": "Answer",
            "text":  strip_tags(self.answer),
            "dateCreated": (
                self.answered_at.isoformat() if self.answered_at
                else self.created_at.isoformat()
            ),
            "upvoteCount": self.question_likes.count(),
            "author": _get_author_schema(self.answered_by, base_url),
        }
        if avg and count:
            accepted_answer["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": avg, "reviewCount": count,
                "bestRating": 5, "worstRating": 1,
            }

        main_entity = {
            "@type":       "Question",
            "name":        self.title or self.text,
            "dateCreated": self.created_at.isoformat(),
            "author":      {"@type": "Person", "name": self.masked_identity},
            "answerCount": 1,
            "upvoteCount": self.votes,
            "interactionStatistic": {
                "@type":                "InteractionCounter",
                "interactionType":      "https://schema.org/CommentAction",
                "userInteractionCount": self.comments.filter(status="approved").count(),
            },
            "acceptedAnswer": accepted_answer,
        }

        data = {
            "@context": "https://schema.org",
            "@type":    "QAPage",
            "name":     self.title or self.text,
            "url":      abs_url,
            "speakable": {
                "@type":       "SpeakableSpecification",
                "cssSelector": ["#doctor-answer", "#question-text"],
            },
            "mainEntity": main_entity,
        }

        if avg and count:
            data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": avg, "reviewCount": count,
                "bestRating": 5, "worstRating": 1,
            }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.slug:
            self.slug = slugify((self.title or self.text)[:100])
        if self.answer and not self.answered_at:
            self.answered_at = timezone.now()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# COMMENT
# ─────────────────────────────────────────────────────────────────────────────

class Comment(models.Model):

    STATUS_CHOICES = [
        ("pending",  "Beklemede"),
        ("approved", "Onaylandı"),
        ("rejected", "Reddedildi"),
    ]

    article  = models.ForeignKey(
        Article, null=True, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    question = models.ForeignKey(
        Question, null=True, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )

    user         = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    display_name = models.CharField(max_length=100, blank=True)
    email        = models.EmailField(blank=True)

    text   = models.TextField()
    rating = models.PositiveSmallIntegerField(null=True, blank=True,
        help_text="1–5 yıldız (article ve question root yorumlarında)")
    likes      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        ordering = ["created_at"]
        indexes  = [
            models.Index(fields=["article",  "status", "parent"]),
            models.Index(fields=["question", "status"]),
        ]

    def __str__(self):
        return f"Yorum → {self.article or self.question} | {self.text[:50]}"

    @property
    def masked_identity(self) -> str:
        if self.user:
            try:
                name = (self.user.profile.display_name or '').strip()
                if name:
                    return name
            except Exception:
                pass
            username = (self.user.username or '').strip()
            if username:
                return username.split('@')[0] if '@' in username else username
        return (self.display_name or '').strip() or "Kullanıcı"


    @property
    def filled_stars(self) -> range:
        return range(self.rating or 0)

    @property
    def empty_stars(self) -> range:
        return range(5 - (self.rating or 0))

    def get_approved_replies(self):
        return self.replies.filter(status="approved").order_by("created_at")


MAX_DEPTH = 4

def build_comment_tree(comments_qs):
    def _node(comment, depth=0):
        return {
            "comment":  comment,
            "depth":    min(depth, MAX_DEPTH),
            "children": [
                _node(r, depth + 1)
                for r in comment.replies.filter(status="approved").order_by("created_at")
            ],
        }
    return [_node(c) for c in comments_qs.order_by("created_at")]


# ─────────────────────────────────────────────────────────────────────────────
# LIKE / QUESTION LIKE
# ─────────────────────────────────────────────────────────────────────────────

class Like(models.Model):
    article     = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="likes")
    session_key = models.CharField(max_length=100, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("article", "session_key")]

    def __str__(self):
        return f"Like → '{self.article}' [{self.session_key[:8]}]"


class QuestionLike(models.Model):
    question    = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="question_likes")
    session_key = models.CharField(max_length=100, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("question", "session_key")]
        indexes = [models.Index(fields=["question", "session_key"])]

    def __str__(self):
        return f"QuestionLike → '{self.question}' [{self.session_key[:8]}]"


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=QuestionLike)
def _ql_save(sender, instance, created, **kwargs):
    if created:
        Question.objects.filter(pk=instance.question_id).update(votes=models.F('votes') + 1)

@receiver(post_delete, sender=QuestionLike)
def _ql_delete(sender, instance, **kwargs):
    Question.objects.filter(pk=instance.question_id).update(
        votes=models.Case(
            models.When(votes__gt=0, then=models.F('votes') - 1),
            default=models.Value(0),
            output_field=models.PositiveIntegerField(),
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# USER BEHAVIOR  — v6
# ─────────────────────────────────────────────────────────────────────────────

class UserBehavior(models.Model):
    """
    Session bazlı davranış kaydı. Her (session_key, article) çifti = 1 satır.

    Alanlar:
      view_count    — aynı makaleyi kaç kez açtı
      time_spent    — toplam saniye (JS AJAX ile birikimli gönderilir)
      liked         — makaleyi beğendi mi
      commented     — yorum yaptı mı
      asked_question — bu makaleye soru sordu mu
      avg_rating    — verdiği yorum rating'i
    """
    session_key    = models.CharField(max_length=100, db_index=True)
    article        = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="user_behaviors")

    view_count     = models.PositiveSmallIntegerField(default=0)
    time_spent     = models.PositiveIntegerField(default=0, help_text="Toplam saniye")
    liked          = models.BooleanField(default=False)
    commented      = models.BooleanField(default=False)
    asked_question = models.BooleanField(default=False)
    avg_rating     = models.FloatField(null=True, blank=True)

    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("session_key", "article")]
        indexes = [models.Index(fields=["session_key", "last_seen"])]
        verbose_name        = "Kullanıcı Davranışı"
        verbose_name_plural = "Kullanıcı Davranışları"

    def __str__(self):
        return f"[{self.session_key[:8]}] → {self.article} (v:{self.view_count} t:{self.time_spent}s)"

    # ── Helper'lar ────────────────────────────────────────────────────────────

    @classmethod
    def record_view(cls, session_key: str, article: "Article"):
        obj, created = cls.objects.get_or_create(
            session_key=session_key, article=article,
            defaults={"view_count": 1},
        )
        if not created:
            cls.objects.filter(pk=obj.pk).update(view_count=models.F("view_count") + 1)

    @classmethod
    def record_time(cls, session_key: str, article: "Article", seconds: int):
        """JS'den gelen süre (saniye) — maksimum 2 saat kabul edilir."""
        if seconds <= 0 or seconds > 7200:
            return
        obj, _ = cls.objects.get_or_create(
            session_key=session_key, article=article,
            defaults={"time_spent": seconds},
        )
        if not _:
            cls.objects.filter(pk=obj.pk).update(time_spent=models.F("time_spent") + seconds)

    @classmethod
    def record_like(cls, session_key: str, article: "Article", liked: bool = True):
        cls.objects.update_or_create(
            session_key=session_key, article=article,
            defaults={"liked": liked},
        )

    @classmethod
    def record_comment(cls, session_key: str, article: "Article", rating: float = None):
        defaults = {"commented": True}
        if rating is not None:
            defaults["avg_rating"] = rating
        cls.objects.update_or_create(
            session_key=session_key, article=article, defaults=defaults,
        )

    @classmethod
    def record_question(cls, session_key: str, article: "Article"):
        cls.objects.update_or_create(
            session_key=session_key, article=article,
            defaults={"asked_question": True},
        )


"""
RecommendationEngine v7 — Collaborative Filtering + Content-Based Hybrid
models.py içindeki RecommendationEngine sınıfıyla değiştirilecek bölüm.

Algoritma:
──────────
AŞAMA 1 — TAG İLGİ SKORU (content-based, v6'dan geliştirildi)
  Kullanıcının davranışlarından her tag için skor üretilir.
  Ağırlıklar artırıldı + decay faktörü eklendi (son görülen daha değerli).

AŞAMA 2 — BENZERLİK SKORU (collaborative filtering — YENİ)
  "Senin gibi okuyanlar şunları da okudu" mantığı:
  a) Kullanıcının liked/commented/asked ettiği makaleleri bul
  b) Aynı makalelerde etkileşim yapmış diğer session'ları bul
  c) Bu benzer kullanıcıların yoğun etkileşim yaptığı makaleleri al
  d) Jaccard benzerliği üzerinden skor hesapla

AŞAMA 3 — POPÜLERLIK BONUSU
  view_count + like_count + comment_count (onaylı)

FINAL SKOR = tag_score * 0.50 + collab_score * 0.35 + pop_bonus * 0.15

Soğuk başlangıç: hiç davranış yoksa → popülerlik bazlı fallback.
"""

from collections import Counter, defaultdict
from django.db import models
from django.db.models import Count, Q


class RecommendationEngine:
    # ── Ağırlıklar (content-based) ───────────────────────────────────────────
    W_TIME     = 0.04       # saniye başına (artırıldı)
    W_TIME_MAX = 6.0        # tavan
    W_VIEW     = 0.6
    W_VIEW_MAX = 4.0
    W_LIKE     = 5.0        # artırıldı
    W_COMMENT  = 4.0
    W_QUESTION = 4.0
    W_RATING   = 2.0        # artırıldı

    # ── Hybrid ağırlıklar ────────────────────────────────────────────────────
    ALPHA_CONTENT = 0.50    # content-based ağırlığı
    ALPHA_COLLAB  = 0.35    # collaborative ağırlığı
    ALPHA_POP     = 0.15    # popülerlik ağırlığı

    # ── Collaborative ayarlar ────────────────────────────────────────────────
    COLLAB_MIN_OVERLAP = 2  # benzer kullanıcıyla en az X ortak etkileşim
    COLLAB_TOP_USERS   = 30 # en benzer kaç kullanıcıya bakılacak
    COLLAB_CANDIDATE_POOL = 100  # collaborative adayları kaç makale havuzundan çekilecek

    @classmethod
    def _get_session_keys(cls, session_key: str, user_id: int = None) -> set:
        """Sorgulanacak session key setini döner."""
        keys = {session_key}
        if user_id:
            keys.add(f"user_{user_id}")
        return keys

    @classmethod
    def get_tag_interest(cls, session_key: str, user_id: int = None) -> dict:
        """
        {tag_id: float_skor} döner.
        Son etkileşimler daha ağırlıklı (son 7 gün = 1.5x, son 30 gün = 1.2x).
        """
        from .models import UserBehavior
        from django.utils import timezone
        import datetime

        keys = cls._get_session_keys(session_key, user_id)
        now  = timezone.now()

        behaviors = (
            UserBehavior.objects
            .filter(session_key__in=keys)
            .select_related("article")
            .prefetch_related("article__tags")
        )

        tag_scores: Counter = Counter()

        for beh in behaviors:
            # Zaman decay: son 7 gün = 1.5x, son 30 gün = 1.2x, daha eski = 1.0x
            age_days = (now - beh.last_seen).days
            if age_days <= 7:
                decay = 1.5
            elif age_days <= 30:
                decay = 1.2
            else:
                decay = 1.0

            score = 0.0
            score += min(beh.time_spent * cls.W_TIME,  cls.W_TIME_MAX)
            score += min(beh.view_count * cls.W_VIEW,  cls.W_VIEW_MAX)
            if beh.liked:          score += cls.W_LIKE
            if beh.commented:      score += cls.W_COMMENT
            if beh.asked_question: score += cls.W_QUESTION
            if beh.avg_rating:
                score += (beh.avg_rating - 2) * cls.W_RATING

            score *= decay

            if score <= 0:
                continue

            for tag in beh.article.tags.all():
                tag_scores[tag.pk] += score

        return dict(tag_scores)

    @classmethod
    def get_collaborative_scores(
        cls,
        session_key: str,
        language: str,
        exclude_pks: set,
        user_id: int = None,
    ) -> dict:
        """
        Collaborative filtering: {article_id: float_skor}

        "Senin gibi okuyanlar şunları da beğendi" mantığı:
        1. Kullanıcının etkileşimde bulunduğu makale setini çıkar
        2. Aynı makalelere etkileşim yapmış benzer session'ları bul
        3. Jaccard benzerliği hesapla
        4. Benzer kullanıcıların yoğun etkileşim yaptığı makaleleri topla
        """
        from .models import UserBehavior

        keys = cls._get_session_keys(session_key, user_id)

        # Bu kullanıcının etkileşimde olduğu makale ID'leri
        # "Etkileşim" = liked OR commented OR asked_question OR (time_spent > 60)
        user_engaged = set(
            UserBehavior.objects
            .filter(session_key__in=keys)
            .filter(
                Q(liked=True) | Q(commented=True) |
                Q(asked_question=True) | Q(time_spent__gte=60)
            )
            .values_list("article_id", flat=True)
        )

        if not user_engaged:
            return {}

        # Bu makalelerde etkileşim yapan diğer session'lar
        similar_sessions_qs = (
            UserBehavior.objects
            .filter(
                article_id__in=user_engaged,
            )
            .filter(
                Q(liked=True) | Q(commented=True) |
                Q(asked_question=True) | Q(time_spent__gte=60)
            )
            .exclude(session_key__in=keys)
            .values("session_key", "article_id")
        )

        # Her session'ın hangi makalelerle etkileşimde olduğunu grupla
        session_articles: dict = defaultdict(set)
        for row in similar_sessions_qs:
            session_articles[row["session_key"]].add(row["article_id"])

        if not session_articles:
            return {}

        # Jaccard benzerliği ile en benzer session'ları bul
        scored_sessions = []
        for sess_key, their_articles in session_articles.items():
            intersection = len(user_engaged & their_articles)
            if intersection < cls.COLLAB_MIN_OVERLAP:
                continue
            union = len(user_engaged | their_articles)
            jaccard = intersection / union if union > 0 else 0
            scored_sessions.append((jaccard, sess_key, their_articles))

        if not scored_sessions:
            return {}

        # En benzer TOP N kullanıcı
        scored_sessions.sort(key=lambda x: x[0], reverse=True)
        top_sessions = scored_sessions[:cls.COLLAB_TOP_USERS]

        # Bu benzer kullanıcıların etkileşimde olduğu makaleleri topla
        # Ağırlık: (jaccard_skoru * etkileşim_gücü)
        article_collab_scores: Counter = Counter()

        all_their_keys = {s[1] for s in top_sessions}
        their_behaviors = (
            UserBehavior.objects
            .filter(
                session_key__in=all_their_keys,
                article__language=language,
                article__is_published=True,
            )
            .filter(
                Q(liked=True) | Q(commented=True) |
                Q(asked_question=True) | Q(time_spent__gte=60)
            )
            .exclude(article_id__in=exclude_pks)
            .values("session_key", "article_id", "liked", "commented",
                    "asked_question", "time_spent", "view_count")
        )

        # jaccard skorunu session_key'e map'le
        session_jaccard = {s[1]: s[0] for s in top_sessions}

        for beh in their_behaviors:
            jaccard = session_jaccard.get(beh["session_key"], 0)
            if jaccard == 0:
                continue

            # Etkileşim gücü (basit)
            strength = 0.0
            if beh["liked"]:          strength += 3.0
            if beh["commented"]:      strength += 2.5
            if beh["asked_question"]: strength += 2.5
            strength += min(beh["time_spent"] * 0.02, 3.0)

            article_collab_scores[beh["article_id"]] += jaccard * strength

        return dict(article_collab_scores)

    @classmethod
    def recommend_articles(
        cls,
        session_key: str,
        language: str,
        exclude_pk: int = None,
        limit: int = 6,
        user_id: int = None,
    ) -> list:
        """
        Hybrid öneri: content-based + collaborative + popularity.
        exclude_pk: şu an okunan makale
        """
        from .models import Article, UserBehavior

        keys = cls._get_session_keys(session_key, user_id)

        # 2+ kez görülen makaleleri çıkar
        seen_pks = set(
            UserBehavior.objects.filter(
                session_key__in=keys,
                view_count__gte=2,
            ).values_list("article_id", flat=True)
        )
        if exclude_pk:
            seen_pks.add(exclude_pk)

        base_qs = Article.objects.filter(
            language=language, is_published=True,
        ).exclude(pk__in=seen_pks).prefetch_related("tags")

        # ── Soğuk başlangıç ──────────────────────────────────────────────────
        tag_interest = cls.get_tag_interest(session_key, user_id=user_id)
        if not tag_interest:
            return list(base_qs.order_by("-view_count")[:limit])

        # ── Content-based skorlar ─────────────────────────────────────────────
        candidates = list(base_qs[:120])

        content_scores: dict = {}
        for art in candidates:
            art_tag_ids = set(art.tags.values_list("pk", flat=True))
            tag_sc = sum(tag_interest.get(tid, 0) for tid in art_tag_ids)
            if tag_sc > 0:
                content_scores[art.pk] = tag_sc

        # ── Collaborative skorlar ─────────────────────────────────────────────
        collab_scores = cls.get_collaborative_scores(
            session_key=session_key,
            language=language,
            exclude_pks=seen_pks,
            user_id=user_id,
        )

        # ── Tüm aday makale ID'lerini birleştir ───────────────────────────────
        all_candidate_pks = set(content_scores.keys()) | set(collab_scores.keys())
        if not all_candidate_pks:
            return list(base_qs.order_by("-view_count")[:limit])

        # Popülerlik verisini tek sorguda çek
        pop_data = (
            Article.objects
            .filter(pk__in=all_candidate_pks)
            .annotate(
                like_count=Count("likes"),
                comment_count=Count("comments", filter=Q(comments__status="approved")),
            )
            .values("pk", "view_count", "like_count", "comment_count")
        )
        pop_map = {row["pk"]: row for row in pop_data}

        # ── Final skor ────────────────────────────────────────────────────────
        # Normalize etmek için max değerleri bul
        max_content = max(content_scores.values(), default=1) or 1
        max_collab  = max(collab_scores.values(),  default=1) or 1

        scored = []
        for pk in all_candidate_pks:
            c_norm    = (content_scores.get(pk, 0) / max_content)
            col_norm  = (collab_scores.get(pk, 0)  / max_collab)

            pop_row   = pop_map.get(pk, {})
            pop_raw   = (
                (pop_row.get("view_count", 0) or 0) * 0.01 +
                (pop_row.get("like_count", 0) or 0) * 0.5 +
                (pop_row.get("comment_count", 0) or 0) * 0.3
            )
            # Pop normalizasyonu — soft cap
            pop_norm = pop_raw / (pop_raw + 50)

            final = (
                cls.ALPHA_CONTENT * c_norm +
                cls.ALPHA_COLLAB  * col_norm +
                cls.ALPHA_POP     * pop_norm
            )
            scored.append((final, pk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_pks = [pk for _, pk in scored[:limit]]

        # DB'den makale nesnelerini çek (sırayı koru)
        articles_map = {
            a.pk: a for a in
            Article.objects.filter(pk__in=top_pks).prefetch_related("tags")
        }
        result = [articles_map[pk] for pk in top_pks if pk in articles_map]

        # Yeterli sonuç yoksa popülerlikle tamamla
        if len(result) < limit:
            existing_pks = {a.pk for a in result} | seen_pks
            fallback = list(
                base_qs.exclude(pk__in=existing_pks)
                .order_by("-view_count")[: limit - len(result)]
            )
            result.extend(fallback)

        return result

    @classmethod
    def get_interest_tags(cls, session_key: str, top_n: int = 5, user_id: int = None) -> list:
        """
        Kullanıcının en çok ilgi duyduğu üst N tag nesnesini döner.
        """
        from .models import ArticleTag

        tag_interest = cls.get_tag_interest(session_key, user_id=user_id)
        if not tag_interest:
            return []
        sorted_tags = sorted(tag_interest.items(), key=lambda x: x[1], reverse=True)
        top_ids = [pk for pk, _ in sorted_tags[:top_n]]
        tags    = {t.pk: t for t in ArticleTag.objects.filter(pk__in=top_ids)}
        return [tags[pk] for pk in top_ids if pk in tags]

    @classmethod
    def get_recommendation_reason(
        cls,
        session_key: str,
        article,
        language: str,
        user_id: int = None,
    ) -> str:
        """
        Bir makalenin neden önerildiğini açıklayan kısa string döner.
        Template'te pill olarak gösterilir.
        TR/EN dil desteği.

        Dönen değerler:
          "benzer_kullanici"  → Benzer kullanıcılar okudu
          "ilgi_alani"        → İlgi alanınla eşleşiyor
          "populer"           → Popüler içerik
        """
        keys = cls._get_session_keys(session_key, user_id)

        tag_interest = cls.get_tag_interest(session_key, user_id=user_id)
        art_tag_ids  = set(article.tags.values_list("pk", flat=True))
        has_tag_match = bool(art_tag_ids & set(tag_interest.keys()))

        from .models import UserBehavior
        from django.db.models import Q

        user_engaged = set(
            UserBehavior.objects
            .filter(session_key__in=keys)
            .filter(Q(liked=True) | Q(commented=True) | Q(time_spent__gte=60))
            .values_list("article_id", flat=True)
        )
        collab_match = False
        if user_engaged:
            similar_count = (
                UserBehavior.objects
                .filter(article_id__in=user_engaged)
                .filter(Q(liked=True) | Q(commented=True) | Q(time_spent__gte=60))
                .exclude(session_key__in=keys)
                .filter(
                    session_key__in=UserBehavior.objects
                    .filter(article=article)
                    .values("session_key")
                )
                .values("session_key").distinct().count()
            )
            collab_match = similar_count >= cls.COLLAB_MIN_OVERLAP

        if collab_match:
            return "benzer_kullanici"
        if has_tag_match:
            return "ilgi_alani"
        return "populer"
