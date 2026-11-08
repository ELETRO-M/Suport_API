from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel
from apps.usuarios.models import Usuario


class CategoriaObrigacao(ModeloUUIDComTimestamps, SoftDeleteModel):
    nome = models.CharField(max_length=150, unique=True)
    descricao = models.TextField(blank=True, default="")
    # Prazo padrão em dias (configurável, NÃO assume lei angolana — validar antes)
    dias_alerta = models.PositiveIntegerField(default=7)

    class Meta:
        ordering = ("nome",)


class ObrigacaoFiscal(ModeloUUIDComTimestamps, SoftDeleteModel):
    class Periodicidade(models.TextChoices):
        UNICA = "unica", "Única"
        MENSAL = "mensal", "Mensal"
        TRIMESTRAL = "trimestral", "Trimestral"
        SEMESTRAL = "semestral", "Semestral"
        ANUAL = "anual", "Anual"
        CUSTOM = "custom", "Personalizada"

    class EstadoExecucao(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PREPARACAO = "preparacao", "Preparação"
        VALIDACAO = "validacao", "Validação"
        ENTREGUE = "entregue", "Entregue"
        PAGA = "paga", "Paga"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey(
        Usuario, related_name="obrigacoes_fiscais", on_delete=models.CASCADE,
        limit_choices_to={"perfil": Usuario.PerfilChoices.CLIENTE},
    )
    categoria = models.ForeignKey(
        CategoriaObrigacao, related_name="obrigacoes", on_delete=models.PROTECT
    )
    periodicidade = models.CharField(
        max_length=15, choices=Periodicidade.choices, default=Periodicidade.UNICA
    )
    meses_custom = models.PositiveSmallIntegerField(
        default=1, help_text="Intervalo em meses quando periodicidade=custom"
    )
    periodo_inicio = models.DateField(null=True, blank=True)
    dia_vencimento = models.PositiveSmallIntegerField(default=15)
    data_vencimento = models.DateField()
    data_execucao = models.DateField(null=True, blank=True)
    responsavel = models.ForeignKey(
        Usuario, related_name="obrigacoes_como_responsavel", on_delete=models.SET_NULL,
        null=True, blank=True, limit_choices_to={"perfil": Usuario.PerfilChoices.TECNICO},
    )
    estado_execucao = models.CharField(
        max_length=20, choices=EstadoExecucao.choices, default=EstadoExecucao.PENDENTE
    )
    observacoes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("data_vencimento",)

    @property
    def vencida(self):
        return timezone.now().date() > self.data_vencimento and self.estado_execucao not in (
            self.EstadoExecucao.CONCLUIDA, self.EstadoExecucao.CANCELADA
        )

    @property
    def proxima(self):
        hoje = timezone.now().date()
        proximas = self.data_vencimento - hoje
        return 0 <= proximas.days <= (self.categoria.dias_alerta or 7)

    def gerar_proxima(self):
        delta = {
            self.Periodicidade.UNICA: None,
            self.Periodicidade.MENSAL: relativedelta(months=1),
            self.Periodicidade.TRIMESTRAL: relativedelta(months=3),
            self.Periodicidade.SEMESTRAL: relativedelta(months=6),
            self.Periodicidade.ANUAL: relativedelta(years=1),
            self.Periodicidade.CUSTOM: relativedelta(months=self.meses_custom or 1),
        }[self.periodicidade]
        if delta is None:
            return None
        próxima = self.data_vencimento + delta
        return ObrigacaoFiscal.objects.create(
            cliente=self.cliente, categoria=self.categoria, periodicidade=self.periodicidade,
            meses_custom=self.meses_custom, periodo_inicio=próxima,
            dia_vencimento=self.dia_vencimento, data_vencimento=próxima,
            data_execucao=self.data_execucao, responsavel=self.responsavel,
            observacoes=self.observacoes,
        )


class TarefaFiscal(ModeloUUIDComTimestamps, SoftDeleteModel):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"
        ATRASADA = "atrasada", "Atrasada"

    obrigacao = models.ForeignKey(ObrigacaoFiscal, related_name="tarefas", on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    responsavel = models.ForeignKey(
        Usuario, related_name="tarefas_fiscais", on_delete=models.SET_NULL, null=True, blank=True
    )
    prazo_execucao = models.DateField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDENTE)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("prazo_execucao",)


class HistoricoObrigacao(ModeloUUIDComTimestamps):
    obrigacao = models.ForeignKey(ObrigacaoFiscal, related_name="historicos", on_delete=models.CASCADE)
    alteracao = models.CharField(max_length=100)  # ex: reagendada, estado, responsavel
    detalhe = models.TextField(blank=True, default="")
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="historicos_obrigacoes")


class DocumentoObrigacao(ModeloUUIDComTimestamps):
    obrigacao = models.ForeignKey(ObrigacaoFiscal, related_name="documentos", on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    ficheiro = models.FileField(upload_to="obrigacoes/documentos/")
    descricao = models.CharField(max_length=255, blank=True, default="")
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
