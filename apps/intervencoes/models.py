from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.sistema.models import ConfiguracaoSistema
from rest_framework.exceptions import ValidationError as DRFValidationError
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario
from apps.configuracoes.models import ModeloUUIDComTimestamps,SoftDeleteModel
from apps.contratos.models import Contrato
from apps.sistema.models import ConfiguracaoSistema

class Intervencao(ModeloUUIDComTimestamps,SoftDeleteModel):
    class Estado(models.TextChoices):
        EXPIRADO="expirado", "Expirado",
        ACTIVO = "activo", "Activo",
        CANCELADO = "cancelado","Cancelado"
    class ActuacaoTipo(models.TextChoices):
        REMOTO = "remoto", "Remoto"
        PRESENCIAL = "presencial", "Presencial"
    class StatusChoices(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        RESOLVIDO = "resolvido", "Resolvido"
        FECHADO = "fechado", "Fechado"
        CONCLUIDO = "concluido", "Concluído"

    class PrioridadeChoices(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    numero = models.CharField(max_length=30, unique=True, blank=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    cliente = models.ForeignKey(
        Usuario,
        related_name="intervencoes",
        on_delete=models.CASCADE,
        limit_choices_to={"perfil__in": [Usuario.PerfilChoices.CLIENTE, Usuario.PerfilChoices.ADMIN]},
    )
    tecnico = models.ForeignKey(
        Usuario,
        related_name="intervencoes_atribuidas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"perfil": Usuario.PerfilChoices.TECNICO, "is_deleted": False},
    )
    contrato = models.ForeignKey(
        Contrato,
        related_name="intervencoes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    estado=models.CharField(choices=Estado.choices , default=Estado.ACTIVO)
    
    actuacao_tipo = models.CharField(max_length=20, choices=ActuacaoTipo.choices, default=ActuacaoTipo.REMOTO)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ABERTO)
    prioridade = models.CharField(max_length=20, choices=PrioridadeChoices.choices)
    data_abertura = models.DateTimeField(default=timezone.now)
    tipo_pagamento = models.CharField(choices=Contrato.TipoPagamento.choices)
    tipo_intervencao = models.CharField( choices=Contrato.Tipo_de_contratos.choices)
    data_inicio_intervencao = models.DateTimeField(null=True, blank=True)
    data_fim_intervencao = models.DateTimeField(null=True, blank=True)
    horas_trabalhadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ("-data_abertura",)
    @property
    def sla(self):

        config = ConfiguracaoSistema.load()

        prazo_final = self.data_abertura + timedelta(
            hours=config.prazo_padrao_intervencao
        )

        diferenca = prazo_final - timezone.now()

        horas_restantes = max(diferenca.total_seconds() / 3600, 0)
        

        return {
            "prazo_final": prazo_final,
            "horas_restantes": round(horas_restantes, 2),
            "expirado": timezone.now() > prazo_final
        }

    def __str__(self):
        return f"{self.numero} - {self  .titulo}"
    def clean(self):
        
        if self.status==self.StatusChoices.CONCLUIDO:
            if not self.data_fim_intervencao:
                raise ValidationError("Erro: Não é possuivel concluí sem data final de trabalho")
            if not self.data_inicio_intervencao:
                raise ValidationError("Erro: Não é possuivel concluí sem data inicio de trabalho")
            if not self.tecnico:
                raise ValidationError("Erro: Não é possuivel concluí sem o tecnico de trabalho")
            if not self.data_fim_intervencao:
                raise ValidationError("Erro: Não é possuivel concluí sem data final de trabalho")
        status_final = self.status in {self.StatusChoices.FECHADO, self.StatusChoices.CONCLUIDO}
        if status_final and not self.data_inicio_intervencao:
            raise ValidationError("Erro: Não foi fornecida a data de inicio da intervenção")
        if not self.cliente:
            raise ValidationError("Erro: não foi fornecido o cliente")
        if self.pk:

            antiga = Intervencao.objects.filter(pk=self.pk).first()

            if antiga and antiga.status in ["fechado", "concluido"]:

                utilizador = getattr(self, "_utilizador", None)

                if (
                    utilizador
                    and utilizador.perfil != Usuario.PerfilChoices.ADMIN
                ):
                    raise ValidationError(
                        "Esta intervenção está fechada e não pode ser editada."
                )
    def save(self, *args, **kwargs):
        if self.data_inicio_intervencao and self.data_fim_intervencao:

            diferenca = (
                self.data_fim_intervencao -
                self.data_inicio_intervencao
            )

            horas = diferenca.total_seconds() / 3600

            self.horas_trabalhadas = round(
                Decimal(str(horas)),
                2
            )
            if self.sla and self.sla.get("horas_restantes", 1) == 0 and self.estado != self.Estado.EXPIRADO:
                self.estado = self.Estado.EXPIRADO
                admins = Usuario.objects.filter(
                    perfil=Usuario.PerfilChoices.ADMIN,
                    is_deleted=False,
                    status=Usuario.StatusChoices.ACTIVO
                )
                notificacoes = []

                for admin in admins:
                    notificacoes.append(
                        Notificacao(
                            utilizador=admin,
                            titulo=f"Alerta: Intervenção expirada {self.numero}",
                            mensagem=f"A intervenção {self.numero} expirou.\n -Numero da Intervenção: {self.numero} \n-Titulo da Intervenção: {self.titulo} \n-Prioridade: {self.prioridade} \n-Tipo de actuação: {self.actuacao_tipo} \n-pelo cliente {self.cliente.nome} na empresa {self.cliente.empresa.nome}",
                            tipo="Alerta",
                            link=f"{settings.ALLOWED_HOSTS}/api/v1/intervencoes/{self.id}/",
                        )
                    )
                if notificacoes:
                    Notificacao.objects.bulk_create(notificacoes)
    
             

        if self.tecnico:
            Notificacao.objects.create(
                utilizador=self.tecnico,
                titulo=f"Nova intervenção na empresa {self.cliente.empresa.nome} ",
                mensagem=f"Foi lhe atribuida uma nova intervenção \n -Numeiro da Intervenção: {self.numero} \n-Titulo da Intervenção: {self.titulo} \n-Prioridade: {self.prioridade} \n-Tipo de actuação: {self.actuacao_tipo} \n-pelo cliente {self.cliente.nome} na empresa {self.cliente.empresa.nome}",
                tipo="imformação",
                link=f"{settings.ALLOWED_HOSTS}/api/v1/intervencoes/{self.id}/",
            )
        if not self.numero:
            date_part = timezone.now().year
            last_id = Intervencao.objects.filter(data_abertura__year=date_part).count() + 1
            self.numero = f"INT-{date_part}-{last_id:03d}"
        status_final = self.status in {self.StatusChoices.FECHADO, self.StatusChoices.CONCLUIDO}
        if status_final and not self.data_conclusao:
            if not self.data_fim_intervencao:
                self.data_fim_intervencao=timezone.now()
            self.data_conclusao = timezone.now()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"data_conclusao"}
        try:
            self.full_clean()
        except ValidationError as e:
            raise DRFValidationError(e.message_dict)
        super().save(*args, **kwargs)
        if status_final and not self.contrato_id:
            contrato = self.criar_contrato_automatico()
            type(self).objects.filter(pk=self.pk, contrato__isnull=True).update(contrato=contrato)
            self.contrato = contrato
    
    def criar_contrato_automatico(self):
        
        inicio = self.data_inicio_intervencao
        fim = self.data_fim_intervencao 
        if fim <= inicio:
            fim = inicio + timedelta(hours=1)
        horas = Decimal(str(round((fim - inicio).total_seconds() / 3600, 2)))
        if horas <= 0:
            horas = Decimal("1.00")
        valor_total = horas * ConfiguracaoSistema.load().taxa_hora
       

        return Contrato.objects.create(
            cliente=self.cliente,
            tipo_contrato=self.tipo_intervencao,
            tipo_de_pagamento=self.tipo_pagamento,
            horas_contratadas=horas,
            valor_total=valor_total,
            data_inicio=inicio.date(),
            data_fim=fim.date(),
            status=Contrato.StatusChoices.ACTIVO,
            observacoes=f"Criação de contrato a partir de intervenção número {self.numero} do cliente {self.cliente.nome} na empresa {self.cliente.empresa.nome}.",
        )


class HistoricoEstadoIntervencao(ModeloUUIDComTimestamps):
    intervencao = models.ForeignKey(Intervencao, related_name="historico_status", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Intervencao.StatusChoices.choices)
    alterado_por = models.ForeignKey(Usuario, related_name="status_alterados", on_delete=models.SET_NULL, null=True)
    nota = models.CharField(max_length=255, blank=True)


class ComentarioIntervencao(ModeloUUIDComTimestamps, SoftDeleteModel):
    intervencao = models.ForeignKey(Intervencao, related_name="comentarios", on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, related_name="comentarios_intervencao", on_delete=models.CASCADE)
    texto = models.TextField()
    visivel_cliente = models.BooleanField(default=True)


class AnexoIntervencao(ModeloUUIDComTimestamps, SoftDeleteModel):
    intervencao = models.ForeignKey(Intervencao, related_name="anexos", on_delete=models.CASCADE)
    utilizador = models.ForeignKey(Usuario, related_name="anexos_intervencao", on_delete=models.SET_NULL, null=True)
    arquivo = models.FileField(upload_to="intervencoes/anexos/")
    descricao = models.CharField(max_length=255, blank=True)
    tamanho = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.arquivo and hasattr(self.arquivo, "size"):
            self.tamanho = self.arquivo.size
        super().save(*args, **kwargs)


class HoraTrabalho(ModeloUUIDComTimestamps):
    class TipoChoices(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        REMOTO = "remoto", "Remoto"

    intervencao = models.ForeignKey(Intervencao, related_name="horas", on_delete=models.CASCADE)
    tecnico = models.ForeignKey(
        Usuario,
        related_name="horas_registadas",
        on_delete=models.CASCADE,
        limit_choices_to={"perfil": Usuario.PerfilChoices.TECNICO},
    )
    horas = models.DecimalField(max_digits=8, decimal_places=2)
    data_trabalho = models.DateField()
    descricao = models.TextField()
    tipo = models.CharField(max_length=20, choices=TipoChoices.choices)

    class Meta:
        ordering = ("-data_trabalho", "-data_criacao")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total = self.intervencao.horas.aggregate(total=models.Sum("horas"))["total"] or Decimal("0.00")
        self.intervencao.horas_trabalhadas = total
        self.intervencao.save(update_fields=["horas_trabalhadas"])
        if self.intervencao.contrato_id:
            contrato = self.intervencao.contrato
            contrato.horas_utilizadas = (
                contrato.intervencoes.aggregate(total=models.Sum("horas_trabalhadas"))["total"] or Decimal("0.00")
            )
            contrato.save(update_fields=["horas_utilizadas"])


TecnicoRelatorio = HoraTrabalho


