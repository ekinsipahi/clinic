from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()

class PublishedManager(models.Manager):
    def get_queryset(self):
        return (super().get_queryset()
                .filter(status="published", published_at__lte=timezone.now()))

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:100]
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:category", kwargs={"category_slug": self.slug})

def cover_upload_to(instance, filename):
    return f"blog/covers/{instance.slug or slugify(instance.title)}/{filename}"

def card_upload_to(instance, filename):
    return f"blog/cards/{instance.slug or slugify(instance.title)}/{filename}"

class Post(models.Model):
    STATUS = (("draft","Draft"), ("published","Published"))
    CONTENT_FORMAT = (("html","HTML"), ("md","Markdown"))

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, related_name="posts",
                                 on_delete=models.SET_NULL, null=True, blank=True)

    # içerik
    content_format = models.CharField(max_length=6, choices=CONTENT_FORMAT, default="md")
    content_html = models.TextField(blank=True, help_text="HTML içerik yazacaksan bunu kullan.")
    content_md = models.TextField(blank=True, help_text="Markdown içerik yazacaksan bunu kullan.")

    # görseller (dosya + harici URL destekli)
    hero_image = models.ImageField(upload_to=cover_upload_to, blank=True, null=True,
                                   help_text="Detay sayfasının tepesindeki büyük poster.")
    card_image = models.ImageField(upload_to=card_upload_to, blank=True, null=True,
                                   help_text="Liste kartında küçük görsel.")
    hero_image_url = models.URLField(blank=True, help_text="Detay sayfası posteri için dış URL")
    card_image_url = models.URLField(blank=True, help_text="Liste kartı görseli için dış URL")

    # SEO
    excerpt = models.TextField(blank=True, help_text="Meta description / liste özeti.")
    meta_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=200, blank=True)
    canonical_url = models.URLField(blank=True)

    # durum
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    published_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ["-published_at"]
        indexes = [models.Index(fields=["-published_at", "category"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:170]
            s = base
            i = 2
            while Post.objects.filter(slug=s).exclude(pk=self.pk).exists():
                s = f"{base}-{i}"
                i += 1
            self.slug = s
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail",
                       kwargs={"category_slug": self.category.slug if self.category else "genel",
                               "post_slug": self.slug})

    @property
    def is_published(self):
        return self.status == "published" and self.published_at <= timezone.now()

    @property
    def reading_time_minutes(self):
        text = self.content_html if self.content_format == "html" else self.content_md
        words = len((text or "").split())
        return max(1, round(words/200))

    # ---- Görsel kaynak seçiciler (önce dosya, sonra URL, sonra fallback) ----
    @property
    def card_src(self):
        if self.card_image:
            try:
                return self.card_image.url
            except Exception:
                pass
        if self.card_image_url:
            return self.card_image_url
        if self.hero_image:
            try:
                return self.hero_image.url
            except Exception:
                pass
        if self.hero_image_url:
            return self.hero_image_url
        return ""

    @property
    def hero_src(self):
        if self.hero_image:
            try:
                return self.hero_image.url
            except Exception:
                pass
        if self.hero_image_url:
            return self.hero_image_url
        if self.card_image:
            try:
                return self.card_image.url
            except Exception:
                pass
        if self.card_image_url:
            return self.card_image_url
        return ""
