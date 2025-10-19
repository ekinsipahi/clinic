from django.shortcuts import render, redirect
from .models import CallMeLead, ArrivalConfirmation
from django.utils.timezone import now
import json
from django.utils.translation import gettext as _  # <-- EKLENDİ

PEDO_CAMPAIGN_ID = "22663185094"


def homepage(request):
    # 1) campaign_id'yi URL'den oku (ValueTrack: {campaignid})
    campaign_id = (
        request.GET.get("campaign_id")
        or request.GET.get("campaignid")
        or request.GET.get("utm_campaignid")
        or request.COOKIES.get("campaign_id")  # opsiyonel: cookie fallback
    )
    pedodonti_ad = (campaign_id == PEDO_CAMPAIGN_ID)

    
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        message = request.POST.get("message")
        gclid = request.POST.get("gclid")
        page = request.POST.get("page")  # <-- gelen sayfa bilgisi
        client_info_raw = request.POST.get("client_info")

        try:
            client_info = json.loads(client_info_raw) if client_info_raw else {}
        except json.JSONDecodeError:
            client_info = {}

        if name and phone:
            lead = CallMeLead.objects.create(
                name=name,
                phone=phone,
                message=message,
                gclid=gclid,
                client_info=client_info,  # <-- EKLENDİ!
                page=page or "Beni Ara Lead",  # <-- EKLENDİ!
            )

            return redirect("/tesekkur")
    ctx = {
        "pedodonti_ad": pedodonti_ad,
    }
    return render(request, "clinic/index.html", ctx)


def randevu_al(request):
    return render(request, "clinic/randevu-al.html")


def whatsapp_yonlendir(request):
    return render(request, "clinic/whatsapp-yonlendir.html")


def telefon_yonlendir(request):
    return render(request, "clinic/telefon-yonlendir.html")


def instagram_yonlendir(request):
    return render(request, "clinic/instagram-yonlendir.html")


def maps_yonlendir(request):
    return render(request, "clinic/maps-yonlendir.html")


def kvkk(request):
    return render(request, "clinic/kvkk.html")


def tesekkurler(request):
    return render(request, "clinic/callme-tesekkur.html")


def onay(request):
    if request.method == "POST":
        name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        gclid = request.POST.get("gclid")
        page = "Manuel Onay"
        client_info_raw = request.POST.get("client_info")
        print("ISIM: ",name)
        print("Telefon: ", phone)
        print("GCLID", gclid)
        print("Sayfa: ", page)
        print("Client Info: ", client_info_raw)
        
        try:
            client_info = json.loads(client_info_raw) if client_info_raw else {}
        except json.JSONDecodeError:
            client_info = {}
        
        if name and phone:
            ArrivalConfirmation.objects.create(
                full_name=name,
                phone=phone,
                gclid=gclid,
                page=page,
                client_info=client_info
            )
            return redirect("/onay-tesekkur")

    return render(request, "clinic/onay.html")

def onay_tesekkur(request):
    return render(request, "clinic/onay-tesekkur.html")


def page_not_found_view(request, exception=None):
    """
    Global 404 handler.
    - DEBUG=False iken Django bu fonksiyonu çağırır.
    - App-scope catch-all ile manuel de çağrılabilir.
    """
    ctx = {
        "title": _("Sayfa bulunamadı"),
        "home_url": "/",
        "randevu_url": "/randevu-al",
        "whatsapp_url": "https://wa.me/905055771883?text=Merhaba%2C%20randevu%20almak%20istiyorum.",
    }
    return render(request, "clinic/404.html", ctx, status=404)
