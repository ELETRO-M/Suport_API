from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.configuracoes.firebase import publicar_notificacao
from apps.notificacoes.models import Notificacao


@receiver(post_save, sender=Notificacao)
def publicar_notificacao_firebase(sender, instance, created, **kwargs):
    if created:
        publicar_notificacao(instance)
