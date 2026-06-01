from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def enviar_comentario_ws(comentario):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"intervencao_{comentario.intervencao_id}_comentarios",
        {
            "type": "comentario.criado",
            "data": {
                "id": str(comentario.id),
                "intervencao_id": str(comentario.intervencao_id),
                "usuario_nome": comentario.usuario.nome,
                "texto": comentario.texto,
                "visivel_cliente": comentario.visivel_cliente,
                "data_criacao": comentario.data_criacao.isoformat(),
            },
        },
    )


def enviar_anexo_ws(anexo):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        f"intervencao_{anexo.intervencao_id}_anexos",
        {
            "type": "anexo.criado",
            "data": {
                "id": str(anexo.id),
                "intervencao_id": str(anexo.intervencao_id),
                "utilizador_id": str(anexo.utilizador_id) if anexo.utilizador_id else None,
                "utilizador_nome": anexo.utilizador.nome if anexo.utilizador else None,
                "arquivo": anexo.arquivo.url if anexo.arquivo else None,
                "nome_arquivo": anexo.arquivo.name.split("/")[-1] if anexo.arquivo else None,
                "descricao": anexo.descricao,
                "tamanho": anexo.tamanho,
                "data_criacao": anexo.data_criacao.isoformat(),
            },
        },
    )
