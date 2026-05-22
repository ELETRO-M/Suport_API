from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario
from apps.configuracoes.email import EmailService


@receiver(post_save, sender=Usuario)
def criar_notificacao_admins(sender, instance, created, **kwargs):

    if created and instance.perfil == Usuario.PerfilChoices.CLIENTE:

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
                    titulo="Nova cliente cadastrado",
                    mensagem=f"O cliente {instance.nome} no servidor {instance.ip_servidor} na empresa {instance.empresa.nome} foi cadastrado.",
                )
            )
        Notificacao.objects.create(
            utilizador=instance,
            tipo="sistema",
            titulo="Seja bem-vindo(a) ao nosso sistema!",
            mensagem=f"Seja bem-vindo(a) ao nosso sistema!",
        )
        #EmailService.send_welcome_email(instance)

        Notificacao.objects.bulk_create(notificacoes)