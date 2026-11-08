from channels.generic.websocket import AsyncJsonWebsocketConsumer


class WhatsAppConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group_name = "whatsapp_chat"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "ligado", "msg": "ligado ao WS", "total": 1})

    async def disconnect(self, event):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        pass

    async def whatsapp_event(self, event):
        await self.send_json(event["data"])
