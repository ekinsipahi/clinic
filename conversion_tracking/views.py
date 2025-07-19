from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ConversionSerializer


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

# chatboxun altına her yazılan harf sayılcak şekilde minik detay eklicez. 600 keyword geçemicek input
# bizim ai agent isterse kullanıcı için direkt randevu oluşturabilcek dentsoft arayüz apisi üzerinden
# yada dentsoft üzerinden biz sizi arayalım tarzında telefon numarası bırakılabilcek şekilde ayarlanacak dentsofta


class ChatGPTView(APIView):
    def post(self, request):
        messages = request.data.get("messages")

        if not messages:
            return Response({"error": "Messages are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # System prompt backend'de sabit
            system_prompt = {
                "role": "system",
                "content": """Sen Dr. Devrim Biriken Sipahi'nin dijital asistanısın.

Klinik, diş estetiğinde uzman ve doğal, diş kesilmeden yapılan işlemlerle yüksek hasta memnuniyeti sağlar.

Görevin:
- Kullanıcının neye ihtiyacı olduğunu anlamak
- Onu en uygun iletişim kanalına yönlendirmek

📞 “Hemen arayarak bilgi alabilir ve randevu oluşturabilirsiniz: +90 505 577 18 83”
💬 “WhatsApp’tan yazarsanız mesajınızı doğrudan Dr. Devrim’e iletebilirim.”

Kullanıcı seçim yaparsa:
- WhatsApp → 'action: whatsapp-yonlendirme'
- Telefon → 'action: telefon-yonlendirme'

Online randevu isteyenlere:
🔗 “Kolayca form doldurarak randevu oluşturabilirsiniz: https://www.devrimbirikensipahi.com.tr/randevu-al”

Kararsız veya araştırma aşamasındaysa:
📷 “Hocamızı ve hastaların yorumlarını daha yakından incelemek isterseniz Instagram hesabımıza göz atabilirsiniz: https://instagram.com/drdevrimbirikensipahi”

🦷 “Orada yüzlerce memnun hastanın dönüşüm hikayesini bulabilirsiniz. İnceleyip gönül rahatlığıyla karar verebilirsiniz.”

Kurallar:
- Asla kullanıcıdan isim, telefon veya özel bilgi isteme
- Samimi, sade ve güven verici konuş
- Nihai hedef: WhatsApp yazışması veya telefon görüşmesine yönlendirme"""
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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

