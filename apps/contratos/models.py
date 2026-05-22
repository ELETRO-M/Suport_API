from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
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
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    valor_hora = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), blank=True, null=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)
    
    observacoes = models.TextField(blank=True)
    def clean(self):
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            raise ValidationError("A data de fim deve ser maior que a data de início.")

        if self.tipo_contrato == self.Tipo_de_contratos.SERVIÇO_AVULSO and self.data_fim is None:
            raise ValidationError("A data de fim é obrigatória para serviços avulsos.")
        if self.tipo_contrato == self.Tipo_de_contratos.SERVIÇO_AVULSO and self.data_inicio is None:
            raise ValidationError("A data de inicio é obrigatória para serviços avulsos.")
        if not self.cliente_id:
            raise ValidationError("O cliente é obrigatório.")
        try:
            if self.cliente.is_deleted:
                raise ValidationError("O cliente não pode estar inativo.")
        except Usuario.DoesNotExist:
            raise ValidationError("O cliente não foi encontrado.")
        if self.status == self.StatusChoices.EXPIRADO and self.data_fim and self.data_fim > timezone.now():
            raise ValidationError("O contrato não pode estar marcado como expirado se a data de fim é futura.")
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

       

        if self.data_fim and self.data_inicio:

            diferenca = self.data_fim - self.data_inicio

            horas = Decimal(str(diferenca.total_seconds()/3600))

            self.horas_contratadas =round(horas,2)

            self.horas_utilizadas = round(horas,2)

            config = ConfiguracaoSistema.load()

            if self.tipo_de_pagamento == self.TipoPagamento.HORAS:
                if self.valor_total is None:
                    self.valor_total= self.horas_contratadas* config.taxa_hora
                if self.horas_contratadas > 0:
                    self.valor_hora = self.valor_total / self.horas_contratadas

            elif self.tipo_de_pagamento == self.TipoPagamento.MENSAL:
                if self.valor_total is None:
                    self.valor_total= self.horas_contratadas* config.taxa_mensal
                meses = diferenca.days // 30

                
            elif self.tipo_de_pagamento == self.TipoPagamento.ANUAL:
                if self.valor_total is None:
                    self.valor_total= self.horas_contratadas* config.taxa_anual
                anos = diferenca.days // 365
            if self.horas_contratadas:
              self.valor_hora= self.valor_total/ self.horas_contratadas
            if self.data_fim:
                if timezone.now() > self.data_fim:
                    
                    dias = (timezone.now()- self.data_fim).days
                else:
                    dias = (self.data_fim - timezone.now()).days   
            
            if dias >=15:
                self.status = self.StatusChoices.EXPIRADO
            else:
                self.status = self.StatusChoices.ACTIVO
             

           
            
    class Meta:
        ordering = ("-data_criacao",)

    all_objects = SoftDeleteQuerySet.as_manager()

    def __str__(self):
        return f"{self.cliente.nome} - {self.tipo_contrato}"

    @property
    def horas_disponiveis(self):
        return max(self.horas_contratadas - self.horas_utilizadas, Decimal("0.00"))
   
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
    
        if self.valor_hora is not None:
            self.valor_hora = round(Decimal(str(self.valor_hora)), 2)
        if self.valor_total is not None:
            self.valor_total = round(Decimal(str(self.valor_total)), 2)

        try:
            self.full_clean()
        except ValidationError as e:
            raise DRFValidationError(e.message_dict)
        super().save(*args, **kwargs)
