from decimal import Decimal
from django.conf import settings
from django.db import models

from apps.configuracoes.models import ModeloUUIDComTimestamps



class ConfiguracaoSistema(models.Model):
    moeda = models.CharField(max_length=10, default="Kz")
    fuso_horario = models.CharField(max_length=100, default="Africa/Luanda")
    email_notificacoes = models.BooleanField(default=True)
    prazo_padrao_intervencao = models.PositiveIntegerField(default=48)
    taxa_hora= models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("5000.00"))
    taxa_mensal= models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("5000.00"))
    taxa_anual = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("5000.00"))
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj




class Conversa(ModeloUUIDComTimestamps):
    numero = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=255, blank=True)
    ultima_mensagem = models.TextField(blank=True)
    ultima_mensagem_em = models.DateTimeField(null=True, blank=True)
    nao_lidas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-ultima_mensagem_em"]


class Mensagem(ModeloUUIDComTimestamps):
    class Direcao(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    conversa = models.ForeignKey(Conversa, related_name="mensagens", on_delete=models.CASCADE)
    wa_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    direcao = models.CharField(max_length=10, choices=Direcao.choices)
    texto = models.TextField()
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["data_criacao"]