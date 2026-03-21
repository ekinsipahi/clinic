"""
soru_cevap/admin.py — v8
Tag seçiminde dil bazlı gruplama:
  - TR makalede → sadece TR tag'ler gösterilir, başlık "🇹🇷 Türkçe Etiketler"
  - EN makalede → sadece EN tag'ler gösterilir, başlık "🇬🇧 English Tags"
  - Yeni kayıt / dil seçilmemiş → iki grup da gösterilir, her biri ayrı başlıklı
  - ValidationError: yanlış dil tag'i eklenirse hata fırlar
"""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html, mark_safe
from django.db.models import Avg

from .models import Article, Question, Comment, Like, ArticleTag, UserBehavior


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM GROUPED TAG WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class GroupedTagWidget(forms.CheckboxSelectMultiple):
    """
    Tag'leri dile göre iki sütun halinde gruplar.
    article_language: 'tr', 'en', veya None (her ikisini göster)
    """

    def __init__(self, *args, article_language=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.article_language = article_language

    def render(self, name, value, attrs=None, renderer=None):
        queryset = list(self.choices.queryset) if hasattr(self.choices, 'queryset') else []

        lang = self.article_language

        if lang == 'tr':
            sections = [('tr', '🇹🇷 Türkçe Etiketler')]
        elif lang == 'en':
            sections = [('en', '🇬🇧 English Tags')]
        else:
            sections = [
                ('tr', '🇹🇷 Türkçe Etiketler'),
                ('en', '🇬🇧 English Tags'),
            ]

        if value is None:
            value = []
        str_values = [str(v) for v in value]

        html_parts = ['<div style="display:flex;gap:40px;flex-wrap:wrap;padding:8px 0;">']

        for lang_code, section_label in sections:
            filtered = [t for t in queryset if t.language == lang_code]
            if not filtered:
                continue

            html_parts.append(
                f'<div style="min-width:200px;">'
                f'<p style="font-weight:700;font-size:12px;margin:0 0 8px 0;'
                f'color:#888;text-transform:uppercase;letter-spacing:.05em;'
                f'border-bottom:2px solid #e5e7eb;padding-bottom:6px;">'
                f'{section_label}</p>'
                f'<ul style="list-style:none;margin:0;padding:0;">'
            )
            for tag in filtered:
                checked = 'checked' if str(tag.pk) in str_values else ''
                label_text = f"{tag.icon} {tag.name}" if tag.icon else tag.name
                html_parts.append(
                    f'<li style="margin:5px 0;">'
                    f'<label style="cursor:pointer;display:flex;align-items:center;'
                    f'gap:7px;font-size:13px;color:#374151;">'
                    f'<input type="checkbox" name="{name}" value="{tag.pk}" {checked} '
                    f'style="cursor:pointer;width:15px;height:15px;"> {label_text}'
                    f'</label></li>'
                )
            html_parts.append('</ul></div>')

        html_parts.append('</div>')
        return mark_safe(''.join(html_parts))


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE ADMIN FORM
# ─────────────────────────────────────────────────────────────────────────────

class ArticleAdminForm(forms.ModelForm):

    class Meta:
        model  = Article
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")
        lang     = None

        if instance and instance.pk:
            lang = instance.language
        elif "data" in kwargs and kwargs["data"].get("language"):
            lang = kwargs["data"].get("language")

        # Queryset: dile göre filtrele
        if lang in ("tr", "en"):
            tag_qs = ArticleTag.objects.filter(language=lang).order_by("order", "name")
        else:
            tag_qs = ArticleTag.objects.all().order_by("language", "order", "name")

        widget = GroupedTagWidget(article_language=lang)
        self.fields["tags"].queryset = tag_qs
        self.fields["tags"].widget   = widget
        # choices'ı queryset'e bağla
        self.fields["tags"].widget.choices = self.fields["tags"].choices

    def clean(self):
        cleaned = super().clean()
        lang    = cleaned.get("language")
        tags    = cleaned.get("tags")

        if not lang or not tags:
            return cleaned

        invalid_tags = []
        for tag in tags:
            if tag.language != lang:
                invalid_tags.append(f'"{tag.icon or ""} {tag.name}" ({tag.language.upper()})')

        if invalid_tags:
            raise ValidationError(
                f"Dil uyumsuzluğu: Aşağıdaki etiket(ler) bu makalenin diliyle "
                f"({lang.upper()}) uyuşmuyor — {', '.join(invalid_tags)}. "
                f"Lütfen yalnızca {lang.upper()} etiketleri kullanın."
            )

        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE TAG
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):
    list_display        = ("icon", "name", "slug", "language", "article_count_display", "order")
    list_editable       = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields       = ("name", "slug")
    list_filter         = ("language",)
    ordering            = ("language", "order", "name")

    @admin.display(description="Makale Sayısı")
    def article_count_display(self, obj):
        return obj.articles.count()


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):

    form = ArticleAdminForm  # filter_horizontal kaldırıldı, widget hallediyor

    list_display  = (
        "featured_image_preview", "title", "language",
        "is_published", "view_count",
        "tag_display",
        "avg_rating_display", "published_at",
    )
    list_filter         = ("language", "is_published", "schema_type", "tags")
    search_fields       = ("title", "slug", "seo_title", "seo_keywords")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = True
    date_hierarchy      = "published_at"
    save_on_top         = True

    fieldsets = (
        ("İçerik", {
            "fields": ("author", "title", "slug", "language", "is_published", "content")
        }),
        ("Etiketler", {
            "fields": ("tags",),
            "description": (
                "Makale diline göre etiketler gruplanmış olarak gösterilir. "
                "Her makaleye en az 1–3 etiket ekleyin."
            ),
        }),
        ("Görsel", {
            "fields": ("featured_image", "featured_image_alt"),
        }),
        ("SEO", {
            "fields": ("seo_title", "seo_description", "seo_keywords", "canonical_url"),
        }),
        ("Schema / JSON-LD", {
            "fields": ("schema_type", "json_ld_override"),
            "classes": ("collapse",),
        }),
        ("Çeviri", {
            "fields": ("translation",),
            "classes": ("collapse",),
        }),
        ("Zaman", {
            "fields": ("published_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("updated_at", "view_count")

    @admin.display(description="Fotoğraf")
    def featured_image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="height:40px;width:60px;object-fit:cover;border-radius:4px">',
                obj.featured_image
            )
        return "-"

    @admin.display(description="Etiketler")
    def tag_display(self, obj):
        tags = obj.tags.all()[:3]
        if not tags:
            return format_html('<span style="color:#94a3b8;">—</span>')
        pills = " ".join(
            f'<span style="display:inline-block;padding:1px 6px;border-radius:999px;'
            f'font-size:11px;background:rgba(16,185,129,.12);color:#10b981;'
            f'border:1px solid rgba(16,185,129,.2);">{t.icon or ""} {t.name}</span>'
            for t in tags
        )
        return format_html(pills)

    @admin.display(description="Puan")
    def avg_rating_display(self, obj):
        avg = obj.comments.filter(
            status="approved", rating__isnull=False
        ).aggregate(avg=Avg("rating"))["avg"]
        if avg is None:
            return "-"
        avg_f = float(avg)
        stars = "★" * round(avg_f) + "☆" * (5 - round(avg_f))
        return format_html('<span title="{}/5">{}</span>', f"{avg_f:.1f}", stars)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):

    list_display  = (
        "short_text", "language", "article",
        "masked_identity_display",
        "answered_by", "has_answer",
        "votes", "status", "created_at",
    )
    list_filter         = ("status", "language", "article")
    search_fields       = ("text", "display_name", "email")
    list_select_related = ("article", "user", "answered_by")
    list_editable       = ("status",)
    date_hierarchy      = "created_at"
    save_on_top         = True

    fieldsets = (
        ("Soru", {
            "fields": ("article", "language", "text", "votes", "status")
        }),
        ("Cevap", {
            "fields": ("answer", "answered_by", "answered_at"),
        }),
        ("Gönderen", {
            "fields": ("user", "display_name", "email"),
        }),
    )
    readonly_fields = ("created_at", "slug")

    @admin.display(description="Soru")
    def short_text(self, obj):
        return obj.text[:70] + ("..." if len(obj.text) > 70 else "")

    @admin.display(description="Kimlik")
    def masked_identity_display(self, obj):
        return obj.masked_identity

    @admin.display(description="Cevap?", boolean=True)
    def has_answer(self, obj):
        return bool(obj.answer)


# ─────────────────────────────────────────────────────────────────────────────
# COMMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):

    list_display  = (
        "short_text", "target_display",
        "masked_identity_display",
        "rating_stars_display",
        "likes", "status", "created_at",
    )
    list_filter         = ("status", "rating")
    search_fields       = ("text", "display_name", "email")
    list_select_related = ("article", "question", "user")
    list_editable       = ("status",)
    date_hierarchy      = "created_at"
    readonly_fields     = ("created_at", "likes")

    @admin.display(description="Yorum")
    def short_text(self, obj):
        return obj.text[:60] + ("..." if len(obj.text) > 60 else "")

    @admin.display(description="Hedef")
    def target_display(self, obj):
        if obj.article:
            return format_html("Makale: {}", obj.article.title[:30])
        if obj.question:
            return format_html("Soru: {}", str(obj.question)[:30])
        return "-"

    @admin.display(description="Kimlik")
    def masked_identity_display(self, obj):
        return obj.masked_identity

    @admin.display(description="Puan")
    def rating_stars_display(self, obj):
        if obj.rating is None:
            return "-"
        return f"{obj.rating}/5"


# ─────────────────────────────────────────────────────────────────────────────
# LIKE
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display    = ("article", "session_key", "created_at")
    list_filter     = ("article",)
    readonly_fields = ("session_key", "created_at")


# ─────────────────────────────────────────────────────────────────────────────
# USER BEHAVIOR
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    """Salt okunur — izleme ve analiz içindir."""

    list_display  = (
        "short_session", "article_title",
        "view_count", "time_spent_display",
        "signals_display", "avg_rating", "last_seen",
    )
    list_filter         = ("liked", "commented", "asked_question")
    search_fields       = ("session_key", "article__title")
    date_hierarchy      = "last_seen"
    list_select_related = ("article",)
    readonly_fields     = (
        "session_key", "article", "view_count", "time_spent",
        "liked", "commented", "asked_question", "avg_rating", "last_seen",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Session")
    def short_session(self, obj):
        return obj.session_key[:14] + "…"

    @admin.display(description="Makale")
    def article_title(self, obj):
        if obj.article:
            return obj.article.title[:45]
        return "—"

    @admin.display(description="Süre")
    def time_spent_display(self, obj):
        t = obj.time_spent or 0
        if t >= 60:
            return f"{t // 60}dk {t % 60}sn"
        return f"{t}sn"

    @admin.display(description="Sinyaller")
    def signals_display(self, obj):
        parts = []
        if obj.liked:
            parts.append('<span style="color:#10b981;font-weight:700;">💚 Beğendi</span>')
        if obj.commented:
            parts.append('<span style="color:#f59e0b;font-weight:700;">💬 Yorum</span>')
        if obj.asked_question:
            parts.append('<span style="color:#818cf8;font-weight:700;">❓ Sordu</span>')
        if not parts:
            return format_html('<span style="color:#94a3b8;">—</span>')
        return format_html(" ".join(parts))