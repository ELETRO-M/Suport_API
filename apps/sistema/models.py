from decimal import Decimal

from django.db import models



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
