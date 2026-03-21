"""
accounts/forms.py
Hasta kayıt, giriş, şifre sıfırlama, profil düzenleme formları.
"""
import re
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


def _validate_phone(value):
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    if not re.match(r'^\+?[\d]{10,15}$', cleaned):
        raise ValidationError('Geçerli bir telefon numarası girin. Örn: 05321234567')
    return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# KAYIT
# ─────────────────────────────────────────────────────────────────────────────

class PatientRegisterForm(forms.Form):

    def __init__(self, *args, lang='tr', **kwargs):
        super().__init__(*args, **kwargs)
        self._lang = lang

    display_name = forms.CharField(
        label='Ad Soyad',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'qa-input',
            'placeholder': 'Adınız Soyadınız',
            'autocomplete': 'name',
        })
    )
    email = forms.EmailField(
        label='E-posta',
        widget=forms.EmailInput(attrs={
            'class': 'qa-input',
            'placeholder': 'ornek@mail.com',
            'autocomplete': 'email',
        })
    )
    phone = forms.CharField(
        label='Telefon',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'qa-input',
            'placeholder': '05321234567',
            'autocomplete': 'tel',
            'inputmode': 'tel',
        })
    )
    password1 = forms.CharField(
        label='Şifre',
        widget=forms.PasswordInput(attrs={
            'class': 'qa-input',
            'placeholder': 'En az 8 karakter',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label='Şifre Tekrar',
        widget=forms.PasswordInput(attrs={
            'class': 'qa-input',
            'placeholder': 'Şifrenizi tekrar girin',
            'autocomplete': 'new-password',
        })
    )
    kvkk = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must accept the Privacy Policy to continue.' }
        # TR mesajı clean'de override edilecek
    )

    def clean_kvkk(self):
        val = self.cleaned_data.get('kvkk')
        if not val:
            msg = 'You must accept the Privacy Policy to continue.' if self._lang == 'en' else 'Devam etmek için KVKK / Aydınlatma Metnini onaylamanız gerekiyor.'
            raise ValidationError(msg)
        return val

    def clean_display_name(self):
        name = self.cleaned_data.get('display_name', '').strip()
        if len(name) < 2:
            msg = 'Full name must be at least 2 characters.' if self._lang == 'en' else 'Ad soyad en az 2 karakter olmalıdır.'
            raise ValidationError(msg)
        return name

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            msg = 'This email address is already registered.' if self._lang == 'en' else 'Bu e-posta adresi zaten kayıtlı.'
            raise ValidationError(msg)
        return email

    def clean_phone(self):
        value = self.cleaned_data['phone']
        cleaned = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^\+?[\d]{10,15}$', cleaned):
            msg = 'Enter a valid phone number. e.g. +905321234567' if self._lang == 'en' else 'Geçerli bir telefon numarası girin. Örn: 05321234567'
            raise ValidationError(msg)
        return cleaned

    def clean_password1(self):
        pw = self.cleaned_data.get('password1', '')
        try:
            validate_password(pw)
        except ValidationError as e:
            raise ValidationError(list(e.messages))
        return pw

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('password1')
        pw2 = cleaned.get('password2')
        if pw1 and pw2 and pw1 != pw2:
            msg = 'Passwords do not match.' if self._lang == 'en' else 'Şifreler eşleşmiyor.'
            self.add_error('password2', msg)
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# GİRİŞ
# ─────────────────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    email = forms.EmailField(
        label='E-posta',
        widget=forms.EmailInput(attrs={
            'class': 'qa-input',
            'placeholder': 'ornek@mail.com',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        label='Şifre',
        widget=forms.PasswordInput(attrs={
            'class': 'qa-input',
            'placeholder': 'Şifreniz',
            'autocomplete': 'current-password',
        })
    )

    def clean(self):
        cleaned  = super().clean()
        email    = cleaned.get('email', '').lower().strip()
        password = cleaned.get('password', '')
        if email and password:
            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ValidationError('E-posta veya şifre hatalı.')
            auth_user = authenticate(username=user_obj.username, password=password)
            if not auth_user:
                raise ValidationError('E-posta veya şifre hatalı.')
            if not auth_user.is_active:
                raise ValidationError('Hesabınız aktif değil. Lütfen bizimle iletişime geçin.')
            cleaned['auth_user'] = auth_user
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# ŞİFRE SIFIRLAMA
# ─────────────────────────────────────────────────────────────────────────────

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='E-posta',
        widget=forms.EmailInput(attrs={
            'class': 'qa-input',
            'placeholder': 'Kayıtlı e-posta adresiniz',
            'autocomplete': 'email',
        })
    )

    def clean_email(self):
        # Güvenlik: kullanıcı yoksa da hata vermiyoruz (enumeration koruması)
        return self.cleaned_data['email'].lower().strip()


class SetNewPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='Yeni Şifre',
        widget=forms.PasswordInput(attrs={
            'class': 'qa-input',
            'placeholder': 'En az 8 karakter',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label='Yeni Şifre Tekrar',
        widget=forms.PasswordInput(attrs={
            'class': 'qa-input',
            'placeholder': 'Şifrenizi tekrar girin',
            'autocomplete': 'new-password',
        })
    )

    def clean_password1(self):
        pw = self.cleaned_data.get('password1', '')
        try:
            validate_password(pw)
        except ValidationError as e:
            raise ValidationError(list(e.messages))
        return pw

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get('password1')
        pw2 = cleaned.get('password2')
        if pw1 and pw2 and pw1 != pw2:
            self.add_error('password2', 'Şifreler eşleşmiyor.')
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# PROFİL DÜZENLEME
# ─────────────────────────────────────────────────────────────────────────────

class ProfileEditForm(forms.Form):
    display_name = forms.CharField(
        label='Ad Soyad',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'qa-input',
            'placeholder': 'Adınız Soyadınız',
        })
    )
    phone = forms.CharField(
        label='Telefon',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'qa-input',
            'placeholder': '05321234567',
            'inputmode': 'tel',
        })
    )

    def clean_display_name(self):
        name = self.cleaned_data.get('display_name', '').strip()
        if len(name) < 2:
            raise ValidationError('Ad soyad en az 2 karakter olmalıdır.')
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            return _validate_phone(phone)
        return phone