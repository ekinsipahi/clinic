from django.urls import path
from .views import PostListView, CategoryListView, PostDetailView

app_name = "blog"

urlpatterns = [
    path("", PostListView.as_view(), name="index"),
    path("<slug:category_slug>/", CategoryListView.as_view(), name="category"),
    path("<slug:category_slug>/<slug:post_slug>/", PostDetailView.as_view(), name="detail"),
]
