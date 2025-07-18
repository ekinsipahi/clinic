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
            chat_response = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            reply = chat_response.choices[0].message.content.strip()
            return Response({"response": reply})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

