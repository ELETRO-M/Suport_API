from django.db import models

from apps.usuarios.models import Usuario
from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel


class Notificacao(ModeloUUIDComTimestamps, SoftDeleteModel):
    utilizador = models.ForeignKey(Usuario, related_name="notificacoes", on_delete=models.CASCADE)
    tipo = models.CharField(max_length=100)
    titulo = models.CharField(max_length=255)
   
    mensagem = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    lida = models.BooleanField(default=False)
    
    # Envio de e-mail desativado temporariamente
    # enviar_email = models.BooleanField(default=False)
    # enviado_email = models.BooleanField(default=False)



class FCMToken(ModeloUUIDComTimestamps):
    utilizador = models.ForeignKey(Usuario, related_name="fcm_tokens", on_delete=models.CASCADE)
    token = models.CharField(max_length=500, unique=True)
    dispositivo_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Token FCM"
        verbose_name_plural = "Tokens FCM"

    def __str__(self):
        return f"{self.utilizador.email} - {self.token[:20]}..."

    

