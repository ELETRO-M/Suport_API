from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.configuracoes.firebase import publicar_notificacao, enviar_notificacao_push
from apps.notificacoes.models import Notificacao


@receiver(post_save, sender=Notificacao)
def publicar_notificacao_firebase(sender, instance, created, **kwargs):
    if created:
        publicar_notificacao(instance)
        # Enviar push notification via FCM
        data = {
            "id": str(instance.id),
            "tipo": instance.tipo,
            "link": instance.link or "",
        }
        enviar_notificacao_push(
            utilizador=instance.utilizador,
            titulo=instance.titulo,
            mensagem=instance.mensagem,
            data=data
        )

