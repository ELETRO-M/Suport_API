from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings

from apps.intervencoes.models import AnexoIntervencao, ComentarioIntervencao, Intervencao
from apps.configuracoes.firebase import publicar_anexo, publicar_comentario, publicar_notificacao, remover_comentario
from apps.configuracoes.notificar import notificar_async, notificar_documento_async
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario


@receiver(pre_save, sender=Intervencao)
def guardar_intervencao_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._intervencao_anterior = Intervencao.all_objects.get(pk=instance.pk)
        except Intervencao.DoesNotExist:
            instance._intervencao_anterior = None


@receiver(post_save, sender=Intervencao)
def criar_notificacao_admins(sender, instance, created, **kwargs):

    if not created:
        anterior = getattr(instance, "_intervencao_anterior", None)
        ator = getattr(instance, "_utilizador_acao", None)
        if anterior:
            _notificar_cliente_alteracao(instance, anterior, ator)
        if (
            anterior
            and instance.status != anterior.status
            and instance.status in {
                Intervencao.StatusChoices.CONCLUIDO,
                Intervencao.StatusChoices.FECHADO,
            }
            and ator
            and ator.perfil == Usuario.PerfilChoices.TECNICO
        ):
            _notificar_validar(instance, ator)
        return

    if created:


        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )

        if instance.cliente.empresa and instance.cliente.empresa.telefone:
            notificar_async(
                numero=instance.cliente.empresa.telefone,
                texto=(
                    f"🔧 *Nova intervenção criada no SOSTICKET*\n\n"
                    f"🏢 *Empresa:* {instance.cliente.empresa.nome}\n"
                    f"🆔 *Nº:* {instance.numero}\n"
                    f"📋 *Título:* {instance.titulo}\n"
                    f"📝 *Descrição:* {instance.descricao}\n"
                    f"⚠️ *Prioridade:* {instance.get_prioridade_display()}\n"
                    f"👤 *Aberto por:* {instance.cliente.nome}\n\n"
                    f"*Para mais detalhes:* entre em contato com o utilizador {instance.cliente.nome} pelo telefone {instance.cliente.telefone} ou pelo email {instance.cliente.email}"
                ),
            )

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo=f"Nova intervenção na empresa {instance.cliente.empresa.nome}",
                mensagem=f"A intervenção {instance.titulo} na empresa {instance.cliente.empresa.nome} pelo cliente {instance.cliente.nome}.",
            )
            if admin.telefone:
                tecnico_nome = instance.tecnico.nome if instance.tecnico else "Ainda não atribuído"
                contrato_info = instance.contrato.tipo_contrato if instance.contrato else "Sem contrato"
                notificar_async(
                    numero=admin.telefone,
                    texto=(
                        f"🚨 *NOVA INTERVENÇÃO* 🚨\n\n"
                        f"🏢 *Empresa:* {instance.cliente.empresa.nome}\n"
                        f"🆔 *Nº:* {instance.numero}\n"
                        f"📋 *Título:* {instance.titulo}\n"
                        f"📝 *Descrição:* {instance.descricao}\n"
                        f"⚠️ *Prioridade:* {instance.get_prioridade_display()}\n"
                        f"🔧 *Tipo de atuação:* {instance.get_actuacao_tipo_display()}\n"
                        f"📄 *Contrato:* {contrato_info}\n"
                        f"👷 *Técnico:* {tecnico_nome}\n"
                        f"👤 *Solicitado por:* {instance.cliente.nome}\n"
                        f"📞 *Contacto:* {instance.cliente.telefone} | {instance.cliente.email}\n"
                        f"🕐 *Abertura:* {instance.data_abertura.strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"_Acompanhe os detalhes pelo sistema._"
                    ),
                )
                   
               

        


@receiver(post_save, sender=ComentarioIntervencao)
def publicar_comentario_firebase(sender, instance, created, **kwargs):
    publicar_comentario(instance)


@receiver(post_delete, sender=ComentarioIntervencao)
def remover_comentario_firebase(sender, instance, **kwargs):
    remover_comentario(instance)


def _formatar_data(valor):
    return valor.strftime("%d/%m/%Y %H:%M") if valor else "—"


def _notificar_cliente_alteracao(instance, anterior, ator):
    cliente = instance.cliente
    if not cliente or (ator and cliente.id == ator.id):
        return

    alteracoes = []

    if instance.tecnico_id != anterior.tecnico_id:
        if instance.tecnico:
            alteracoes.append(f"👷 Técnico atribuído: {instance.tecnico.nome}")
        else:
            alteracoes.append("👷 Técnico removido")

    if instance.status != anterior.status:
        alteracoes.append(
            f"📊 Status: {anterior.get_status_display()} → {instance.get_status_display()}"
        )

    if instance.estado != anterior.estado:
        alteracoes.append(
            f"🚦 Estado: {anterior.get_estado_display()} → {instance.get_estado_display()}"
        )

    if instance.prioridade != anterior.prioridade:
        alteracoes.append(
            f"⚠️ Prioridade: {anterior.get_prioridade_display()} → {instance.get_prioridade_display()}"
        )

    if instance.actuacao_tipo != anterior.actuacao_tipo:
        alteracoes.append(
            f"🔧 Tipo de atuação: {anterior.get_actuacao_tipo_display()} → {instance.get_actuacao_tipo_display()}"
        )

    if instance.data_inicio_intervencao != anterior.data_inicio_intervencao:
        alteracoes.append(
            f"🕐 Início: {_formatar_data(instance.data_inicio_intervencao)}"
        )

    if instance.data_fim_intervencao != anterior.data_fim_intervencao:
        alteracoes.append(
            f"🕐 Fim: {_formatar_data(instance.data_fim_intervencao)}"
        )

    if instance.titulo != anterior.titulo:
        alteracoes.append(f"📋 Título: {instance.titulo}")

    if instance.descricao != anterior.descricao:
        alteracoes.append("📝 Descrição atualizada")

    if instance.contrato_id != anterior.contrato_id:
        contrato = instance.contrato.tipo_contrato if instance.contrato else "Sem contrato"
        alteracoes.append(f"📄 Contrato: {contrato}")

    if not alteracoes:
        return

    empresa_nome = cliente.empresa.nome if cliente.empresa else "—"
    titulo = f"Intervenção {instance.numero} atualizada"
    mensagem = (
        f"A intervenção {instance.numero} ({instance.titulo}) foi atualizada.\n"
        + "\n".join(f"- {alteracao}" for alteracao in alteracoes)
    )

    Notificacao.objects.create(
        utilizador=cliente,
        tipo="atualizacao_intervencao",
        titulo=titulo,
        mensagem=mensagem,
        link=f"/intervencoes/{instance.id}",
    )

    texto = (
        f"🔔 *Intervenção atualizada*\n\n"
        f"🆔 *Nº:* {instance.numero}\n"
        f"📋 *Título:* {instance.titulo}\n"
        f"🏢 *Empresa:* {empresa_nome}\n\n"
        + "\n".join(alteracoes)
        + f"\n\n👤 *Atualizado por:* {ator.nome if ator else 'Sistema'}"
    )

    numeros = set()
    if cliente.telefone:
        numeros.add(cliente.telefone)
    if cliente.empresa and cliente.empresa.telefone:
        numeros.add(cliente.empresa.telefone)

    for numero in numeros:
        notificar_async(numero=numero, texto=texto)


def _notificar_validar(instance, ator):
    admins = Usuario.objects.filter(
        perfil=Usuario.PerfilChoices.ADMIN,
        is_deleted=False,
        status=Usuario.StatusChoices.ACTIVO,
    )

    status_texto = dict(Intervencao.StatusChoices.choices).get(instance.status, instance.status)
    titulo = "Intervenção concluída — aguarda validação"
    mensagem = (
        f"A intervenção {instance.numero} ({instance.titulo}) foi concluída pelo técnico "
        f"{ator.nome} e aguarda validação."
    )
    texto = (
        f"🔔 *Intervenção concluída — aguarda validação*\n\n"
        f"🆔 *Nº:* {instance.numero}\n"
        f"📋 *Título:* {instance.titulo}\n"
        f"👷 *Técnico:* {ator.nome}\n"
        f"📊 *Status:* {status_texto}\n"
        f"🕐 *Concluída em:* {instance.data_conclusao.strftime('%d/%m/%Y %H:%M') if instance.data_conclusao else '—'}\n\n"
        f"_Valide a conclusão pelo sistema._"
    )

    for admin in admins:
        Notificacao.objects.create(
            utilizador=admin,
            tipo="sistema",
            titulo=titulo,
            mensagem=mensagem,
            link=f"{settings.SITE_URL}/api/v1/intervencoes/{instance.id}/",
        )
        if admin.telefone:
            notificar_async(numero=admin.telefone, texto=texto)


@receiver(post_save, sender=AnexoIntervencao)
def publicar_anexo_firebase(sender, instance, created, **kwargs):
    if created:
        publicar_anexo(instance)
        _notificar_anexo(instance)


def _notificar_anexo(instance):
    intervencao = instance.intervencao
    nome_arquivo = str(instance.arquivo.name or "").split("/")[-1]

    utilizadores = {instance.utilizador, intervencao.cliente, intervencao.tecnico}
    utilizadores.discard(None)
    admins = Usuario.objects.filter(
        perfil=Usuario.PerfilChoices.ADMIN,
        is_deleted=False,
        status=Usuario.StatusChoices.ACTIVO,
    )
    for admin in admins:
        utilizadores.add(admin)

    titulo = "Novo documento anexado"
    mensagem = f"Foi anexado o documento '{nome_arquivo}' à intervenção {intervencao.numero} ({intervencao.titulo})."

    for utilizador in utilizadores:
        Notificacao.objects.create(
            utilizador=utilizador,
            tipo="sistema",
            titulo=titulo,
            mensagem=mensagem,
            link=f"{settings.SITE_URL}/api/v1/intervencoes/{intervencao.id}/",
        )

    numeros = {u.telefone for u in utilizadores if u.telefone}
    empresa = intervencao.cliente.empresa
    if empresa and empresa.telefone:
        numeros.add(empresa.telefone)

    legenda = (
        f"📎 *Documento anexado*\n\n"
        f"🆔 *Intervenção:* {intervencao.numero}\n"
        f"📋 *Título:* {intervencao.titulo}\n"
        f"📄 *Arquivo:* {nome_arquivo}\n"
        f"📝 *Descrição:* {instance.descricao or '—'}"
    )

    for numero in numeros:
        notificar_documento_async(
            numero=numero,
            arquivo_url=instance.arquivo.url,
            nome_arquivo=nome_arquivo,
            descricao=legenda,
        )
