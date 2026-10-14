from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.configuracoes.firebase import publicar_notificacao, enviar_notificacao_push, remover_notificacao
from apps.notificacoes.models import Notificacao


@receiver(post_save, sender=Notificacao)
def publicar_notificacao_firebase(sender, instance, created, **kwargs):
    # Publicar ou atualizar no Firestore
    publicar_notificacao(instance)
    
    if created:
        # Enviar push notification via FCM apenas na criação
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


@receiver(post_delete, sender=Notificacao)
def remover_notificacao_firebase(sender, instance, **kwargs):
    remover_notificacao(instance)


