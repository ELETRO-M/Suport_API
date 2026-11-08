import hmac

from django.conf import settings
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.sistema.models import ConfiguracaoSistema, Mensagem
from apps.sistema.serializers import ConfiguracaoSistemaSerializer
from apps.sistema.whatsapp import registar_mensagem

from drf_spectacular.utils import extend_schema
@extend_schema(tags=["Configurações"])
class ConfiguracaoSistemaViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = ConfiguracaoSistemaSerializer
    queryset = ConfiguracaoSistema.objects.all()

    def list(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = self.get_serializer(ConfiguracaoSistema.load())
        return resposta_sucesso(data=serializer.data)

    def update(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        configuracao = ConfiguracaoSistema.load()
        serializer = self.get_serializer(configuracao, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return resposta_sucesso(message="Configurações atualizadas com sucesso")


class WebhookWhatsApp(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token_esperado = settings.WHATSAPP_WEBHOOK_TOKEN
        token = request.headers.get("X-Webhook-Token", "")
        if not token_esperado or not hmac.compare_digest(token, token_esperado):
            return Response(status=403)

        corpo = request.data
        if corpo.get("event") != "messages.upsert":
            return Response({"ignorado": True})

        data = corpo.get("data", {})
        key = data.get("key", {})

        jid = key.get("remoteJid", "")
        if jid.endswith("@lid"):  # versões recentes podem enviar o número real aqui
            jid = key.get("remoteJidAlt", jid)
        if not jid.endswith("@s.whatsapp.net"):  # ignora grupos e estados
            return Response({"ignorado": True})

        msg = data.get("message", {})
        from apps.sistema.evolution import extrair_mensagem, subir_cloudinary
        texto, tipo, file_name, mimetype = extrair_mensagem(msg)
        texto = texto or f"[{data.get('messageType', 'mídia')}]"

        # Ficheiro com base64 (foto/documento/áudio/vídeo) → Cloudinary, pra preview no chat
        media_url = ""
        base64 = msg.get("base64") or data.get("base64") or ""
        if base64 and tipo in ("document", "image", "video", "audio"):
            try:
                import base64 as b64mod
                raw = base64.split(",", 1)[-1] if "," in base64 else base64
                if len(raw) > 20:
                    blob = b64mod.b64decode(raw, validate=False)
                    media_url = subir_cloudinary(blob, file_name or f"{tipo}.bin")
            except Exception:
                media_url = ""

        registar_mensagem(
            numero=jid.split("@")[0],
            texto=texto,
            direcao=Mensagem.Direcao.SAIDA if key.get("fromMe") else Mensagem.Direcao.ENTRADA,
            wa_id=key.get("id"),
            nome=data.get("pushName", ""),
            tipo=tipo, file_name=file_name, mimetype=mimetype, media_url=media_url,
        )
        return resposta_sucesso(message="sucesso na Requisição")