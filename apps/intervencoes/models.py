from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
import re

from apps.sistema.models import ConfiguracaoSistema
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario
from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel
from apps.contratos.models import Contrato


class Intervencao(ModeloUUIDComTimestamps, SoftDeleteModel):
    class Estado(models.TextChoices):
        EXPIRADO = "expirado", "Expirado"
        ACTIVO = "activo", "Activo"
        CANCELADO = "cancelado", "Cancelado"

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
        limit_choices_to={
            "perfil__in": [Usuario.PerfilChoices.CLIENTE, Usuario.PerfilChoices.ADMIN],
            "is_deleted": False,
            "status": Usuario.StatusChoices.ACTIVO,
        },
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
        limit_choices_to={"is_deleted": False, "status": Contrato.StatusChoices.ACTIVO},
    )
    estado = models.CharField(choices=Estado.choices, default=Estado.ACTIVO)
    actuacao_tipo = models.CharField(
        max_length=20, choices=ActuacaoTipo.choices, default=ActuacaoTipo.REMOTO
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.ABERTO
    )
    prioridade = models.CharField(max_length=20, choices=PrioridadeChoices.choices)
    data_abertura = models.DateTimeField(default=timezone.now)
    data_inicio_intervencao = models.DateTimeField(null=True, blank=True)
    data_fim_intervencao = models.DateTimeField(null=True, blank=True)
    horas_trabalhadas = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), null=True, blank=True
    )
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data_abertura",)

    def __str__(self):
        return f"{self.numero} - {self.titulo}"

    @property
    def sla(self):
        config = ConfiguracaoSistema.load()
        prazo_final = self.data_abertura + timedelta(hours=config.prazo_padrao_intervencao)
        diferenca = prazo_final - timezone.now()
        horas_restantes = max(diferenca.total_seconds() / 3600, 0)
        return {
            "prazo_final": prazo_final,
            "horas_restantes": round(horas_restantes, 2),
            "expirado": timezone.now() > prazo_final,
        }

    def clean(self):
        # ── Cliente obrigatório ──────────────────────────────────────────────
        if not self.cliente_id:
            raise ValidationError("Erro: não foi fornecido o cliente.")

        # ── Validações do contrato ───────────────────────────────────────────
        if self.contrato_id:
            if self.cliente.empresa_id != self.contrato.Empresa_id:
                raise ValidationError(
                    "Erro: o contrato não pertence à empresa do cliente."
                )
            if self.contrato.status != Contrato.StatusChoices.ACTIVO:
                raise ValidationError("Erro: o contrato associado não está activo.")

            if self.horas_trabalhadas:
                # Ao editar, devolver as horas desta intervenção ao disponível
                # para não comparar contra um valor já descontado.
                horas_disponiveis_reais = self.contrato.horas_disponiveis
                if self.pk:
                    horas_proprias = (
                        Intervencao.objects.filter(pk=self.pk)
                        .values_list("horas_trabalhadas", flat=True)
                        .first()
                    ) or Decimal("0.00")
                    horas_disponiveis_reais += horas_proprias

                

        # ── Validações de status final ───────────────────────────────────────
        if self.status == self.StatusChoices.CONCLUIDO:
            if not self.data_inicio_intervencao:
                raise ValidationError(
                    "Erro: não é possível concluir sem data de início de trabalho."
                )
            if not self.data_fim_intervencao:
                raise ValidationError(
                    "Erro: não é possível concluir sem data de fim de trabalho."
                )
            if not self.tecnico_id:
                raise ValidationError(
                    "Erro: não é possível concluir sem técnico atribuído."
                )

        status_final = self.status in {self.StatusChoices.FECHADO, self.StatusChoices.CONCLUIDO}
        if status_final and not self.data_inicio_intervencao:
            raise ValidationError(
                "Erro: não foi fornecida a data de início da intervenção."
            )

        # ── Bloqueio de edição em intervenções fechadas/concluídas ──────────
        if self.pk:
            antiga = Intervencao.objects.filter(pk=self.pk).first()
            if antiga and antiga.status in {
                self.StatusChoices.FECHADO,
                self.StatusChoices.CONCLUIDO,
            }:
                utilizador = getattr(self, "_utilizador", None)
                if utilizador and utilizador.perfil != Usuario.PerfilChoices.ADMIN:
                    raise ValidationError(
                        "Esta intervenção está fechada e não pode ser editada."
                    )

    # ── Métodos auxiliares privados ──────────────────────────────────────────

    def _calcular_horas_trabalhadas(self):
        """Calcula horas_trabalhadas a partir das datas de início e fim."""
        if self.data_inicio_intervencao and self.data_fim_intervencao:
            diferenca = self.data_fim_intervencao - self.data_inicio_intervencao
            self.horas_trabalhadas = round(
                Decimal(str(diferenca.total_seconds() / 3600)), 2
            )

    def _auto_atribuir_contrato(self, kwargs):
        """Atribui automaticamente o contrato activo com horas disponíveis."""
        if not self.contrato_id and self.cliente_id and self.cliente.empresa_id:
            contratos_ativos = Contrato.objects.filter(
                Empresa_id=self.cliente.empresa_id,
                status=Contrato.StatusChoices.ACTIVO,
                is_deleted=False,
            ).order_by("data_fim", "data_criacao")

            self.contrato = next(
                (c for c in contratos_ativos if c.horas_disponiveis > Decimal("0.00")),
                contratos_ativos.first(),
            )

            if self.contrato_id:
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"contrato"}

    def _gerar_numero(self):
        """Gera o número único da intervenção de forma segura contra concorrência."""
        if not self.numero:
            with transaction.atomic():
                date_part = timezone.now().year
                ultimo = (
                    Intervencao.objects.select_for_update()
                    .filter(data_abertura__year=date_part, numero__startswith=f"INT-{date_part}-")
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

                self.numero = f"INT-{date_part}-{last_id:03d}"









    def _atualizar_estado_sla(self, kwargs):
        """Marca a intervenção como expirada se o SLA tiver terminado."""
        sla = self.sla
        if (
            sla
            and sla.get("horas_restantes", 1) == 0
            and self.estado != self.Estado.EXPIRADO
        ):
            self.estado = self.Estado.EXPIRADO
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"estado"}

            admins = Usuario.objects.filter(
                perfil=Usuario.PerfilChoices.ADMIN,
                is_deleted=False,
                status=Usuario.StatusChoices.ACTIVO,
            )
            notificacoes = [
                Notificacao(
                    utilizador=admin,
                    titulo=f"Alerta: Intervenção expirada {self.numero}",
                    mensagem=(
                        f"A intervenção {self.numero} expirou.\n"
                        f"- Número: {self.numero}\n"
                        f"- Título: {self.titulo}\n"
                        f"- Prioridade: {self.prioridade}\n"
                        f"- Tipo de actuação: {self.actuacao_tipo}\n"
                        f"- Cliente: {self.cliente.nome} / Empresa: {self.cliente.empresa.nome}"
                    ),
                    tipo="Alerta",
                    #link=f"{settings.SITE_URL}/api/v1/intervencoes/{self.id}/",
                )
                for admin in admins
            ]
            if notificacoes:
                Notificacao.objects.bulk_create(notificacoes)

    def _notificar_tecnico(self, tecnico_anterior_id):
        """Envia notificação ao técnico apenas quando este é atribuído/alterado."""
        if self.tecnico_id and self.tecnico_id != tecnico_anterior_id:
            Notificacao.objects.create(
                utilizador=self.tecnico,
                titulo=f"Nova intervenção na empresa {self.cliente.empresa.nome}",
                mensagem=(
                    f"Foi-lhe atribuída uma nova intervenção.\n"
                    f"- Número: {self.numero}\n"
                    f"- Título: {self.titulo}\n"
                    f"- Prioridade: {self.prioridade}\n"
                    f"- Tipo de actuação: {self.actuacao_tipo}\n"
                    f"- Cliente: {self.cliente.nome} / Empresa: {self.cliente.empresa.nome}"
                ),
                tipo="informação",
               # link=f"{settings.SITE_URL}/api/v1/intervencoes/{self.id}/",
            )

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        
        # Guardar IDs anteriores para comparações
        contrato_anterior_id = None
        tecnico_anterior_id = None
        if self.pk:
            anterior = (
                Intervencao.objects.filter(pk=self.pk)
                .values("contrato_id", "tecnico_id")
                .first()
            )
            if anterior:
                contrato_anterior_id = anterior["contrato_id"]
                tecnico_anterior_id = anterior["tecnico_id"]

        # 1. Auto-atribuir contrato
        self._auto_atribuir_contrato(kwargs)

        # 2. Calcular horas a partir das datas (necessário antes do clean)
        self._calcular_horas_trabalhadas()

        # 3. Gerar número (necessário antes do clean para unicidade)
        self._gerar_numero()

        # 4. Validar — todos os valores já estão calculados
        self.full_clean(exclude=None)

        # 5. Actualizar estado SLA (efeito secundário, depois da validação)
        self._atualizar_estado_sla(kwargs)

        # 6. Definir data_conclusao se status for final
        status_final = self.status in {self.StatusChoices.FECHADO, self.StatusChoices.CONCLUIDO}
        if status_final and not self.data_conclusao:
            if not self.data_fim_intervencao:
                self.data_fim_intervencao = timezone.now()
            self.data_conclusao = timezone.now()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {
                    "data_conclusao", "data_fim_intervencao"
                }

        # 7. Gravar
        super().save(*args, **kwargs)

        # 8. Notificar técnico (após gravar, pois precisa do self.id)
        self._notificar_tecnico(tecnico_anterior_id)

        # 9. Actualizar horas usadas nos contratos afectados
        for contrato_id in {contrato_anterior_id, self.contrato_id}:
            if contrato_id:
                Contrato.atualizar_horas_utilizadas(contrato_id)


# ── Histórico ────────────────────────────────────────────────────────────────

class HistoricoEstadoIntervencao(ModeloUUIDComTimestamps):
    intervencao = models.ForeignKey(
        Intervencao, related_name="historico_status", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=Intervencao.StatusChoices.choices)
    alterado_por = models.ForeignKey(
        Usuario,
        related_name="status_alterados",
        on_delete=models.SET_NULL,
        null=True,
    )
    nota = models.CharField(max_length=255, blank=True)


# ── Comentários ──────────────────────────────────────────────────────────────

class ComentarioIntervencao(ModeloUUIDComTimestamps, SoftDeleteModel):
    intervencao = models.ForeignKey(
        Intervencao, related_name="comentarios", on_delete=models.CASCADE
    )
    usuario = models.ForeignKey(
        Usuario, related_name="comentarios_intervencao", on_delete=models.CASCADE
    )
    texto = models.TextField()
    visivel_cliente = models.BooleanField(default=True)


# ── Anexos ───────────────────────────────────────────────────────────────────

class AnexoIntervencao(ModeloUUIDComTimestamps, SoftDeleteModel):
    intervencao = models.ForeignKey(
        Intervencao, related_name="anexos", on_delete=models.CASCADE
    )
    utilizador = models.ForeignKey(
        Usuario,
        related_name="anexos_intervencao",
        on_delete=models.SET_NULL,
        null=True,
    )
    arquivo = models.FileField(upload_to="intervencoes/anexos/")
    descricao = models.CharField(max_length=255, blank=True)
    tamanho = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.arquivo and hasattr(self.arquivo, "size"):
            self.tamanho = self.arquivo.size
        super().save(*args, **kwargs)


# ── Horas de trabalho ────────────────────────────────────────────────────────

class HoraTrabalho(ModeloUUIDComTimestamps):
    class TipoChoices(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        REMOTO = "remoto", "Remoto"

    intervencao = models.ForeignKey(
        Intervencao, related_name="horas", on_delete=models.CASCADE
    )
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
        # Usar .update() em vez de .save() para evitar re-executar
        # toda a lógica (full_clean, notificações, etc.) da Intervencao.
        total = (
            self.intervencao.horas.aggregate(total=models.Sum("horas"))["total"]
            or Decimal("0.00")
        )
        Intervencao.objects.filter(pk=self.intervencao_id).update(
            horas_trabalhadas=total
        )
        # Actualizar horas do contrato directamente
        if self.intervencao.contrato_id:
            Contrato.atualizar_horas_utilizadas(self.intervencao.contrato_id)


TecnicoRelatorio = HoraTrabalho