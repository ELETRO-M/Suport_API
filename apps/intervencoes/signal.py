from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings

from apps.intervencoes.models import AnexoIntervencao, ComentarioIntervencao, Intervencao
from apps.configuracoes.firebase import publicar_anexo, publicar_comentario, publicar_notificacao, remover_comentario
from apps.configuracoes.whatsapp import enviar_whatsapp, enviar_whatsapp_documento
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
            enviar_whatsapp(
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
                enviar_whatsapp(
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
            enviar_whatsapp(numero=admin.telefone, texto=texto)


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
        enviar_whatsapp_documento(
            numero=numero,
            arquivo_url=instance.arquivo.url,
            nome_arquivo=nome_arquivo,
            descricao=legenda,
        )
