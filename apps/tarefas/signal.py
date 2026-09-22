from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.configuracoes.whatsapp import enviar_whatsapp
from apps.notificacoes.models import Notificacao
from apps.tarefas.models import ComentarioTarefa, Tarefa
from apps.usuarios.models import Usuario


def _fmt_data(data):
    return data.strftime("%d/%m/%Y %H:%M") if data else "—"


def _prazo_texto(tarefa):
    if tarefa.estado in (Tarefa.EstadoChoices.CONCLUIDA, Tarefa.EstadoChoices.CANCELADA):
        return "—"
    prazo = tarefa.prazo
    if not prazo:
        return "—"
    if prazo["expirado"]:
        return "EXPIRADO"
    horas = prazo["restantes_horas"]
    if horas >= 24:
        return f"{round(horas / 24, 1)} dias ({horas} h)"
    return f"{horas} h"


def _nome(tarefa, tecnico=None):
    if tecnico:
        return tecnico.nome
    if tarefa.atribuido_a_id:
        return tarefa.atribuido_a.nome
    return "—"


def _detalhe_completo(tarefa, tecnico=None):
    prioridades = dict(Tarefa.PrioridadeChoices.choices)
    intervencao = tarefa.intervencao
    intervencao_txt = f"{intervencao.numero} - {intervencao.titulo}" if intervencao else "—"
    descricao = (tarefa.descricao[:200] + "…") if len(tarefa.descricao) > 200 else tarefa.descricao
    return (
        f"🔢 *Número:* {tarefa.numero}\n"
        f"📌 *Título:* {tarefa.titulo}\n"
        f"📝 *Descrição:* {descricao or '—'}\n"
        f"⚠️ *Prioridade:* {prioridades.get(tarefa.prioridade, tarefa.prioridade)}\n"
        f"📊 *Estado:* {dict(Tarefa.EstadoChoices.choices).get(tarefa.estado, tarefa.estado)}\n"
        f"👤 *Técnico:* {_nome(tarefa, tecnico)}\n"
        f"🛠️ *Criada por:* {tarefa.criado_por.nome if tarefa.criado_por else '—'}\n"
        f"🚦 *Início:* {_fmt_data(tarefa.data_inicio)}\n"
        f"⏰ *Prazo (fim):* {_fmt_data(tarefa.data_fim)}\n"
        f"⏳ *Prazo restante:* {_prazo_texto(tarefa)}\n"
        f"✅ *Concluída em:* {_fmt_data(tarefa.data_conclusao)}\n"
        f"📎 *Intervenção:* {intervencao_txt}"
    )


def _notificar(tarefa, utilizador, titulo, mensagem, texto_whatsapp):
    if not utilizador:
        return
    Notificacao.objects.create(
        utilizador=utilizador,
        tipo="tarefa",
        titulo=titulo,
        mensagem=mensagem,
        link=f"/tarefas/{tarefa.id}",
    )
    if utilizador.telefone:
        enviar_whatsapp(numero=utilizador.telefone, texto=texto_whatsapp)


@receiver(pre_save, sender=Tarefa)
def guardar_tarefa_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._tarefa_anterior = Tarefa.all_objects.get(pk=instance.pk)
        except Tarefa.DoesNotExist:
            instance._tarefa_anterior = None


@receiver(post_save, sender=Tarefa)
def notificar_tarefa(sender, instance, created, **kwargs):
    anterior = getattr(instance, "_tarefa_anterior", None)
    ator = getattr(instance, "_utilizador_acao", None)

    if created:
        if instance.atribuido_a_id:
            _notificar(
                instance,
                instance.atribuido_a,
                titulo="Nova tarefa atribuída",
                mensagem=f"Foi-lhe atribuída uma nova tarefa.\n\n{_detalhe_completo(instance)}",
                texto_whatsapp=(
                    f"✅ *Nova tarefa atribuída*\n\n"
                    f"Olá, {instance.atribuido_a.nome}!\n\n{_detalhe_completo(instance)}"
                ),
            )
        return

    if anterior is None:
        return

    atribuicao_mudou = (
        instance.atribuido_a_id
        and instance.atribuido_a_id != anterior.atribuido_a_id
    )
    if atribuicao_mudou:
        _notificar(
            instance,
            instance.atribuido_a,
            titulo="Nova tarefa atribuída",
            mensagem=f"Foi-lhe atribuída uma nova tarefa.\n\n{_detalhe_completo(instance)}",
            texto_whatsapp=(
                f"✅ *Nova tarefa atribuída*\n\n"
                f"Olá, {instance.atribuido_a.nome}!\n\n{_detalhe_completo(instance)}"
            ),
        )

    estado_mudou = instance.estado != anterior.estado
    if not estado_mudou:
        return

    novo_estado = instance.estado

    if novo_estado == Tarefa.EstadoChoices.CONCLUIDA:
        if ator and ator.perfil == Usuario.PerfilChoices.TECNICO:
            admins = Usuario.objects.filter(
                perfil=Usuario.PerfilChoices.ADMIN,
                is_deleted=False,
                status=Usuario.StatusChoices.ACTIVO,
            )
            titulo = "Tarefa concluída — aguarda validação"
            mensagem = (
                f"A tarefa {instance.numero} foi concluída pelo técnico {ator.nome} "
                f"e aguarda validação.\n\n{_detalhe_completo(instance, ator)}"
            )
            texto = (
                f"🔔 *Tarefa concluída — aguarda validação*\n\n"
                f"{ator.nome} concluiu a tarefa:\n\n{_detalhe_completo(instance, ator)}"
            )
            for admin in admins:
                _notificar(instance, admin, titulo, mensagem, texto)
        else:
            destino = instance.atribuido_a
            titulo = "Tarefa concluída"
            mensagem = f"A tarefa {instance.numero} foi concluída.\n\n{_detalhe_completo(instance)}"
            texto = f"🎉 *Tarefa concluída*\n\n{_detalhe_completo(instance)}"
            if destino and destino.id != getattr(ator, "id", None):
                _notificar(instance, destino, titulo, mensagem, texto)

    elif novo_estado == Tarefa.EstadoChoices.CANCELADA:
        destino = instance.atribuido_a
        if destino and destino.id != getattr(ator, "id", None):
            _notificar(
                instance,
                destino,
                titulo="Tarefa cancelada",
                mensagem=f"A tarefa {instance.numero} foi cancelada.\n\n{_detalhe_completo(instance)}",
                texto_whatsapp=f"🚫 *Tarefa cancelada*\n\n{_detalhe_completo(instance)}",
            )

    elif novo_estado == Tarefa.EstadoChoices.EXPIRADO:
        if instance.criado_por and instance.criado_por.id != getattr(ator, "id", None):
            _notificar(
                instance,
                instance.criado_por,
                titulo="Tarefa expirada",
                mensagem=f"A tarefa {instance.numero} expirou.\n\n{_detalhe_completo(instance)}",
                texto_whatsapp=f"⏰ *Tarefa expirada*\n\n{_detalhe_completo(instance)}",
            )


@receiver(post_save, sender=ComentarioTarefa)
def notificar_comentario(sender, instance, created, **kwargs):
    if not created:
        return
    tarefa = instance.tarefa
    autor = instance.utilizador
    if autor and autor.perfil == Usuario.PerfilChoices.TECNICO:
        destino = tarefa.criado_por
    else:
        destino = tarefa.atribuido_a
    if not destino or destino.id == getattr(autor, "id", None):
        return
    _notificar(
        tarefa,
        destino,
        titulo="Novo comentário na tarefa",
        mensagem=f"Foi adicionado um comentário na tarefa {tarefa.numero}.",
        texto_whatsapp=(
            f"💬 *Novo comentário na tarefa {tarefa.numero}*\n\n"
            f"{autor.nome if autor else '—'}: {instance.texto}"
        ),
    )