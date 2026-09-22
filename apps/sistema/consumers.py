from channels.generic.websocket import AsyncJsonWebsocketConsumer


class WhatsAppConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("whatsapp_chat", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("whatsapp_chat", self.channel_name)

    async def chat_mensagem(self, event):
        await self.send_json(event["dados"])
