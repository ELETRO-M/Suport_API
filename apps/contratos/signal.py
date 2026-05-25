from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.contratos.models import Contrato
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario


@receiver(post_save, sender=Contrato)
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
                    titulo="Novo contrato",
                    mensagem=f"Novo contrato {instance.tipo_contrato} criado para a empresa {instance.Empresa.nome}.",
                    link=f"{settings.SITE_URL}/api/v1/contratos/{instance.id}/",
                )
            )

        Notificacao.objects.bulk_create(notificacoes)
