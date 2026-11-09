import re

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Conversa, Mensagem


def sufixo_numero(valor):
    """Ultimos 9 digitos: 244933863042, 933863042 e +244 933 863 042 dao o mesmo."""
    n = re.sub(r"\D", "", str(valor or ""))
    return n[-9:] if len(n) >= 9 else ""


def atribuir_utilizador(conversa, usuario=None):
    """Liga a conversa ao utilizador cujo telefone corresponde ao numero.

    - mensagem enviada por um tecnico -> a conversa passa a ser dele (se nao tiver dono)
    - numero da conversa == telefone de um tecnico -> conversa.tecnico (corrige se estava errado)
    - numero da conversa == telefone de um cliente -> conversa.cliente (corrige se estava errado)
    - nome vazio -> usa o nome do utilizador encontrado (nunca "Por identificar")

    Devolve o conjunto de campos alterados (ainda por gravar).
    """
    from apps.usuarios.models import Usuario

    alterados = set()

    if usuario is not None and getattr(usuario, "perfil", None) == Usuario.PerfilChoices.TECNICO:
        if conversa.tecnico_id is None:
            conversa.tecnico = usuario
            alterados.add("tecnico")

    alvo = re.sub(r"\D", "", str(conversa.numero or ""))
    if alvo:
        # pontuacao 2 = numero completo igual, 1 = mesmos 9 digitos finais
        candidatos = []
        for u in Usuario.objects.filter(
            perfil__in=(Usuario.PerfilChoices.TECNICO, Usuario.PerfilChoices.CLIENTE),
        ).only("id", "perfil", "telefone", "nome"):
            tel = re.sub(r"\D", "", str(u.telefone or ""))
            if not tel:
                continue
            if tel == alvo:
                candidatos.append((2, u))
            elif len(tel) >= 9 and len(alvo) >= 9 and tel[-9:] == alvo[-9:]:
                candidatos.append((1, u))

        candidatos.sort(key=lambda par: par[0], reverse=True)
        decidido = set()
        for _, u in candidatos:
            if u.perfil == Usuario.PerfilChoices.TECNICO and "tecnico" not in decidido:
                decidido.add("tecnico")
                if conversa.tecnico_id != u.id:
                    conversa.tecnico = u
                    alterados.add("tecnico")
            elif u.perfil == Usuario.PerfilChoices.CLIENTE and "cliente" not in decidido:
                decidido.add("cliente")
                if conversa.cliente_id != u.id:
                    conversa.cliente = u
                    alterados.add("cliente")
            if len(decidido) == 2:
                break

    if not conversa.nome:
        dono = conversa.tecnico or conversa.cliente
        if dono is not None:
            conversa.nome = dono.nome
            alterados.add("nome")

    return alterados


def registar_mensagem(numero, texto, direcao, wa_id=None, nome="", usuario=None,
                      tipo="conversation", file_name="", mimetype="", media_url=""):
    # todos os chamadores passam a gravar o numero no mesmo formato (244...)
    from apps.sistema.evolution import normalizar_numero
    numero = normalizar_numero(numero)
    if not numero:
        return None
    conversa, _ = Conversa.objects.get_or_create(numero=numero)
    entrada = direcao == Mensagem.Direcao.ENTRADA
    alterados = atribuir_utilizador(conversa, usuario)

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
            if alterados:
                conversa.save(update_fields=sorted(alterados))
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