from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Conversa, Mensagem


def registar_mensagem(numero, texto, direcao, wa_id=None, nome="", usuario=None,
                      tipo="conversation", file_name="", mimetype="", media_url=""):
    conversa, _ = Conversa.objects.get_or_create(numero=numero)
    entrada = direcao == Mensagem.Direcao.ENTRADA

    if wa_id:
        msg, criada = Mensagem.objects.get_or_create(
            wa_id=wa_id,
            defaults=dict(conversa=conversa, direcao=direcao, texto=texto, enviado_por=usuario,
                          tipo=tipo, file_name=file_name, mimetype=mimetype, media_url=media_url),
        )
        if not criada:
            # a Evolution devolve as mensagens enviadas pela API no webhook: evita duplicados
            if usuario and not msg.enviado_por:
                msg.enviado_por = usuario
                msg.save(update_fields=["enviado_por"])
            return msg
    else:
        msg = Mensagem.objects.create(
            conversa=conversa, direcao=direcao, texto=texto, enviado_por=usuario,
            tipo=tipo, file_name=file_name, mimetype=mimetype, media_url=media_url,
        )

    if nome and entrada and not conversa.nome:
        conversa.nome = nome
    conversa.ultima_mensagem = texto[:200]
    conversa.ultima_mensagem_em = timezone.now()
    if entrada:
        conversa.nao_lidas += 1
    conversa.save()

    # Broadcast para o WebSocket: nunca deve derrubar o webhook se o Redis estiver fora
    try:
        async_to_sync(get_channel_layer().group_send)(
            "whatsapp_chat",
            {
                "type": "chat.mensagem",
                "dados": {
                    "id": str(msg.id),
                    "wa_id": wa_id or "",
                    "conversa_id": str(conversa.id),
                    "numero": conversa.numero,
                    "nome": conversa.nome,
                    "texto": texto,
                    "direcao": direcao,
                    "tipo": tipo,
                    "file_name": file_name,
                    "mimetype": mimetype,
                    "media_url": media_url,
                    "enviado_por": usuario.nome if usuario else None,
                    "data_hora": timezone.now().isoformat(),
                },
            },
        )
    except Exception:
        pass
    return msg