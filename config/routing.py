from django.urls import path

from apps.intervencoes.consumers import (
    AnexoIntervencaoConsumer,
    ComentarioIntervencaoConsumer,
)
from apps.notificacoes.consumers import NotificacaoConsumer


websocket_urlpatterns = [
    path("ws/notificacoes/", NotificacaoConsumer.as_asgi()),
    path(
        "ws/intervencoes/<uuid:intervencao_id>/comentarios/",
        ComentarioIntervencaoConsumer.as_asgi(),
    ),
    path(
        "ws/intervencoes/<uuid:intervencao_id>/anexos/",
        AnexoIntervencaoConsumer.as_asgi(),
    ),
]
