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
        send_mail(
                subject="Criação de Nova Intervenção",
                message=(
                    f"Olá, caro admin da empresa{utilizador.empresa.nome}\n\n"
                    "Foi criada uma nova intervenção na empresa.\n\n"
                    f"Intervenção: {instance.titulo}\n"
                    f"Cliente: {instance.cliente.nome}\n"
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

        

        Notificacao.objects.bulk_create(notificacoes)