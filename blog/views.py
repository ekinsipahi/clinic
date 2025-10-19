from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import Post, Category
import markdown

MD_EXT = ["fenced_code", "tables", "toc", "codehilite"]

class PostListView(ListView):
    model = Post
    queryset = (Post.published.select_related("category").order_by("-published_at"))
    paginate_by = 12
    template_name = "blog/blog_index.html"
    context_object_name = "posts"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["all_categories"] = Category.objects.all().order_by("name")
        ctx["active_category_slug"] = None
        return ctx

class CategoryListView(PostListView):
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["category_slug"])
        return (Post.published
                    .filter(category=self.category)
                    .select_related("category")
                    .order_by("-published_at"))
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["category"] = self.category
        ctx["active_category_slug"] = self.category.slug
        return ctx
class PostDetailView(DetailView):
    model = Post
    template_name = "blog/detail.html"
    context_object_name = "post"

    def get_object(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["category_slug"])
        return get_object_or_404(
            Post.published.select_related("category"),
            category=self.category,
            slug=self.kwargs["post_slug"]
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.object

        # --- İçerik render (akıllı fallback) ---
        html_src = (post.content_html or "").strip()
        md_src = (post.content_md or "").strip()

        # Öncelik: content_format'e saygı + fallback
        if post.content_format == "html":
            raw_html = html_src or md_src  # HTML boşsa Markdown'ı fallback olarak kullan
            if raw_html == html_src:
                ctx["content_html"] = mark_safe(raw_html)
            else:
                ctx["content_html"] = mark_safe(markdown.markdown(raw_html, extensions=MD_EXT))
        else:  # "md"
            raw_md = md_src or html_src  # MD boşsa HTML'i fallback olarak kullan
            if raw_md == md_src:
                ctx["content_html"] = mark_safe(markdown.markdown(raw_md, extensions=MD_EXT))
            else:
                ctx["content_html"] = mark_safe(raw_md)

        # --- Prev/Next ---
        ctx["prev_post"] = (
            Post.published
                .filter(category=post.category, published_at__lt=post.published_at)
                .order_by("-published_at")
                .first()
        )
        ctx["next_post"] = (
            Post.published
                .filter(category=post.category, published_at__gt=post.published_at)
                .order_by("published_at")
                .first()
        )
        

        # --- JSON-LD için hero absolute URL ---
        hero_src = post.hero_src or ""
        if hero_src and not hero_src.startswith(("http://", "https://", "//")):
            ctx["hero_abs_url"] = self.request.build_absolute_uri(hero_src)
        else:
            ctx["hero_abs_url"] = hero_src

        return ctx
