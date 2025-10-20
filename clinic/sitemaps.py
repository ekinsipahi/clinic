# clinic/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse, get_resolver, URLPattern, URLResolver, NoReverseMatch
from django.utils import timezone
from blog.models import Post, Category


def _iter_urlpatterns(resolver=None, prefix=""):
    resolver = resolver or get_resolver()
    for p in resolver.url_patterns:
        if isinstance(p, URLPattern):
            yield (p, prefix + str(p.pattern))
        elif isinstance(p, URLResolver):
            new_prefix = prefix + str(p.pattern)
            yield from _iter_urlpatterns(p, new_prefix)


def _is_paramless_route(route: str) -> bool:
    # path converters: <slug>, <int>...
    if "<" in route or ">" in route:
        return False
    # re_path: regex parantezleri
    if "(" in route or ")" in route:
        return False
    return True


def _is_whitelisted_name(name: str) -> bool:
    # isim bazlı kaba eleme (admin, debug, static vs). API'yı path bazında ayrıca eleyeceğiz.
    if not name:
        return False
    deny_prefixes = (
        "admin",
        "__debug__", "djdt",
        "static", "media",
        "schema", "openapi", "redoc",
        "blog:",  # blog detay/kategori Auto’dan hariç; onlar DB tabanlı sitemaps’te
    )
    return not any(name.startswith(p) for p in deny_prefixes)


class AutoURLSitemap(Sitemap):
    """
    Parametresiz + whiteliste takılan named URL'ler.
    - PATH bazında /api ile başlayan her şey HARİÇ
    - blog namespace (detay/kategori) Auto’dan hariç
    - Aynı path birden çok name üretirse dedupe yap
    """
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        # Aday isimleri topla (parametresiz & whitelist)
        candidate_names = []
        for pat, route in _iter_urlpatterns():
            name = getattr(pat, "name", None)
            if not _is_paramless_route(route):
                continue
            if not _is_whitelisted_name(name):
                continue
            candidate_names.append(name)

        # Kritik sayfaları garantiye al (kendi name'lerine göre güncelle)
        candidate_names.extend({"home", "kvkk", "appointment", "blog:index"})

        # DEDUPE: path’e göre tekilleştir + /api ile başlayanları dışla
        seen_locations = set()
        unique_names = []
        for nm in candidate_names:
            # resolve et
            try:
                loc = reverse(nm)
            except NoReverseMatch:
                mapping = {
                    "home": "/",
                    "kvkk": "/kvkk",
                    "appointment": "/randevu-al",
                    "blog:index": "/blog/",
                }
                loc = mapping.get(nm)
                if not loc:
                    continue

            # *** EN ÖNEMLİ KISIM: /api ile başlayan path'leri alma ***
            # normalize (domain yok; sadece path gelir)
            if loc.startswith("/api"):
                continue

            # dedupe
            if loc in seen_locations:
                continue
            seen_locations.add(loc)
            unique_names.append(nm)

        return sorted(unique_names)

    def location(self, item):
        try:
            return reverse(item)
        except NoReverseMatch:
            mapping = {
                "home": "/",
                "kvkk": "/kvkk",
                "appointment": "/randevu-al",
                "blog:index": "/blog/",
            }
            return mapping.get(item, "/")

    def lastmod(self, item):
        last = Post.published.order_by("-updated_at").first()
        return last.updated_at if last else timezone.now()


class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        cat_ids = (Post.published.exclude(category__isnull=True)
                   .values_list("category_id", flat=True).distinct())
        return Category.objects.filter(id__in=cat_ids).order_by("name")

    def location(self, obj: Category):
        return obj.get_absolute_url()

    def lastmod(self, obj: Category):
        last = (Post.published.filter(category=obj)
                .order_by("-updated_at").first())
        return last.updated_at if last else timezone.now()


class PostSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return (Post.published
                .select_related("category")
                .order_by("-published_at"))

    def location(self, obj: Post):
        return obj.get_absolute_url()

    def lastmod(self, obj: Post):
        return obj.updated_at

    def priority(self, obj: Post):
        age = (timezone.now() - obj.published_at).days
        return 1.0 if age <= 7 else (0.9 if age <= 30 else 0.8)
