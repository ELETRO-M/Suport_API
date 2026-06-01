import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.intervencoes.models import Intervencao
from apps.usuarios.models import Usuario


@database_sync_to_async
def pode_aceder_intervencao(user, intervencao_id):
    if user.is_anonymous:
        return False
    if user.perfil == Usuario.PerfilChoices.ADMIN:
        return True
    return Intervencao.objects.filter(
        id=intervencao_id,
    ).filter(
        cliente_id=user.id
    ).exists() or Intervencao.objects.filter(
        id=intervencao_id,
        tecnico_id=user.id,
    ).exists()


class ComentarioIntervencaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.intervencao_id = self.scope["url_route"]["kwargs"]["intervencao_id"]
        autorizado = await pode_aceder_intervencao(
            self.scope["user"], self.intervencao_id
        )
        if not autorizado:
            await self.close()
            return

        self.group_name = f"intervencao_{self.intervencao_id}_comentarios"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def comentario_criado(self, event):
        await self.send(text_data=json.dumps(event["data"]))


class AnexoIntervencaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.intervencao_id = self.scope["url_route"]["kwargs"]["intervencao_id"]
        autorizado = await pode_aceder_intervencao(
            self.scope["user"], self.intervencao_id
        )
        if not autorizado:
            await self.close()
            return

        self.group_name = f"intervencao_{self.intervencao_id}_anexos"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def anexo_criado(self, event):
        await self.send(text_data=json.dumps(event["data"]))
