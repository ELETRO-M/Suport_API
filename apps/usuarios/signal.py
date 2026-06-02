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

        Notificacao.objects.create(
            utilizador=instance,
            tipo="sistema",
            titulo="Seja bem-vindo(a) ao nosso sistema!",
            mensagem="Seja bem-vindo(a) ao nosso sistema!",
        )
        #EmailService.send_welcome_email(instance)

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo="Novo cliente cadastrado",
                mensagem=f"O cliente {instance.nome} na empresa {instance.empresa.nome} foi cadastrado.",
            )

    if created and instance.perfil == Usuario.PerfilChoices.TECNICO:

        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )

        Notificacao.objects.create(
            utilizador=instance,
            tipo="sistema",
            titulo="Seja bem-vindo(a) ao nosso sistema!",
            mensagem="Seja bem-vindo(a) ao nosso sistema!",
        )
        #EmailService.send_welcome_email(instance)

        especialidades_list = instance.especialidades if isinstance(instance.especialidades, list) else []
        especialidades_str = ", ".join(str(e) for e in especialidades_list)

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo="Novo técnico cadastrado",
                mensagem=f"O técnico {instance.nome} com a(s) especialidade(s) ({especialidades_str}) foi cadastrado.",
            )