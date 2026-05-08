from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.usuarios.models import Usuario
from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel, SoftDeleteQuerySet



class Contrato(ModeloUUIDComTimestamps, SoftDeleteModel):
    class Tipo_de_contratos(models.TextChoices):
        ASSISTENCIA_TECNICA = "assistencia tecnica", "Assistência Técnica"
        SUPORTE = "suporte", "Suporte",
        INSTALAÇÃO = "instalação", "Instalação"
        MANUTENÇÃO_PREVENTIVA = "manutencao preventiva", "Manutenção Preventiva"
        MANUTENÇÃO_CORRETIVA = "manutencao corretiva", "Manutenção Corretiva"
        SERVIÇO_AVULSO = "servico avulso", "Serviço Avulso"
        OUTROS = "outros", "Outros"
        ANUAL = "anual", "Anual"

    class TipoPagamento(models.TextChoices):
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
    
    tipo_de_pagamento= models.CharField(max_length=20, choices=TipoPagamento.choices)
    tipo_contrato= models.CharField(max_length=40, choices=Tipo_de_contratos.choices)
    descricao_contrato = models.TextField(blank=True)
    horas_contratadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    horas_utilizadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)
    valor_hora = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    data_inicio = models.DateField()
    data_fim = models.DateField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)
    observacoes = models.TextField(blank=True)
    def clean(self):
        if self.data_fim < self.data_inicio:
            raise ValidationError({
                "ERRO": "A data de fim deve ser maior que a data de início.",
                })
        if self.tipo_de_pagamento == self.TipoPagamento.HORAS and self.horas_contratadas <= 0:
            raise ValidationError({
                "ERRO": "O número de horas deve ser maior que 0.",
                })
        if self.tipo_de_pagamento == self.TipoPagamento.HORAS and self.horas_utilizadas < 0:
            raise ValidationError({
                "ERRO": "O número de horas deve ser maior que 0.",
                })
        if self.tipo_de_pagamento == self.TipoPagamento.HORAS and self.valor_total <= 0:
            raise ValidationError({
                "ERRO": "O valor total deve ser maior que 0.",
                })
        if self.tipo_contrato == self.Tipo_de_contratos.SERVIÇO_AVULSO and self.data_fim == None:
            raise ValidationError({
                "ERRO": "A data de fim é obrigatória para serviços avulsos.",
                })
        if self.tipo_contrato == self.Tipo_de_contratos.SERVIÇO_AVULSO and self.data_inicio == None:
            raise ValidationError({
                "ERRO": "A data de inicio é obrigatória para serviços avulsos.",
                })
        if self.cliente.is_deleted == True:
            raise ValidationError({
                "ERRO": "O cliente não pode estar inativo.",
                })
        if self.status == self.StatusChoices.EXPIRADO and self.data_fim > timezone.now().date():
            raise ValidationError({
                "ERRO": "O contrato não pode estar expirado.",
                })
        if self.tipo_contrato == self.Tipo_de_contratos.OUTROS:
            if not self.descricao_contrato:
                raise ValidationError({
                    "ERRO": "A descrição do contrato é obrigatória.",
                    })
            if not self.observacoes:
                raise ValidationError({
                    "ERRO": "A descrição do contrato é obrigatória.",
                    })
            if not self.valor_total:
                raise ValidationError({
                    "ERRO": "O valor total é obrigatório para contrato tipo outros.",
                    })
            if not self.data_inicio:
                raise ValidationError({
                    "ERRO": "A data de inicio é obrigatória para contrato tipo outros.",
                    })
            if not self.data_fim:
                raise ValidationError({
                    "ERRO": "A data de fim é obrigatória para contrato tipo outros.",
                    })
            if not self.status:
                raise ValidationError({
                    "ERRO": "O status é obrigatório para contrato tipo outros.",
                    })
            if not self.tipo_de_pagamento:
                raise ValidationError({
                    "ERRO": "O tipo de pagamento é obrigatório para contrato tipo outros.",
                    })
            if self.tipo_de_pagamento == self.TipoPagamento.HORAS and not self.horas_contratadas:
                raise ValidationError({
                    "ERRO": "O número de horas é obrigatório para contrato tipo outros.",
                    })
    class Meta:
        ordering = ("-data_criacao",)

    all_objects = SoftDeleteQuerySet.as_manager()

    def __str__(self):
        return f"{self.cliente.nome} - {self.tipo_contrato}"

    @property
    def horas_disponiveis(self):
        return max(self.horas_contratadas - self.horas_utilizadas, Decimal("0.00"))

    def save(self, *args, **kwargs):
        if self.tipo_de_pagamento == self.TipoPagamento.HORAS and self.horas_contratadas:
            self.valor_hora = self.valor_total / self.horas_contratadas
        self.full_clean()
        super().save(*args, **kwargs)
