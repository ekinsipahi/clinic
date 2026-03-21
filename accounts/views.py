"""
accounts/views.py
URL'den dil tespiti:
  /accounts/giris/    → TR
  /accounts/login/    → EN
  /accounts/kayit/    → TR
  /accounts/register/ → EN
  vb.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .forms import (
    PatientRegisterForm, LoginForm,
    PasswordResetRequestForm, SetNewPasswordForm,
    ProfileEditForm,
)
from soru_cevap.views import _user_display_name

User = get_user_model()

# URL path → dil eşlemesi
_EN_PATHS = {
    'login', 'register', 'logout',
    'password-reset', 'profile', 'privacy',
}


def _detect_lang(request) -> str:
    """
    URL path'inden dili tespit et.
    /accounts/login/    → 'en'
    /accounts/giris/    → 'tr'
    """
    path = request.path.rstrip('/')
    last = path.split('/')[-1]
    return 'en' if last in _EN_PATHS else 'tr'


def _next_url(request, default='/soru-cevap/'):
    nxt = request.GET.get('next') or request.POST.get('next', '')
    if nxt and nxt.startswith('/') and not nxt.startswith('//'):
        return nxt
    return default


def _forum_home(lang):
    return '/question-and-answer/' if lang == 'en' else '/soru-cevap/'


# ─────────────────────────────────────────────────────────────────────────────
# KAYIT / REGISTER
# ─────────────────────────────────────────────────────────────────────────────

def register(request):
    lang = _detect_lang(request)
    if request.user.is_authenticated:
        return redirect(_next_url(request, _forum_home(lang)))

    form = PatientRegisterForm(request.POST or None, lang=lang)

    if request.method == 'POST' and form.is_valid():
        cd           = form.cleaned_data
        email        = cd['email']
        display_name = cd['display_name'].strip()
        phone        = cd['phone']
        password     = cd['password1']

        user = User.objects.create_user(
            username=email, email=email, password=password,
        )
        parts = display_name.split(' ', 1)
        user.first_name = parts[0]
        user.last_name  = parts[1] if len(parts) > 1 else ''
        user.save()

        profile              = user.profile
        profile.display_name = display_name
        profile.save()

        request.session['reg_phone'] = phone
        login(request, user)
        return redirect(_next_url(request, _forum_home(lang)))

    return render(request, 'accounts/register.html', {
        'form': form,
        'lang': lang,
        'next': request.GET.get('next', ''),
        'alt_url': '/accounts/register/' if lang == 'tr' else '/accounts/kayit/',
    })


# ─────────────────────────────────────────────────────────────────────────────
# GİRİŞ / LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def login_view(request):
    lang = _detect_lang(request)
    if request.user.is_authenticated:
        return redirect(_next_url(request, _forum_home(lang)))

    form  = LoginForm(request.POST or None)
    reset = request.GET.get('reset')

    if request.method == 'POST' and form.is_valid():
        login(request, form.cleaned_data['auth_user'])
        return redirect(_next_url(request, _forum_home(lang)))

    return render(request, 'accounts/login.html', {
        'form':    form,
        'lang':    lang,
        'next':    request.GET.get('next', ''),
        'reset':   reset,
        'alt_url': '/accounts/login/' if lang == 'tr' else '/accounts/giris/',
        'register_url': '/accounts/register/' if lang == 'en' else '/accounts/kayit/',
        'reset_url':    '/accounts/password-reset/' if lang == 'en' else '/accounts/sifre-sifirla/',
    })


# ─────────────────────────────────────────────────────────────────────────────
# ÇIKIŞ / LOGOUT
# ─────────────────────────────────────────────────────────────────────────────

def logout_view(request):
    lang = _detect_lang(request)
    logout(request)
    return redirect(_forum_home(lang))


# ─────────────────────────────────────────────────────────────────────────────
# ŞİFRE SIFIRLAMA / PASSWORD RESET — REQUEST
# ─────────────────────────────────────────────────────────────────────────────

def password_reset_request(request):
    lang = _detect_lang(request)
    form = PasswordResetRequestForm(request.POST or None)
    sent = False

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user  = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid   = urlsafe_base64_encode(force_bytes(user.pk))

            # Dile göre sıfırlama URL'i
            if lang == 'en':
                reset_path = f'/accounts/password-reset/{uid}/{token}/'
            else:
                reset_path = f'/accounts/sifre-sifirla/{uid}/{token}/'

            reset_url = request.build_absolute_uri(reset_path)

            if lang == 'en':
                subject = 'Dr. Devrim Forum — Password Reset'
                body = (
                    f'Hello,\n\n'
                    f'Click the link below to reset your password:\n\n'
                    f'{reset_url}\n\n'
                    f'This link is valid for 24 hours.\n\n'
                    f'If you did not request this, please ignore this email.\n\n'
                    f'— Dr. Devrim Dental Forum'
                )
            else:
                subject = 'Dr. Devrim Forum — Şifre Sıfırlama'
                body = (
                    f'Merhaba,\n\n'
                    f'Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:\n\n'
                    f'{reset_url}\n\n'
                    f'Bu bağlantı 24 saat geçerlidir.\n\n'
                    f'Bu isteği siz yapmadıysanız bu e-postayı görmezden gelebilirsiniz.\n\n'
                    f'— Dr. Devrim Dental Forum'
                )

            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@drdevrim.com'),
                recipient_list=[email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass  # Enumeration koruması
        sent = True

    return render(request, 'accounts/password_reset.html', {
        'form': form,
        'lang': lang,
        'sent': sent,
        'login_url': '/accounts/login/' if lang == 'en' else '/accounts/giris/',
    })


# ─────────────────────────────────────────────────────────────────────────────
# ŞİFRE SIFIRLAMA / PASSWORD RESET — CONFIRM
# ─────────────────────────────────────────────────────────────────────────────

def password_reset_confirm(request, uidb64, token):
    lang = _detect_lang(request)

    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    valid = user is not None and default_token_generator.check_token(user, token)
    form  = SetNewPasswordForm(request.POST or None) if valid else None
    done  = False

    if valid and request.method == 'POST' and form and form.is_valid():
        user.set_password(form.cleaned_data['password1'])
        user.save()
        done = True

    login_url = '/accounts/login/?reset=1' if lang == 'en' else '/accounts/giris/?reset=1'
    reset_url = '/accounts/password-reset/' if lang == 'en' else '/accounts/sifre-sifirla/'

    return render(request, 'accounts/password_reset_confirm.html', {
        'form':      form,
        'lang':      lang,
        'valid':     valid,
        'done':      done,
        'uidb64':    uidb64,
        'token':     token,
        'login_url': login_url,
        'reset_url': reset_url,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PROFİL / PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    lang = _detect_lang(request)
    user = request.user
    prof = user.profile

    initial = {
        'display_name': prof.display_name or user.get_full_name(),
        'phone':        '',
    }
    form  = ProfileEditForm(request.POST or None, initial=initial)
    saved = False

    if request.method == 'POST' and form.is_valid():
        cd               = form.cleaned_data
        prof.display_name = cd['display_name']
        prof.save()
        parts            = cd['display_name'].strip().split(' ', 1)
        user.first_name  = parts[0]
        user.last_name   = parts[1] if len(parts) > 1 else ''
        user.save()
        saved = True

    return render(request, 'accounts/profile.html', {
        'form':    form,
        'profile': prof,
        'lang':    lang,
        'saved':   saved,
    })


# ─────────────────────────────────────────────────────────────────────────────
# KVKK / PRIVACY
# ─────────────────────────────────────────────────────────────────────────────

def kvkk_view(request):
    path = request.path.rstrip('/')
    lang = 'en' if path.endswith('privacy') else 'tr'
    return render(request, 'accounts/kvkk.html', {'lang': lang})



@login_required
def my_questions(request):
    lang = _detect_lang(request)

    from soru_cevap.models import Question

    questions = (
        Question.objects
        .filter(user=request.user)
        .select_related('user')
        .prefetch_related('comments')
        .order_by('-created_at')
    )

    answered_count = questions.filter(answer__isnull=False).exclude(answer='').count()
    pending_count  = questions.filter(answer__isnull=True).count() + questions.filter(answer='').count()
    # Daha temiz:
    # pending_count = questions.count() - answered_count

    return render(request, 'accounts/my_questions.html', {
        'questions':      questions,
        'answered_count': answered_count,
        'pending_count':  pending_count,   # ← YENİ
        'lang':           lang,
        'language':       lang,
        'user_display_name': _user_display_name(request.user),
    })