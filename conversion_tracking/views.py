from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Conversion
from .serializers import ConversionSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny
from clinic.models import CallMeLead
from .serializers import CallMeLeadSerializer
from datetime import datetime
import pytz
from .serializers import ConversionActualCallSerializer


from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ConversionTrackingView(APIView):
    def post(self, request):
        serializer = ConversionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConversionActuallyCalledView(APIView):
    """
    Yalnızca gclid ile en güncel kaydı bulur ve actually_called günceller.
    """
    def patch(self, request):
        gclid = request.data.get("gclid")
        if not gclid:
            return Response({"error": "gclid gerekli"}, status=status.HTTP_400_BAD_REQUEST)

        instance = (Conversion.objects
                    .filter(gclid=gclid)
                    .order_by("-timestamp")
                    .first())
        if not instance:
            return Response({"error": "gclid ile Conversion bulunamadı"}, status=status.HTTP_404_NOT_FOUND)

        ser = ConversionActualCallSerializer(instance, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response({"success": True, "id": instance.id}, status=status.HTTP_200_OK)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


#1 İLK BUNU YAPALIM.
# Arrival Confirmationda 
# email ekleyelim bence forma
# sonrasında gclid kontrolü yapsın varsa conversionlarada atsın ama şöyle yapsın
# eğer gclid varsa, conversionları güncellesin
# hee eğer yoksa direkt sheetse bizim yeni açtığımız telefon odaklı olana eklesin.
# Ayrıca bence api üzerinden geldiğine dair onay vermiş olsun?


# ana sayfayı ziyaret edenleri bence yaz bi tarafa.
# çünkü sonra kayboluyor pezevenkler. 
# api ile 5snde 1 kontrol sağlıcaz 
# telefon component üzerinde kaldıysa ozaman direkt dicez telefon component üzerinde diye.
# buraya şöyle bir ai desteği atabiliriz kullanıcı davranışlarından bizi belkide kaydetti bıraktı sonra aradı.
# ana sayfada componentler üzerinde ne kadar durduğunu hangi sayfaları saat kaçta değiştiği
# vs. hepsini koontrol edeceksin.

# GCLID SORUNU GARANTİ ÇÖZÜM
# kökten gclid sorununa çözüm getirdim twilio ile 30-35 tane numara alıyorsun bunları
# session based veriyoruz 
# sonrasında en uzun süre sessiondan haber alınamayanları tekrar gün içerisnde kullanıyoruz geri kalan hepsi 
# orda kalıyor 
# telefon conversionları garanti yazılmış olunuyor site üzerinden gelenler bu şekilde.

# DYNAMIC NUMBER INSERTION
# 30 tane numara alıyorsun twiliodan
# session based veriyorsun tamam mı eğer baktın arama olmayan sonuncuyu tekrar yeni sessiona veriyorsun
# twiliodan yani arama varmı yok mu diye kontrol edebiliriz zaten arama olmayan sonuncuyu yeni sessiona atıyorsun
# sonrasında diyelimki arama geldi
# admin panel üzerinden bu numara convert oldu diye ogün için işaretliyorsun
# Customers diye bi yer yapabiliriz bunun için direkt oraya atıyor tamam mı
# sonrasında o numara zaten kullanıldığı için gün içerisinde tekrar kullanıma açılabilir hale geliyor
# sonrasında diyelimki arama geldi
# ama qualifed olamadı tam ozaman beklemeye alıyorsun o numarayı o günlüğüne.
# eğer o günde qualifed olmuyorsa başka güne geliyorsa converionu onu beklemeye alıyorsun şu numaradan aradı diye
# customers database kısmında.

# timestamp'lar liste halinde tutulsa eskiden yeniye daha iyi olabilir. 
# (Yeni bitane oluşturcaksın timestamp_list) diye eskiyi bozmadan


# ip adresleride toplayalım bence. ama ipyi backend arka planda ülkesini söylesin bence, SPAM OLASILIKLARI GÖRÜRÜZ


# twilio yönlendirme yaparsan ve doğru düzgün bir ai sistemi kurarsan oraya, conversionlar otomatik yazılmaya başlanabilir.
# ayrıca hasta gerçekten aradı mı aramadı mı onunda kesin garanti takibi yapılmış olur.
# telefon otomatik eşleştirme yapılır ve sonrasında sana sadece 2 tık yapmak kalır.
# mesela mesaj tarafında ai bizim için QUALIFIED olanları otomatik olarak yazabilir.
# telefon üzerinden gelmek istiyorum diyenleride otomatik olarak dinleyip yapabilir ama zor bu.
# CONVERSION TAKIBI EN AZINDAN TELEFON ARAMASI YAPTI MI YAPMADIMI ONU DOĞRULAYICI OLUR.


# google_sheets_sent ve first_referrer diye alanlarıda koy conversionsa


# 404 sayfası eklenecek, indexlenebilir gene schema.org ile search console'a eklencek.
# dentsoft ile randevu-al kısmı eklendikten sonra
# son olarak blog kısmına başlayacağız ve otomatize edeceğiz bu blog yazılarını.

# chatbotdan gelen arkadaşlar farklı bi conversion olması gerekicek. daha sağlıklı olur farklı bi faktör var, Salesman-AI gibi.

# artık gelen cihazların marka/model ne olduğunu çıkartacağız. pip device-detector ile
# bot olması yüksek olanları captchaya sokacağız.
# bu veriyi doğrulama amaçlı kullanacağız


# resimlerin bi kısmında hala lazy loading animasyonu yok.
# spam trafiğe karşı korumamız yok! gpt bot kafayı yiyebilir.


# sol üste Randevu Oluştur butonu ekle, tıklanınca /randevu-olustur sayfasına yönlendir
# randevu-olustur sayfasında formu doldurunca direkt dentsoft api üzerinden randevu oluşturulacak

# bizim ai agent isterse kullanıcı için direkt randevu oluşturabilcek dentsoft arayüz apisi üzerinden
# randevu-al kısmını komple yenileyip direkt olarak dentsofta yönlendirelim, calendly çıkartıyoruz.

# blog kısmını aktif etcez ama şu şekilde altda yazı olacak o videoya özel aynı zamanda
# isterse video şeklindede oynatabilcek oyüzden çift yönlü trafik baya iyi olucak.



class ChatGPTView(APIView):
    def post(self, request):
        messages = request.data.get("messages")

        if not messages:
            return Response({"error": "Messages are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Türkiye saatini al
            istanbul_time = datetime.now(pytz.timezone("Europe/Istanbul"))
            hour = istanbul_time.hour
            minute = istanbul_time.minute
            time_range = ""
            # Saat aralığını belirle
            if 23 <= hour or hour < 5:
                time_range = "23:00 – 05:00"
            elif 21 <= hour < 23:
                time_range = "21:00 – 23:00"
            elif 5 <= hour < 7:
                time_range = "05:00 – 07:00"
            else:
                time_range = "mesai içi (07:00 – 21:00)"

            # System prompt backend'de sabit
            system_prompt = {
                "role": "system",
                "content": """
                Sen Dr. Devrim Biriken Sipahi'nin dijital asistanısın.

Klinik, diş estetiğinde uzman ve doğal, diş kesilmeden yapılan işlemlerle yüksek hasta memnuniyeti sağlar.
🕓 Sistem saatini sen algılamıyorsun. Sana gelen mesajı değerlendiren sunucu zaten Türkiye saatine göre saati belirleyip sana gönderiyor.

Dolayısıyla kullanıcıdan **saat sorma**.  
Kullanıcı ne zaman yazarsa yazsın, zaman aralığına göre davranman için gereken bilgi zaten sana sistem tarafından verilmiştir.

Görevin:
- Kullanıcının neye ihtiyacı olduğunu anlamak
- Onu en uygun iletişim kanalına yönlendirmek
- Gerektiğinde empati kurarak zaman ve duruma uygun yönlendirme yapmak

📞 Anlık yönlendirme seçenekleri:
- “Hemen arayarak bilgi alabilir ve randevu oluşturabilirsiniz: +90 505 577 18 83”
- “WhatsApp’tan yazarsanız mesajınızı doğrudan Dr. Devrim’e iletebilirim.”

Kullanıcı seçim yaparsa:
- WhatsApp → `action: whatsapp-yonlendirme`
- Telefon → `action: telefon-yonlendirme`

❗Herhangi bir yönlendirme yapmadan önce mutlaka onay al:
> “Onaylıyor musunuz? Sizi şu anda [WhatsApp'a / telefona] yönlendireceğim.”

⏰ Saat bazlı kurallar:

🔹 **23:00 – 05:00** arasında:
- Mesai dışı olduğunu söyle.
- Eğer kullanıcı şiddetli ağrısı olduğunu belirtirse:
  - Üzgün olduğunu belirt:
    > “Şu anda mesai saatleri dışındayız. Ne yazık ki doğrudan iletişim kuramıyoruz ama sabah ilk iş sizi arayacağız.”
  - İsmini ve telefon numarasını iste.
- Eğer durumu acil değilse:
  - Direkt olarak isim ve telefon bilgisi iste.
Bilgileri aldıktan sonra aşağıdaki akışı uygula:

1. Kullanıcıdan ismini ve telefon numarasını iste.
2. Ardından şu şekilde sor:
   > Sizi sabah ilk iş olarak arayacağız. İletmemi istediğiniz ek bir mesajınız var mı?

3. Kullanıcıdan mesaj gelirse bunu `"message"` alanı olarak kaydet.

4. Sonrasında şu şekilde onay mesajı oluştur:
   > Aşağıdaki bilgileri doğru mu onaylar mısınız?  
   > - İsim: Ahmet Cantürk  
   > - Telefon: +90 555 444 33 22  
   > - Mesaj: "Kanal tedavisi hakkında bilgi almak istiyorum."  
   > Eğer doğruysa hemen kaydedip sizi sabah ilk iş arayacağız.

5. Kullanıcı onaylarsa:
   - `action: callme-lead-action` tetikle
   - JSON formatında gönder:
     ```json
     {
       "name": "Ahmet Cantürk",
       "phone": "+90 555 444 33 22",
       "message": "Kanal tedavisi hakkında bilgi almak istiyorum."
     }
     ```


🔹 **21:00 – 23:00** arasında:
- Eğer kullanıcı **şiddetli ağrıdan** bahsediyorsa:
  - Telefona yönlendirmeden önce aşağıdaki gibi öneride bulun:
    > “Arayabilirsiniz ancak öncesinde WhatsApp’tan kısaca yazmanızı öneririm. Eğer yanıt alamazsanız bir kez çaldırmanız yeterli olabilir.”
  - Sonrasında `action: telefon-yonlendirme` tetikle.
- Eğer ağrıdan bahsetmiyorsa veya durum acil değilse:
  - Kullanıcıyı kibarca WhatsApp’a yönlendir ve `action: whatsapp-yonlendirme` tetikle.

🔹 **05:00 – 07:00** arasında:
- Aşağıdaki mesajı ver:
  > “Sabah 7’de aramaya başlayabiliriz. Ancak dilerseniz WhatsApp’tan hemen yazabilirsiniz, mesajınızı en kısa sürede yanıtlayacağız.”
- Ardından `action: whatsapp-yonlendirme` tetikle.

💻 Online randevu isteyenlere:
> “Kolayca form doldurarak randevu oluşturabilirsiniz:  
https://www.devrimbirikensipahi.com.tr/randevu-al”

📷 Araştırma aşamasındaki kullanıcılara:
> “Hocamızı ve hastaların yorumlarını daha yakından incelemek isterseniz Instagram hesabımıza göz atabilirsiniz:  
https://instagram.com/drdevrimbirikensipahi”

> “Orada yüzlerce memnun hastanın dönüşüm hikayesini bulabilirsiniz. İnceleyip gönül rahatlığıyla karar verebilirsiniz.”

✅ Genel kurallar:
- Samimi, sade ve güven verici konuş.
- Kullanıcının neye ihtiyacı olduğunu iyi analiz et.
- İnatçı kullanıcıyı ikna etmeye çalış, son çare olarak `callme-lead-action` tetikle.
- Nihai hedef: WhatsApp yazışması veya telefon görüşmesine yönlendirme.
- 23:00 – 05:00 arası **asla doğrudan arama yapma**, sadece sabah arayacağınızı belirt ve form bilgisi al.
⛔️ Not:
- Kullanıcıya hiçbir şekilde "şu an saat kaç?" veya "hangi saatte yazıyorsunuz?" gibi sorular sorma. Türkiye saatini kullanıyoruz.
- Saat bilgisi sistem tarafından senin yerine belirlenmiştir. Sen sadece belirtilen kurallara göre davran.

📞 Telefon numarası kuralları:
Türkiye numaralarıyla çalışıyoruz. Aşağıdaki kurallara göre düzenle ve json olarak gönderirken +90 formatına uygun hale getir:
Numara +90 ile başlıyorsa → olduğu gibi kullan.
Numara 0 ile başlıyorsa (örneğin 05XX...) → 0’ı kaldır, başına +90 ekle.
Numara 5 ile başlıyorsa (örneğin 5XX...) → doğrudan başına +90 ekle.
Numara 10 haneden kısaysa eksik kabul et ve kullanıcıdan tekrar iste.


""" + f"\nŞu an Türkiye saatiyle {hour}:{minute}. Aktif zaman dilimi: {time_range}."
            }

            # Sadece user ve assistant mesajlarını al
            filtered_messages = [msg for msg in messages if msg["role"] != "system"]

            chat_response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[system_prompt] + filtered_messages,
                temperature=0.7,
                max_tokens=600,
            )

            reply = chat_response.choices[0].message.content.strip()
            return Response({"response": reply})

        except Exception as e:
            print("HATA VAR, ", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CallMeLeadCreateAPIView(generics.CreateAPIView):
    queryset = CallMeLead.objects.all()
    serializer_class = CallMeLeadSerializer
    permission_classes = [AllowAny]
