from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notificacoes.models import Notificacao
from apps.notificacoes.realtime import enviar_notificacao_ws


@receiver(post_save, sender=Notificacao)
def emitir_notificacao_realtime(sender, instance, created, **kwargs):
    if created:
        enviar_notificacao_ws(instance)
