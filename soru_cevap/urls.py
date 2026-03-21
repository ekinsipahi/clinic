from django.urls import path
from . import views

urlpatterns = [
    path("",         views.home,           name="home"),
    path("sorular/", views.questions_list, name="questions"),

    # Makaleyle ilgili tüm sorular
    path("makale-sorular/<slug:slug>/",
         views.article_questions_list, name="article_questions"),

    # Soru detay
    path("soru/<int:question_id>/<slug:slug>/",
         views.question_detail, name="question_detail"),

    # POST actions
    path("yorum/<slug:slug>/",
         views.comment_article,       name="comment_article"),
    path("begen/<slug:slug>/",
         views.like_article,           name="like_article"),
    path("sor/<slug:slug>/",
         views.ask_question,           name="ask_question"),
    path("soru-yorum/<int:question_id>/",
         views.comment_question,       name="comment_question"),
    path("soru-begen/<int:question_id>/",
         views.like_question,          name="like_question"),
    path("soru-cevapla/<int:question_id>/",
         views.answer_question,        name="answer_question"),
    path("global-sor/",
         views.ask_global_question,    name="ask_global_question"),
    path("sure-takip/",
         views.sure_takip,             name="sure_takip"),

    # Makaleler listesi — tag filtreli
    path("makaleler/",
         views.articles_list,          name="articles_list"),

    # Makale — EN SONA
    path("<slug:slug>/",
         views.article_page,           name="article"),
    
]