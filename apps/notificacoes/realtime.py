from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def enviar_notificacao_ws(notificacao):
    channel_layer = get_channel_layer()
    if not channel_layer or not notificacao.utilizador_id:
        return

    async_to_sync(channel_layer.group_send)(
        f"notificacoes_{notificacao.utilizador_id}",
        {
            "type": "notificacao.criada",
            "data": {
                "id": str(notificacao.id),
                "tipo": notificacao.tipo,
                "titulo": notificacao.titulo,
                "mensagem": notificacao.mensagem,
                "link": notificacao.link,
                "lida": notificacao.lida,
                "data_criacao": notificacao.data_criacao.isoformat(),
            },
        },
    )
