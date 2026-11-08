from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.configuracoes.responses import resposta_sucesso
from apps.sistema import evolution
from apps.sistema.models import Conversa, Mensagem, RespostaRapida
from apps.sistema.serializers import ConversaSerializer, MensagemSerializer, RespostaRapidaSerializer
from apps.sistema.whatsapp import registar_mensagem
from apps.usuarios.models import Usuario


class RespostaRapidaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RespostaRapidaSerializer
    filterset_fields = ("ativa",)
    search_fields = ("titulo", "texto")


class ConversaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversaSerializer
    filterset_fields = ("numero", "tecnico", "cliente")
    search_fields = ("numero", "nome")
    ordering_fields = ("ultima_mensagem_em", "data_criacao")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Conversa.objects.none()
        qs = Conversa.objects.select_related("tecnico", "cliente")
        u = self.request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(tecnico=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(cliente=u)
        return qs

    @action(detail=True, methods=["post"], url_path="atribuir")
    def atribuir(self, request, pk=None):
        inst = self.get_object()
        tecnico = Usuario.objects.filter(id=request.data.get("tecnico_id"), perfil=Usuario.PerfilChoices.TECNICO).first()
        cliente = Usuario.objects.filter(id=request.data.get("cliente_id"), perfil=Usuario.PerfilChoices.CLIENTE).first() if request.data.get("cliente_id") else None
        upd = []
        if request.data.get("tecnico_id") and tecnico is None:
            return Response({"success": False, "message": "Técnico não encontrado."}, status=400)
        if tecnico:
            inst.tecnico = tecnico; upd.append("tecnico")
        if cliente:
            inst.cliente = cliente; upd.append("cliente")
        if upd:
            inst.save(update_fields=upd)
        return resposta_sucesso(data=ConversaSerializer(inst).data)

    @action(detail=True, methods=["post"], url_path="ler")
    def ler(self, request, pk=None):
        inst = self.get_object()
        inst.nao_lidas = 0
        inst.save(update_fields=["nao_lidas"])
        return resposta_sucesso(data=ConversaSerializer(inst).data)


class MensagemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MensagemSerializer
    filterset_fields = ("conversa", "direcao", "tipo")
    ordering = ("data_criacao",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Mensagem.objects.none()
        qs = Mensagem.objects.select_related("conversa", "enviado_por")
        u = self.request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(conversa__tecnico=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(conversa__cliente=u)
        return qs


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enviar_texto(request):
    numero = (request.data.get("numero") or "").strip()
    texto = (request.data.get("texto") or "").strip()
    if not evolution.normalizar_numero(numero) or not texto:
        return Response({"success": False, "message": 'Envie {"numero": "...", "texto": "..."}'}, status=400)
    res = evolution.enviar_texto(numero, texto)
    if res["status_code"] in (200, 201) and isinstance(res["data"], dict):
        key = (res["data"].get("key") or {})
        registar_mensagem(evolution.normalizar_numero(numero), texto, Mensagem.Direcao.SAIDA,
                          wa_id=key.get("id"), usuario=request.user)
    return resposta_sucesso(data=res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enviar_media(request):
    numero = (request.data.get("numero") or "").strip()
    media = request.data.get("media")
    url = request.data.get("url")
    if not evolution.normalizar_numero(numero) or not (media or url):
        return Response({"success": False, "message": "Envie 'media' (base64) ou 'url' (Cloudinary)"}, status=400)
    res = evolution.enviar_media(
        numero, media=media, url=url,
        mediatype=request.data.get("mediatype", "document"),
        mimetype=request.data.get("mimetype", "application/pdf"),
        filename=request.data.get("fileName", "documento.pdf"),
        caption=request.data.get("caption"),
    )
    if res["status_code"] in (200, 201) and isinstance(res["data"], dict):
        key = (res["data"].get("key") or {})
        registar_mensagem(evolution.normalizar_numero(numero), request.data.get("caption", ""),
                          Mensagem.Direcao.SAIDA, wa_id=key.get("id"),
                          usuario=request.user,
                          tipo=request.data.get("mediatype", "document"),
                          file_name=request.data.get("fileName", "documento.pdf"),
                          mimetype=request.data.get("mimetype", "application/pdf"),
                          media_url=url or "")
    return resposta_sucesso(data=res)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enviar_cloudinary(request):
    numero = (request.data.get("numero") or "").strip()
    ficheiro = request.FILES.get("ficheiro")
    if not evolution.normalizar_numero(numero) or not ficheiro:
        return Response({"success": False, "message": "Envie numero + ficheiro (form)"}, status=400)
    try:
        url = evolution.subir_cloudinary(ficheiro.read(), ficheiro.name)
    except Exception as e:
        return Response({"success": False, "message": f"Falha Cloudinary: {e}"}, status=502)
    tipo = ficheiro.content_type or "application/octet-stream"
    mt = "image" if tipo.startswith("image/") else "video" if tipo.startswith("video/") else "audio" if tipo.startswith("audio/") else "document"
    res = evolution.enviar_media(numero, url=url, mediatype=mt, mimetype=tipo,
                                 filename=getattr(ficheiro, "name", "documento"),
                                 caption=request.data.get("caption"))
    if res["status_code"] in (200, 201) and isinstance(res["data"], dict):
        key = (res["data"].get("key") or {})
        registar_mensagem(evolution.normalizar_numero(numero), request.data.get("caption", "") or "",
                          Mensagem.Direcao.SAIDA, wa_id=key.get("id"),
                          usuario=request.user, tipo=mt,
                          file_name=getattr(ficheiro, "name", "documento"), mimetype=tipo,
                          media_url=url)
    return resposta_sucesso(data={"cloudinaryUrl": url, "evolution": res})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enviar_audio(request):
    """Nota de voz gravada no browser: multipart numero + ficheiro."""
    numero = (request.data.get("numero") or "").strip()
    ficheiro = request.FILES.get("ficheiro")
    if not evolution.normalizar_numero(numero) or not ficheiro:
        return Response({"success": False, "message": "Envie numero + ficheiro (form)"}, status=400)

    conteudo = ficheiro.read()
    nome = getattr(ficheiro, "name", "audio.webm")
    tipo = ficheiro.content_type or "audio/webm"

    try:
        url = evolution.subir_cloudinary(conteudo, nome)
    except Exception as e:
        return Response({"success": False, "message": f"Falha Cloudinary: {e}"}, status=502)

    res = evolution.enviar_audio(numero, url=url, conteudo=conteudo, mimetype=tipo, filename=nome)
    if res["status_code"] in (200, 201) and isinstance(res["data"], dict):
        key = (res["data"].get("key") or {})
        registar_mensagem(evolution.normalizar_numero(numero), "",
                          Mensagem.Direcao.SAIDA, wa_id=key.get("id"),
                          usuario=request.user, tipo="audio",
                          file_name=nome, mimetype=tipo, media_url=url)
    return resposta_sucesso(data={"cloudinaryUrl": url, "evolution": res})
