from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

from apps.whatsapp.consumers import WhatsAppConsumer

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/whatsapp/", WhatsAppConsumer.as_asgi()),
            path("ws/whatsapp", WhatsAppConsumer.as_asgi()),
        ])
    ),
})
