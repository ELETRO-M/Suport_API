from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from apps.intervencoes.models import AnexoIntervencao, ComentarioIntervencao, Intervencao
from apps.configuracoes.firebase import (
    enviar_push_notificacao,
    publicar_anexo,
    publicar_comentario,
    publicar_notificacao,
)
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario


@receiver(post_save, sender=Intervencao)
def criar_notificacao_admins(sender, instance, created, **kwargs):

    if created:

        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo=f"Nova intervenção na empresa {instance.cliente.empresa.nome}",
                mensagem=f"A intervenção {instance.titulo} na empresa {instance.cliente.empresa.nome} pelo cliente {instance.cliente.nome}.",
                link=f"{settings.SITE_URL}/api/v1/intervencoes/{instance.id}/",
            )
            enviar_push_notificacao(
                admin,
                f"Nova intervenção - {instance.cliente.empresa.nome}",
                f"{instance.titulo} - {instance.cliente.nome}",
                dados={"link": f"/intervencoes/{instance.id}", "tipo": "nova_intervencao"},
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

        


@receiver(post_save, sender=ComentarioIntervencao)
def publicar_comentario_firebase(sender, instance, created, **kwargs):
    if created:
        publicar_comentario(instance)
        intervencao = instance.intervencao
        if intervencao.tecnico and intervencao.tecnico.fcm_token:
            enviar_push_notificacao(
                intervencao.tecnico,
                "Novo comentário",
                f"{instance.usuario.nome}: {instance.texto[:80]}",
                dados={"link": f"/intervencoes/{intervencao.id}", "tipo": "comentario"},
            )


@receiver(post_save, sender=AnexoIntervencao)
def publicar_anexo_firebase(sender, instance, created, **kwargs):
    if created:
        publicar_anexo(instance)
        intervencao = instance.intervencao
        if intervencao.tecnico and intervencao.tecnico.fcm_token:
            enviar_push_notificacao(
                intervencao.tecnico,
                "Novo anexo",
                f"{instance.utilizador.nome} anexou {instance.nome_arquivo or 'um ficheiro'}",
                dados={"link": f"/intervencoes/{intervencao.id}", "tipo": "anexo"},
            )
