from django.urls import path
from .views import ConversionTrackingView, ChatGPTView 

urlpatterns = [
    path('conversion-tracking/', ConversionTrackingView.as_view(), name='conversion-tracking'),
    path('ai-agent/', ChatGPTView.as_view(), name="chatgpt-endpoint"),
]
