from django.urls import path
from .views import ConversionTrackingView

urlpatterns = [
    path('conversion-tracking/', ConversionTrackingView.as_view(), name='conversion-tracking'),
]
