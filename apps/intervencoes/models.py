from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.usuarios.models import Usuario
from apps.configuracoes.models import ModeloUUIDComTimestamps
from apps.contratos.models import Contrato


class Intervencao(ModeloUUIDComTimestamps):
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
        limit_choices_to={"perfil": Usuario.PerfilChoices.CLIENTE},
    )
    tecnico = models.ForeignKey(
        Usuario,
        related_name="intervencoes_atribuidas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"perfil": Usuario.PerfilChoices.TECNICO},
    )
    contrato = models.ForeignKey(
        Contrato,
        related_name="intervencoes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ABERTO)
    prioridade = models.CharField(max_length=20, choices=PrioridadeChoices.choices)
    horas_trabalhadas = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    data_abertura = models.DateTimeField(default=timezone.now)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data_abertura",)

    def __str__(self):
        return f"{self.numero} - {self.titulo}"

    def save(self, *args, **kwargs):
        if not self.numero:
            date_part = timezone.now().year
            last_id = Intervencao.objects.filter(data_abertura__year=date_part).count() + 1
            self.numero = f"INT-{date_part}-{last_id:03d}"
        if self.status in {self.StatusChoices.FECHADO, self.StatusChoices.CONCLUIDO} and not self.data_conclusao:
            self.data_conclusao = timezone.now()
        super().save(*args, **kwargs)


class HistoricoEstadoIntervencao(ModeloUUIDComTimestamps):
    intervencao = models.ForeignKey(Intervencao, related_name="historico_status", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Intervencao.StatusChoices.choices)
    alterado_por = models.ForeignKey(Usuario, related_name="status_alterados", on_delete=models.SET_NULL, null=True)
    nota = models.CharField(max_length=255, blank=True)


class ComentarioIntervencao(ModeloUUIDComTimestamps):
    intervencao = models.ForeignKey(Intervencao, related_name="comentarios", on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, related_name="comentarios_intervencao", on_delete=models.CASCADE)
    texto = models.TextField()
    visivel_cliente = models.BooleanField(default=True)


class AnexoIntervencao(ModeloUUIDComTimestamps):
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

    def delete(self, *args, **kwargs):
        intervencao = self.intervencao
        contrato = intervencao.contrato if intervencao.contrato_id else None
        super().delete(*args, **kwargs)
        total = intervencao.horas.aggregate(total=models.Sum("horas"))["total"] or Decimal("0.00")
        intervencao.horas_trabalhadas = total
        intervencao.save(update_fields=["horas_trabalhadas"])
        if contrato:
            contrato.horas_utilizadas = (
                contrato.intervencoes.aggregate(total=models.Sum("horas_trabalhadas"))["total"] or Decimal("0.00")
            )
            contrato.save(update_fields=["horas_utilizadas"])
