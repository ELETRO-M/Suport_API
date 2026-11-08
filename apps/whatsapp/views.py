from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import parsers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.configuracoes.responses import resposta_sucesso
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario
from apps.whatsapp.models import ContatoWhatsApp, MensagemWhatsApp
from apps.whatsapp import services
from apps.whatsapp.serializers import ContatoWhatsAppSerializer, MensagemWhatsAppSerializer


@extend_schema(tags=["WhatsApp - Contactos"])
class ContatoWhatsAppViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ContatoWhatsAppSerializer
    filterset_fields = ("numero", "salvo_de", "tecnico")
    search_fields = ("numero", "nome", "push_name")
    ordering_fields = ("data_actualizacao", "numero")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ContatoWhatsApp.objects.none()
        qs = ContatoWhatsApp.objects.select_related("cliente", "tecnico")
        u = self.request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(tecnico=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(cliente=u)
        return qs


@extend_schema(tags=["WhatsApp - Mensagens"])
class MensagemWhatsAppViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MensagemWhatsAppSerializer
    filterset_fields = ("contato", "tipo", "from_me")
    ordering_fields = ("whatsapp_ts", "data_criacao")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return MensagemWhatsApp.objects.none()
        qs = MensagemWhatsApp.objects.select_related("contato")
        u = self.request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(contato__tecnico=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(contato__cliente=u)
        return qs


@extend_schema(tags=["WhatsApp - Chat"])
class ConversaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        qs = ContatoWhatsApp.objects.all()
        u = request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(tecnico=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(cliente=u)
        dados = []
        for c in qs:
            msgs = c.mensagens.all().order_by("-whatsapp_ts", "-data_criacao")[:1]
            dados.append({
                "numero": c.numero,
                "contato": ContatoWhatsAppSerializer(c).data,
                "total": c.mensagens.count(),
                "ultimaMensagem": MensagemWhatsAppSerializer(msgs[0]).data if msgs else None,
            })
        dados.sort(key=lambda x: (x["ultimaMensagem"] or {}).get("whatsapp_ts") or 0, reverse=True)
        return resposta_sucesso(data=dados)


@extend_schema(tags=["WhatsApp - Chat"])
@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def enviar_texto(request):
    if request.method == "GET":
        return resposta_sucesso(data={"msg": "POST com {numero, texto}"})
    numero = (request.data.get("numero") or "").strip()
    texto = (request.data.get("texto") or "").strip()
    if not services.normalizar_numero(numero) or not texto:
        return Response({"success": False, "message": 'Envie {"numero": "...", "texto": "..."}'}, status=400)
    res = services.enviar_texto(numero, texto)
    if res["status_code"] in (200, 201) and isinstance(res["data"], dict):
        c, _ = ContatoWhatsApp.objects.get_or_create(
            numero=services.normalizar_numero(numero),
            defaults={"nome": "Sem nome", "salvo_de": "manual"},
        )
        MensagemWhatsApp.objects.create(
            contato=c, message_id="", from_me=True, texto=texto, tipo="conversation",
            whatsapp_ts=None, push_name=None,
        )
    return resposta_sucesso(data=res)


@extend_schema(tags=["WhatsApp - Chat"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enviar_media(request):
    numero = (request.data.get("numero") or "").strip()
    media = request.data.get("media")
    url = request.data.get("url")
    if not services.normalizar_numero(numero) or not (media or url):
        return Response({"success": False, "message": "Envie 'media' (base64) ou 'url' (Cloudinary)"}, status=400)
    res = services.enviar_media(
        numero, media=media, url=url,
        mediatype=request.data.get("mediatype", "document"),
        mimetype=request.data.get("mimetype", "application/pdf"),
        filename=request.data.get("fileName", "documento.pdf"),
        caption=request.data.get("caption"),
    )
    return resposta_sucesso(data=res)


@extend_schema(tags=["WhatsApp - Chat"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enviar_cloudinary(request):
    numero = (request.data.get("numero") or "").strip()
    ficheiro = request.FILES.get("ficheiro")
    if not services.normalizar_numero(numero) or not ficheiro:
        return Response({"success": False, "message": "Envie numero + ficheiro (form)"}, status=400)
    try:
        url = services.subir_cloudinary(ficheiro.read(), ficheiro.name)
    except Exception as e:
        return Response({"success": False, "message": f"Falha Cloudinary: {e}"}, status=502)
    tipo = ficheiro.content_type or "application/octet-stream"
    mt = "image" if tipo.startswith("image/") else "video" if tipo.startswith("video/") else "audio" if tipo.startswith("audio/") else "document"
    res = services.enviar_media(numero, url=url, mediatype=mt, mimetype=tipo,
                                filename=getattr(ficheiro, "name", "documento"),
                                caption=request.data.get("caption"))
    return resposta_sucesso(data={"cloudinaryUrl": url, "evolution": res})


@extend_schema(tags=["WhatsApp - Webhook"])
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def webhook(request):
    payload = request.data or {}
    event = payload.get("event")
    data = payload.get("data") or {}

    if event == "connection.update":
        return resposta_sucesso(data={"event": event, "state": data.get("state")})

    if event == "messages.upsert":
        key = data.get("key") or {}
        jid = key.get("remoteJid") or ""
        if "@g.us" in jid or "broadcast" in jid or not jid:
            return resposta_sucesso(data={"ignorado": "grupo/broadcast/sem jid"})
        numero = services.normalizar_numero(jid.split("@")[0])
        if not numero:
            return resposta_sucesso(data={"ignorado": "numero invalido"})
        push_name = data.get("pushName") or ""
        from_me = bool(key.get("fromMe", False))
        texto, tipo, fn, mt = services.extrair_mensagem(data.get("message") or {})
        contato, _ = ContatoWhatsApp.objects.get_or_create(
            numero=numero,
            defaults={"nome": push_name or "Sem nome", "push_name": push_name, "salvo_de": "webhook"},
        )
        if push_name and not contato.push_name:
            contato.push_name = push_name
            contato.nome = push_name
            contato.save(update_fields=["push_name", "nome", "data_actualizacao"])
        msg = MensagemWhatsApp.objects.create(
            contato=contato, message_id=key.get("id", ""), from_me=from_me,
            texto=texto, tipo=tipo, file_name=fn, mimetype=mt,
            whatsapp_ts=data.get("messageTimestamp"), push_name=push_name,
        )
        # difunde ao vivo via WebSocket /ws/whatsapp/
        try:
            ch = get_channel_layer()
            if ch:
                async_to_sync(ch.group_send)(
                    "whatsapp_chat",
                    {"type": "whatsapp_event", "data": {"event": event, "numero": numero, "texto": texto}},
                )
        except Exception:
            pass
        # avisa notificacao ao técnico atribuído (se houver)
        if contato.tecnico_id and not from_me:
            Notificacao.objects.create(
                utilizador=contato.tecnico, tipo="whatsapp_nova_mensagem",
                titulo="Nova mensagem WhatsApp",
                mensagem=f"{contato.nome or numero}: {texto[:200]}",
                link=f"/whatsapp?numero={numero}",
            )
        return resposta_sucesso(data={
            "event": event, "contato": ContatoWhatsAppSerializer(contato).data,
            "mensagem": MensagemWhatsAppSerializer(msg).data,
        })
    return resposta_sucesso(data={"event": event})
