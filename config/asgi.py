import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from apps.whatsapp.consumers import WhatsAppConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/whatsapp/", WhatsAppConsumer.as_asgi()),
            path("ws/whatsapp", WhatsAppConsumer.as_asgi()),
        ])
    ),
})
