from django.urls import re_path

from apps.sistema import consumers

websocket_urlpatterns = [
    re_path(r"ws/whatsapp/$", consumers.WhatsAppConsumer.as_asgi()),
]
