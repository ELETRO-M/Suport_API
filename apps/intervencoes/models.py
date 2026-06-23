import re
import time
from datetime import timedelta
from decimal import Decimal
from urllib.parse import unquote, urlparse

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.utils import timezone

from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel
from apps.contratos.models import Contrato
from apps.notificacoes.models import Notificacao
from apps.sistema.models import ConfiguracaoSistema
from apps.usuarios.models import Usuario


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
            "perfil__in": [Usuario.PerfilChoices.CLIENTE],
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
            contrato_anterior_id = None
            if self.pk:
                contrato_anterior_id = (
                    Intervencao.objects.filter(pk=self.pk)
                    .values_list("contrato_id", flat=True)
                    .first()
                )
            contrato_foi_alterado = not self.pk or contrato_anterior_id != self.contrato_id
            if contrato_foi_alterado and self.contrato.status != Contrato.StatusChoices.ACTIVO:
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
        """Gera o número único da intervenção usando lock de advisory no PostgreSQL."""
        if self.numero:
            return
        date_part = timezone.now().year
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [date_part])
            ultimo = (
                Intervencao.all_objects.filter(numero__startswith=f"INT-{date_part}-")
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

        # 2. Calcular horas a partir das datas (necessário antes do clean)
        self._calcular_horas_trabalhadas()

        # 3. Validar e processar lógica de negócio
        is_deleting = "is_deleted" in (kwargs.get("update_fields") or {})
        if not is_deleting:
            self.full_clean(exclude=["contrato"])
            self._atualizar_estado_sla(kwargs)

            status_final = self.status in {self.StatusChoices.FECHADO, self.StatusChoices.CONCLUIDO}
            if status_final and not self.data_conclusao:
                self.data_conclusao = timezone.now()
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {
                        "data_conclusao"
                    }

        # 4. Gravar (número gerado dentro da mesma transação com advisory lock)
        if self._state.adding:
            with transaction.atomic():
                self._gerar_numero()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

        # 6. Se o técnico foi atribuído ou alterado, (re)aplicar marca d'água
        if not is_deleting and self.tecnico_id and tecnico_anterior_id != self.tecnico_id:
            for anexo in self.anexos.all():
                anexo.arquivo_marcado_url = ""
                anexo.save(update_fields=["arquivo_marcado_url"])
                anexo.gerar_marca_dagua()

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
    arquivo_marcado_url = models.URLField(blank=True, default="")

    @staticmethod
    def _extrair_public_id(url):
        path = unquote(urlparse(url).path)
        path = re.sub(r"^/.+?/upload/", "", path)
        path = re.sub(r"^v\d+/", "", path)
        return path.rsplit(".", 1)[0]

    @staticmethod
    def _extrair_resource_type(url):
        match = re.search(r"/(raw|image|video)/upload/", urlparse(url).path)
        return match.group(1) if match else "image"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if self.arquivo and hasattr(self.arquivo, "size"):
            self.tamanho = self.arquivo.size
        super().save(*args, **kwargs)
        if is_new and self.intervencao.tecnico_id:
            self.gerar_marca_dagua()

    FORMATOS_MARCA = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "pdf", "ico"}

    def gerar_marca_dagua(self):
        tecnico = self.intervencao.tecnico
        if not tecnico:
            return

        ext = self.arquivo.name.rsplit(".", 1)[-1].lower()
        if ext not in self.FORMATOS_MARCA:
            return

        texto_marca = f"{tecnico.nome} - {tecnico.BI}"
        wm_public_id = re.sub(r"[^a-zA-Z0-9_/.-]", "_", f"{self.arquivo.name.rsplit('.', 1)[0]}_wm")

        try:
            src_url = cloudinary.utils.private_download_url(
                self.arquivo.name, ext,
                resource_type="raw", type="upload",
                expires_at=int(time.time()) + 120, attachment=False,
            )

            import io, requests as _requests
            resp = _requests.get(src_url, timeout=60)
            if resp.status_code != 200:
                return

            if ext == "pdf":
                from pypdf import PdfReader, PdfWriter
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas as rl_canvas

                reader = PdfReader(io.BytesIO(resp.content))
                writer = PdfWriter()

                page_w = float(reader.pages[0].mediabox.width)
                page_h = float(reader.pages[0].mediabox.height)

                wm_buf = io.BytesIO()
                c = rl_canvas.Canvas(wm_buf, pagesize=(page_w, page_h))
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(1, 0, 0, 0.30)
                c.setPageRotation(0)
                cols = int(page_w // 130) + 2
                rows = int(page_h // 35) + 2
                for row in range(rows):
                    for col in range(cols):
                        x = col * 130
                        y = row * 35
                        c.saveState()
                        c.translate(x, y)
                        c.rotate(45)
                        c.drawString(0, 0, texto_marca)
                        c.restoreState()
                c.showPage()
                c.save()
                wm_buf.seek(0)

                wm_reader = PdfReader(wm_buf)
                wm_page = wm_reader.pages[0]

                for page in reader.pages:
                    page.merge_page(wm_page, over=True)
                    writer.add_page(page)

                out_buf = io.BytesIO()
                writer.write(out_buf)
                out_buf.seek(0)

                result = cloudinary.uploader.upload(
                    out_buf,
                    public_id=wm_public_id,
                    resource_type="image",
                    overwrite=True,
                )
                self.arquivo_marcado_url = result["secure_url"]
            else:
                transformation = [
                    {"overlay": f"text:Arial_24_bold:{texto_marca}"},
                    {"opacity": 35, "width": 200, "height": 80, "flags": "tiled"},
                    {"flags": "layer_apply"},
                    {"fetch_format": ext},
                ]
                result = cloudinary.uploader.upload(
                    resp.content,
                    public_id=wm_public_id,
                    resource_type="image",
                    transformation=transformation,
                    overwrite=True,
                )
                self.arquivo_marcado_url = result["secure_url"]

            super().save(update_fields=["arquivo_marcado_url"])
        except Exception:
            pass

    def url_para(self, usuario):
        if usuario.is_staff or usuario.perfil in (Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.CLIENTE):
            ext = self.arquivo.name.rsplit(".", 1)[-1]
            return cloudinary.utils.private_download_url(
                self.arquivo.name, ext,
                resource_type="raw", type="upload",
                expires_at=int(time.time()) + 86400,
                attachment=False,
            )

        if not self.arquivo_marcado_url:
            ext = self.arquivo.name.rsplit(".", 1)[-1]
            return cloudinary.utils.private_download_url(
                self.arquivo.name, ext,
                resource_type="raw", type="upload",
                expires_at=int(time.time()) + 300,
                attachment=False,
            )

        public_id = self._extrair_public_id(self.arquivo_marcado_url)
        filename = self.arquivo_marcado_url.rsplit("/", 1)[-1]
        fmt = filename.rsplit(".", 1)[-1] if "." in filename else self.arquivo.name.rsplit(".", 1)[-1]
        res_type = self._extrair_resource_type(self.arquivo_marcado_url)
        return cloudinary.utils.private_download_url(
            public_id, fmt,
            resource_type=res_type, type="upload",
            expires_at=int(time.time()) + 300,
            attachment=False,
        )
 


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
