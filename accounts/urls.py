from django.urls import path
from . import views

urlpatterns = [
    # ── Kayıt / Register ──────────────────────────────────────────────────────
    path('kayit/',                            views.register,               name='register'),
    path('register/',                         views.register,               name='register_en'),

    # ── Giriş / Login ─────────────────────────────────────────────────────────
    path('giris/',                            views.login_view,             name='login'),
    path('login/',                            views.login_view,             name='login_en'),

    # ── Çıkış / Logout ────────────────────────────────────────────────────────
    path('cikis/',                            views.logout_view,            name='logout'),
    path('logout/',                           views.logout_view,            name='logout_en'),

    # ── Şifre Sıfırla / Password Reset ───────────────────────────────────────
    path('sifre-sifirla/',                    views.password_reset_request, name='password_reset'),
    path('password-reset/',                   views.password_reset_request, name='password_reset_en'),

    path('sifre-sifirla/<uidb64>/<token>/',   views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/<uidb64>/<token>/',  views.password_reset_confirm, name='password_reset_confirm_en'),

    # ── Profil — geçici olarak devre dışı, hazır olunca açılacak ─────────────
    # path('profil/',   views.profile_view, name='profile'),
    # path('profile/',  views.profile_view, name='profile_en'),

    # ── Benim Sorularım / My Questions ───────────────────────────────────────
    path('benim-sorularim/',                  views.my_questions,           name='my_questions'),
    path('my-questions/',                     views.my_questions,           name='my_questions_en'),

    # ── KVKK / Privacy ────────────────────────────────────────────────────────
    path('kvkk/',                             views.kvkk_view,              name='kvkk'),
    path('privacy/',                          views.kvkk_view,              name='privacy'),
]