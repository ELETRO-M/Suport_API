from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError
from datetime import datetime
from zoneinfo import ZoneInfo
from apps.usuarios.models import Usuario,empresa
from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel, SoftDeleteQuerySet
from apps.sistema.models import ConfiguracaoSistema


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
        CONCLUIDO = "concluído", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    Empresa= models.ForeignKey(
        empresa,
        related_name="contratos",
        on_delete=models.CASCADE,
    )

    tipo_de_pagamento= models.CharField(max_length=20, choices=TipoPagamento.choices)
    tipo_contrato= models.CharField(max_length=40, choices=Tipo_de_contratos.choices)
    descricao_contrato = models.TextField( blank=True, null=True)
    horas_contratadas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    horas_utilizadas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, blank=True)
    valor_hora = models.DecimalField(max_digits=25, decimal_places=2, blank=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)
    
    observacoes = models.TextField(blank=True)
    def delete(self):
        for i in self.intervencoes.all():
            i.delete()
        self.status = self.StatusChoices.CANCELADO
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "status"])
    def clean(self):
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise ValidationError("A data de fim deve ser maior que a data de inicio.")
        if self.data_fim and self.data_inicio:
            if self.tipo_de_pagamento == self.TipoPagamento.HORAS and self.data_fim == self.data_inicio:
                raise ValidationError({"data_fim": "A data de fim deve gerar pelo menos uma hora contratada."})
            if self.tipo_de_pagamento == self.TipoPagamento.MENSAL:
                meses = (
                    (self.data_fim.year - self.data_inicio.year) * 12
                    + (self.data_fim.month - self.data_inicio.month)
                )
                if meses <= 0:
                    raise ValidationError({"data_fim": "Contrato mensal deve ter pelo menos um mes de duracao."})
            if self.tipo_de_pagamento == self.TipoPagamento.ANUAL:
                anos = self.data_fim.year - self.data_inicio.year
                if anos <= 0:
                    raise ValidationError({"data_fim": "Contrato anual deve ter pelo menos um ano de duracao."})
        if self.horas_contratadas is not None and self.horas_contratadas <= Decimal("0.00"):
            raise ValidationError({"horas_contratadas": "As horas contratadas devem ser maiores que zero."})

        if self.tipo_contrato == self.Tipo_de_contratos.SERVIÇO_AVULSO and self.data_fim is None:
            raise ValidationError("A data de fim é obrigatória para serviços avulsos.")
        if self.tipo_contrato == self.Tipo_de_contratos.SERVIÇO_AVULSO and self.data_inicio is None:
            raise ValidationError("A data de inicio é obrigatória para serviços avulsos.")
        if not self.Empresa_id:
            raise ValidationError("A empresa é obrigatório.")
        try:
            if self.Empresa.is_deleted:
                raise ValidationError("O cliente não pode estar inativo.")
        except Usuario.DoesNotExist:
            raise ValidationError("O cliente não foi encontrado.")
        
        if self.tipo_contrato == self.Tipo_de_contratos.OUTROS:
            if not self.descricao_contrato:
                raise ValidationError("A descrição do contrato é obrigatória.")
            if not self.observacoes:
                raise ValidationError("As observações do contrato são obrigatórias.")
            if not self.valor_total:
                raise ValidationError("O valor total é obrigatório para contrato tipo outros.")
            if not self.data_inicio:
                raise ValidationError("A data de inicio é obrigatória para contrato tipo outros.")
            if not self.data_fim:
                raise ValidationError("A data de fim é obrigatória para contrato tipo outros.")
            if not self.tipo_de_pagamento:
                raise ValidationError("O tipo de pagamento é obrigatório para contrato tipo outros.")
            
    def calcular_contrato(self):
        config = ConfiguracaoSistema.load()

        if self.data_fim and self.data_inicio:
            diferenca = self.data_fim - self.data_inicio
            if self.tipo_de_pagamento == self.TipoPagamento.HORAS:
                horas = Decimal(
                    str(round(diferenca.total_seconds() / 3600,2))
                )
                if not self.valor_total:
                    self.valor_total=config.taxa_hora*horas
                if self.valor_total and not self.valor_hora:
                    self.valor_hora = round(self.valor_total / horas, 2)

            elif self.tipo_de_pagamento == self.TipoPagamento.MENSAL:
                meses = (
                    (self.data_fim.year - self.data_inicio.year) * 12
                    + (self.data_fim.month - self.data_inicio.month)
                )
                horas = Decimal(str(round(meses,2)))
                if not self.valor_total:
                    self.valor_total=config.taxa_mensal*horas
                if self.valor_total and not self.valor_hora:
                    self.valor_hora = round(self.valor_total / horas, 2)

            elif self.tipo_de_pagamento == self.TipoPagamento.ANUAL:
                anos = self.data_fim.year - self.data_inicio.year
                horas = Decimal(str(round(anos,2)))
                if not self.valor_total:
                    self.valor_total=config.taxa_anual*horas
                if self.valor_total and not self.valor_hora:
                    self.valor_hora = round(self.valor_total / horas, 2)
            else:
                horas = Decimal("0.00")

            if horas <= Decimal("0.00"):
                raise ValidationError({"data_fim": "O contrato deve gerar horas contratadas maior que zero."})
            if not self.horas_contratadas:
                self.horas_contratadas =round(horas,2)

            if self.horas_contratadas <= Decimal("0.00"):
                raise ValidationError({"horas_contratadas": "As horas contratadas devem ser maiores que zero."})

            if self.valor_total and not self.valor_hora:
                self.valor_hora = round(self.valor_total / self.horas_contratadas, 2)
            if timezone.now() > self.data_fim:
                self.status = self.StatusChoices.EXPIRADO
            else:
                self.status = self.StatusChoices.ACTIVO
            horas_utilizadas = self.horas_utilizadas or Decimal("0.00")
            if self.horas_contratadas <=horas_utilizadas:
                self.status= self.StatusChoices.CONCLUIDO

            
    class Meta:
        ordering = ("-data_criacao",)

    all_objects = SoftDeleteQuerySet.as_manager()

    def __str__(self):
        return f"{self.Empresa.nome} - {self.tipo_contrato}"

    @property
    def horas_disponiveis(self):
        horas_contratadas = self.horas_contratadas or Decimal("0.00")
        horas_utilizadas = self.horas_utilizadas or Decimal("0.00")
        return max(horas_contratadas - horas_utilizadas, Decimal("0.00"))

    @classmethod
    def atualizar_horas_utilizadas(cls, contrato_id):
        if not contrato_id:
            return

        total = (
            cls.objects.filter(pk=contrato_id)
            .aggregate(total=Sum("intervencoes__horas_trabalhadas"))["total"]
            or Decimal("0.00")
        )
        cls.objects.filter(pk=contrato_id).update(horas_utilizadas=round(total, 2))
   
    @property
    def expiracao(self):
        if self.data_fim:
            if timezone.now() > self.data_fim:
                
               dias = (timezone.now()- self.data_fim).days
            else:
                dias = (self.data_fim - timezone.now()).days   
            return dias
        return 0

    def save(self, *args, **kwargs):
        
        self.calcular_contrato()
        
    
        if self.valor_hora not in (None,0.00):
            self.valor_hora = round(Decimal(str(self.valor_hora)), 2)
        if self.valor_total not in (None,0.00):
            self.valor_total = round(Decimal(str(self.valor_total)), 2)

        update_fields = kwargs.get("update_fields")
        if update_fields is None or "is_deleted" not in update_fields:
            try:
                self.full_clean()
            except ValidationError as e:
                raise DRFValidationError(e.message_dict)
        super().save(*args, **kwargs)
