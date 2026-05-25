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

        limit_choices_to={"perfil__in": [Usuario.PerfilChoices.CLIENTE, Usuario.PerfilChoices.ADMIN], "is_deleted": False, "status": Usuario.StatusChoices.ACTIVO},
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
        limit_choices_to={"is_deleted": False, "status": Contrato.StatusChoices.ACTIVO}
    )
    estado=models.CharField(choices=Estado.choices , default=Estado.ACTIVO)
    actuacao_tipo = models.CharField(max_length=20, choices=ActuacaoTipo.choices, default=ActuacaoTipo.REMOTO)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ABERTO)
    prioridade = models.CharField(max_length=20, choices=PrioridadeChoices.choices)
    data_abertura = models.DateTimeField(default=timezone.now)
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
        if self.contrato_id:
            if not self.cliente_id:
                raise ValidationError("Erro: não foi fornecido o cliente")
            if self.cliente.empresa_id != self.contrato.Empresa_id:
                raise ValidationError("Erro: o contrato não pertence à empresa do cliente.")
            if self.contrato.status != Contrato.StatusChoices.ACTIVO:
                raise ValidationError("Erro: o contrato associado não está activo.")
            if self.horas_trabalhadas > empresa.self.horas_disponiveis:
                raise ValidationError("Erro: valor de horas trabalhadas não satifaz o contrato")

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
        contrato_anterior_id = None
        if self.pk:
            contrato_anterior_id = (
                Intervencao.objects.filter(pk=self.pk)
                .values_list("contrato_id", flat=True)
                .first()
            )
        if self.horas_trabalhadas > empresa.self.horas_disponiveis:
            raise ValidationError

        if not self.contrato_id and self.cliente_id and self.cliente.empresa_id:
            contratos_ativos = Contrato.objects.filter(
                Empresa_id=self.cliente.empresa_id,
                status=Contrato.StatusChoices.ACTIVO,
                is_deleted=False,
            ).order_by("data_fim", "data_criacao")
            self.contrato = next(
                (contrato for contrato in contratos_ativos if contrato.horas_disponiveis > Decimal("0.00")),
                contratos_ativos.first(),
            )
            if self.contrato_id:
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"contrato"}

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
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"horas_trabalhadas"}
            if self.sla and self.sla.get("horas_restantes", 1) == 0 and self.estado != self.Estado.EXPIRADO:
                self.estado = self.Estado.EXPIRADO
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"estado"}
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
                            mensagem=f"""A intervenção {self.numero} expirou.
                            -Numero da Intervenção: {self.numero} 
                            -Titulo da Intervenção: {self.titulo} 
                            -Prioridade: {self.prioridade} 
                            -Tipo de actuação: {self.actuacao_tipo} 
                            -pelo cliente {self.cliente.nome} na empresa {self.cliente.empresa.nome}""",
                            tipo="Alerta",
                            link=f"{settings.SITE_URL}/api/v1/intervencoes/{self.id}/",
                        )
                    )
                if notificacoes:
                    Notificacao.objects.bulk_create(notificacoes)
    
             

        if self.tecnico:
            Notificacao.objects.create(
                utilizador=self.tecnico,
                titulo=f"Nova intervenção na empresa {self.cliente.empresa.nome} ",
                mensagem=f"""
                 Foi lhe atribuida uma nova intervenção 
                 -Numeiro da Intervenção: {self.numero} 
                 -Titulo da Intervenção: {self.titulo} 
                 -Prioridade: {self.prioridade} 
                 -Tipo de actuação: {self.actuacao_tipo} 
                 -pelo cliente {self.cliente.nome} na empresa {self.cliente.empresa.nome}
                 """,
                tipo="imformação",
                link=f"{settings.SITE_URL}/api/v1/intervencoes/{self.id}/",
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

        contratos_para_atualizar = {contrato_anterior_id, self.contrato_id}
        for contrato_id in contratos_para_atualizar:
            Contrato.atualizar_horas_utilizadas(contrato_id)
       
       

     


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


TecnicoRelatorio = HoraTrabalho


