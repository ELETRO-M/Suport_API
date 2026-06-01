from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from apps.intervencoes.models import AnexoIntervencao, ComentarioIntervencao, Intervencao
from apps.intervencoes.realtime import enviar_anexo_ws, enviar_comentario_ws
from apps.notificacoes.models import Notificacao
from apps.notificacoes.realtime import enviar_notificacao_ws
from apps.usuarios.models import Usuario


@receiver(post_save, sender=Intervencao)
def criar_notificacao_admins(sender, instance, created, **kwargs):

    if created:

        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )

        notificacoes = []

        for admin in admins:

            notificacoes.append(
                Notificacao(
                    utilizador=admin,
                    tipo="sistema",
                    titulo="Nova intervenção",
                    mensagem=f"A intervenção {instance.titulo} na empresa {instance.cliente.empresa.nome}  pelo cliente {instance.cliente.nome}.",
                    link=f"{settings.SITE_URL}/api/v1/intervencoes/{instance.id}/",
                )
            )
            """
        send_mail(
                subject="Criação de Nova Intervenção",
                message=(
                    f"Olá, caro admin da empresa{utilizador.empresa.nome}\n\n"
                    "Foi criada uma nova intervenção na empresa.\n\n"
                    f"Intervenção: {instance.titulo}\n"
                    f"Pelo Utilizador: {instance.cliente.nome}\n"
                    f"Descrição: {instance.descricao}\n"
                    f"para mais detalhes entre em contato com o utilizador: {utilizador.nome} pelo telefone: {utilizador.telefone} ou pelo email: {utilizador.email}"
                   
                ),
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    settings.EMAIL_HOST_USER
                ),
                recipient_list=[utilizador.empresa.email],
                fail_silently=False,
            )
            """

        

        notificacoes_criadas = Notificacao.objects.bulk_create(notificacoes)
        for notificacao in notificacoes_criadas:
            enviar_notificacao_ws(notificacao)


@receiver(post_save, sender=ComentarioIntervencao)
def emitir_comentario_realtime(sender, instance, created, **kwargs):
    if created:
        enviar_comentario_ws(instance)


@receiver(post_save, sender=AnexoIntervencao)
def emitir_anexo_realtime(sender, instance, created, **kwargs):
    if created:
        enviar_anexo_ws(instance)
