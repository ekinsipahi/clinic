from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ConversionSerializer
from rest_framework import generics
from rest_framework.permissions import AllowAny
from clinic.models import CallMeLead
from .serializers import CallMeLeadSerializer
from datetime import datetime
import pytz


from openai import OpenAI

client = OpenAI(
  api_key="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"
)


class ConversionTrackingView(APIView):
    def post(self, request):
        serializer = ConversionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 404 sayfası eklenecek, indexlenebilir gene schema.org ile search console'a eklencek.
# dentsoft ile randevu-al kısmı eklendikten sonra
# son olarak blog kısmına başlayacağız ve otomatize edeceğiz bu blog yazılarını.




# resimlerin bi ksmında hala lazy loading animasyonu yok.
# spam trafiğe karşı korumamız yok! gpt bot kafayı yiyebilir.
# ip addresleride toplayalım bence.


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
