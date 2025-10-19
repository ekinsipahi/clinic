# blog/admin.py
from django.contrib import admin

try:
    from .models import Category, Post, PostFAQ
    HAS_POSTFAQ = True
except ImportError:
    from .models import Category, Post
    HAS_POSTFAQ = False

if HAS_POSTFAQ:
    class PostFAQInline(admin.TabularInline):
        model = PostFAQ
        extra = 1
        fields = ("order","question","answer_html")
else:
    PostFAQInline = None

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name","slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title","category","status","published_at")
    list_filter = ("status","category")
    search_fields = ("title","excerpt","content_html","content_md")
    date_hierarchy = "published_at"
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PostFAQInline] if PostFAQInline else []

    fieldsets = (
        (None, {"fields": ("title","slug","author","category","status","published_at","excerpt")}),
        ("İçerik", {"fields": ("content_format","content_html","content_md")}),
        ("Görseller", {"fields": ("card_image", "card_image_url", "hero_image", "hero_image_url")}),
        ("SEO", {"fields": ("meta_title","meta_description","canonical_url")}),
    )
