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
    

