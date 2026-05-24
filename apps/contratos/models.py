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
        CANCELADO = "cancelado", "Cancelado"

    Empresa= models.ForeignKey(
        empresa,
        related_name="contratos",
        on_delete=models.CASCADE,
    )

    tipo_de_pagamento= models.CharField(max_length=20, choices=TipoPagamento.choices)
    tipo_contrato= models.CharField(max_length=40, choices=Tipo_de_contratos.choices)
    descricao_contrato = models.TextField()
    horas_contratadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    horas_utilizadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), null=True, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)
    valor_hora = models.DecimalField(max_digits=25, decimal_places=2, default=Decimal("0.00"), blank=True)
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

       

        if self.data_fim and self.data_inicio:
            agora = timezone.now()

            diferenca = self.data_fim - self.data_inicio
            if self.tipo_de_pagamento == self.TipoPagamento.HORAS:

                horas = Decimal(
                    str(diferenca.total_seconds() / 3600)
                )


            elif self.tipo_de_pagamento == self.TipoPagamento.MENSAL:

                meses = (
                    (agora.year - self.data_inicio.year) * 12
                    + (agora.month - self.data_inicio.month)
                )
                horas = Decimal(str(meses))


            elif self.tipo_de_pagamento == self.TipoPagamento.ANUAL:

                anos = self.data_inicio.year - agora.year

                horas = Decimal(str(anos))
                
            self.horas_contratadas =round(horas,2)

            config = ConfiguracaoSistema.load()

            if self.horas_contratadas:
              self.valor_hora= self.valor_total/ self.horas_contratadas
            
            dias = (self.data_fim - timezone.now()).days   
            
            if dias <=0:
                self.status = self.StatusChoices.EXPIRADO
            else:
                print(dias)
                self.status = self.StatusChoices.ACTIVO
             

           
            
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
    
        if self.valor_hora is not None:
            self.valor_hora = round(Decimal(str(self.valor_hora)), 2)
        if self.valor_total is not None:
            self.valor_total = round(Decimal(str(self.valor_total)), 2)

        try:
            self.full_clean()
        except ValidationError as e:
            raise DRFValidationError(e.message_dict)
        super().save(*args, **kwargs)
