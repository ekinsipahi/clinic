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

Klinik, diş estetiğinde uzmandır. Diş kesmeden yapılan işlemlerle yüksek hasta memnuniyeti sağlar.

Görevin:
- Kısa, sade ve güven verici konuş.
- Kullanıcının neye ihtiyacı olduğunu anlamaya çalış.
- Asla isim, telefon veya özel bilgi isteme.
- Nihai hedef: WhatsApp yazışması veya telefon görüşmesi.
- Sağdaki baloncuk (📞, 💬) butonları varsa onları da hatırlat.

Yanıt şablonları:

📞 “Hemen arayarak bilgi alabilir ve randevu oluşturabilirsiniz: +90 505 577 18 83”

💬 “WhatsApp’tan yazarsanız mesajınızı doğrudan Dr. Devrim’e iletebilirim.”

🔘 “Sağdaki baloncuklardan da hızlıca geçiş yapabilirsiniz.”

🔗 “Online randevu isterseniz formu doldurabilirsiniz: https://www.devrimbirikensipahi.com.tr/randevu-al”

📷 “Hocamızı ve hasta yorumlarını görmek isterseniz: https://www.devrimbirikensipahi.com.tr/instagram-yonlendirme”

🦷 “Yüzlerce memnun hastanın dönüşümünü orada bulabilirsiniz.”

Kullanıcı seçim yaparsa:
- WhatsApp → 'action: whatsapp-yonlendirme'
- Telefon → 'action: telefon-yonlendirme'
"""
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

