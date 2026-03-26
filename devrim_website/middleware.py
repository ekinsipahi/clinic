# devrim_website/middleware.py
from django.shortcuts import redirect

OLD_DOMAINS = {
    "devrimbirikensipahi.com.tr",
    "www.devrimbirikensipahi.com.tr"
}

NEW_DOMAIN = "https://drdevrim.com"

class RedirectDomainMiddleware:
    """
    Sadece eski domainlerden gelen tüm istekleri
    yeni domain'e 301 redirect ile yönlendirir.
    Path korunur.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()  # www veya domain
        if host in OLD_DOMAINS:
            new_url = f"{NEW_DOMAIN}{request.get_full_path()}"
            return redirect(new_url, permanent=True)

        return self.get_response(request)