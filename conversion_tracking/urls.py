from django.urls import path
from .views import ConversionTrackingView, ChatGPTView, CallMeLeadCreateAPIView, ConversionActuallyCalledView

urlpatterns = [
    path('conversion-tracking/', ConversionTrackingView.as_view(), name='conversion-tracking'),
    path('conversion-tracking/actual-call/', ConversionActuallyCalledView.as_view(), name='conversion-tracking-actual-call'),
    path('ai-agent/', ChatGPTView.as_view(), name="chatgpt-endpoint"),
    path('ai-callme-lead/', CallMeLeadCreateAPIView.as_view(), name="callme-lead-create"),
]
