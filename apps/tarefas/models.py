from django.db import models, transaction
from django.utils import timezone

from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel
from apps.intervencoes.models import Intervencao
from apps.usuarios.models import Usuario


class Tarefa(ModeloUUIDComTimestamps, SoftDeleteModel):
    class EstadoChoices(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_PROGRESSO = "em_progresso", "Em progresso"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"
        EXPIRADO = "expirado", "Expirado"

    class PrioridadeChoices(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    numero = models.CharField(max_length=30, unique=True, blank=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    estado = models.CharField(
        max_length=20, choices=EstadoChoices.choices, default=EstadoChoices.PENDENTE
    )
    prioridade = models.CharField(
        max_length=20, choices=PrioridadeChoices.choices, default=PrioridadeChoices.MEDIA
    )
    atribuido_a = models.ForeignKey(
        Usuario,
        related_name="tarefas_atribuidas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={
            "perfil__in": [Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.TECNICO],
            "is_deleted": False,
            "status": Usuario.StatusChoices.ACTIVO,
        },
    )
    intervencao = models.ForeignKey(
        Intervencao,
        related_name="tarefas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_deleted": False},
    )
    data_inicio = models.DateTimeField(null=True, blank=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data_criacao",)

    def __str__(self):
        return f"{self.numero} - {self.titulo}"

    @property
    def prazo(self):
        if not self.data_fim:
            return None
        agora = timezone.now()
        total = self.data_fim - self.data_inicio if self.data_inicio else None
        restante = self.data_fim - agora
        return {
            "total_horas": round(total.total_seconds() / 3600, 2) if total else None,
            "restantes_horas": round(max(restante.total_seconds(), 0) / 3600, 2),
            "expirado": restante.total_seconds() <= 0,
        }

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                date_part = timezone.now().year
                ultimo = (
                    Tarefa.all_objects.select_for_update()
                    .filter(data_criacao__year=date_part, numero__startswith=f"TAR-{date_part}-")
                    .order_by("-numero")
                    .values_list("numero", flat=True)
                    .first()
                )
                if ultimo:
                    try:
                        last_id = int(ultimo.split("-")[-1]) + 1
                    except (ValueError, IndexError):
                        last_id = 1
                else:
                    last_id = 1
                self.numero = f"TAR-{date_part}-{last_id:03d}"
        if self.data_fim and self.estado not in {
            self.EstadoChoices.CONCLUIDA,
            self.EstadoChoices.CANCELADA,
        } and timezone.now() >= self.data_fim:
            self.estado = self.EstadoChoices.EXPIRADO
        super().save(*args, **kwargs)


class ComentarioTarefa(ModeloUUIDComTimestamps):
    tarefa = models.ForeignKey(Tarefa, related_name="comentarios", on_delete=models.CASCADE)
    utilizador = models.ForeignKey(
        Usuario, related_name="comentarios_tarefas", on_delete=models.SET_NULL, null=True
    )
    texto = models.TextField()

    class Meta:
        ordering = ("data_criacao",)

    def __str__(self):
        return f"Comentário em {self.tarefa.numero}"


class AnexoTarefa(ModeloUUIDComTimestamps, SoftDeleteModel):
    tarefa = models.ForeignKey(Tarefa, related_name="anexos", on_delete=models.CASCADE)
    utilizador = models.ForeignKey(
        Usuario, related_name="anexos_tarefas", on_delete=models.SET_NULL, null=True
    )
    arquivo = models.FileField(upload_to="tarefas/anexos/")
    descricao = models.CharField(max_length=255, blank=True)
    tamanho = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.arquivo and hasattr(self.arquivo, "size"):
            self.tamanho = self.arquivo.size
        super().save(*args, **kwargs)