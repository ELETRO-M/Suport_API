from decimal import Decimal

from django.db import models

from apps.usuarios.models import Usuario
from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel



class Contrato(ModeloUUIDComTimestamps, SoftDeleteModel):
    class TipoChoices(models.TextChoices):
        HORAS = "horas", "Horas"
        MENSAL = "mensal", "Mensal"
        ANUAL = "anual", "Anual"

    class StatusChoices(models.TextChoices):
        ACTIVO = "activo", "Activo"
        EXPIRADO = "expirado", "Expirado"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(
        Usuario,
        related_name="contratos",
        on_delete=models.CASCADE,
        limit_choices_to={"perfil": Usuario.PerfilChoices.CLIENTE},
    )
    
    tipo = models.CharField(max_length=20, choices=TipoChoices.choices)
    horas_contratadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    horas_utilizadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)
    valor_hora = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    data_inicio = models.DateField()
    delete=models.BooleanField(default=False)
    data_fim = models.DateField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ("-data_criacao",)

    def __str__(self):
        return f"{self.cliente.nome} - {self.tipo}"

    @property
    def horas_disponiveis(self):
        return max(self.horas_contratadas - self.horas_utilizadas, Decimal("0.00"))

    def save(self, *args, **kwargs):
        if self.tipo == self.TipoChoices.HORAS and self.horas_contratadas:
            self.valor_hora = self.valor_total / self.horas_contratadas
        super().save(*args, **kwargs)
