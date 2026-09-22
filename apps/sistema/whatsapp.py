from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Conversa, Mensagem


def registar_mensagem(numero, texto, direcao, wa_id=None, nome="", usuario=None):
    conversa, _ = Conversa.objects.get_or_create(numero=numero)
    entrada = direcao == Mensagem.Direcao.ENTRADA

    if wa_id:
        msg, criada = Mensagem.objects.get_or_create(
            wa_id=wa_id,
            defaults=dict(conversa=conversa, direcao=direcao, texto=texto, enviado_por=usuario),
        )
        if not criada:
            # a Evolution devolve as mensagens enviadas pela API no webhook: evita duplicados
            if usuario and not msg.enviado_por:
                msg.enviado_por = usuario
                msg.save(update_fields=["enviado_por"])
            return msg
    else:
        msg = Mensagem.objects.create(
            conversa=conversa, direcao=direcao, texto=texto, enviado_por=usuario
        )

    if nome and entrada and not conversa.nome:
        conversa.nome = nome
    conversa.ultima_mensagem = texto[:200]
    conversa.ultima_mensagem_em = timezone.now()
    if entrada:
        conversa.nao_lidas += 1
    conversa.save()

    async_to_sync(get_channel_layer().group_send)(
        "whatsapp_chat",
        {
            "type": "chat.mensagem",
            "dados": {
                "conversa_id": str(conversa.id),
                "numero": conversa.numero,
                "nome": conversa.nome,
                "texto": texto,
                "direcao": direcao,
                "enviado_por": usuario.nome if usuario else None,
                "data_hora": timezone.now().isoformat(),
            },
        },
    )
    return msg