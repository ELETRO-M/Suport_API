from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.intervencoes.models import Intervencao
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

        notificacoes = []

        for admin in admins:

            notificacoes.append(
                Notificacao(
                    utilizador=admin,
                    tipo="sistema",
                    titulo="Nova intervenção",
                    mensagem=f"A intervenção {instance.titulo} na empresa {instance.cliente.empresa.nome}  pelo cliente {instance.cliente.nome}.",
                )
            )

        Notificacao.objects.bulk_create(notificacoes)