from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.calendario.models import (
    CategoriaObrigacao, DocumentoObrigacao, HistoricoObrigacao,
    ObrigacaoFiscal, TarefaFiscal,
)
from apps.calendario.serializers import (
    CategoriaSerializer, DocumentoSerializer, HistoricoSerializer,
    ObrigacaoSerializer, TarefaSerializer,
)
from apps.configuracoes.responses import resposta_sucesso
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario


@extend_schema(tags=["Calendário Fiscal - Categorias"])
class CategoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CategoriaSerializer
    queryset = CategoriaObrigacao.objects.all()

    def list(self, request, *args, **kwargs):
        return resposta_sucesso(data=self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data)


@extend_schema(tags=["Calendário Fiscal - Obrigações"])
class ObrigacaoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ObrigacaoSerializer
    filterset_fields = ("cliente", "categoria", "periodicidade", "estado_execucao", "responsavel")
    search_fields = ("observacoes", "categoria__nome", "cliente__nome")
    ordering_fields = ("data_vencimento", "data_execucao", "data_criacao")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ObrigacaoFiscal.objects.none()
        qs = ObrigacaoFiscal.objects.select_related("cliente", "categoria", "responsavel")
        u = self.request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(responsavel=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(cliente=u)
        return qs


@extend_schema(tags=["Calendário Fiscal - Tarefas"])
class TarefaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TarefaSerializer
    filterset_fields = ("obrigacao", "status", "responsavel")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TarefaFiscal.objects.none()
        qs = TarefaFiscal.objects.select_related("obrigacao", "responsavel")
        u = self.request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(responsavel=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(obrigacao__cliente=u)
        return qs


@extend_schema(tags=["Calendário Fiscal - Documentos"])
class DocumentoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentoSerializer
    filterset_fields = ("obrigacao",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DocumentoObrigacao.objects.none()
        return DocumentoObrigacao.objects.select_related("obrigacao")


@extend_schema(tags=["Calendário Fiscal - Alertas e relatórios"])
class CalendarioExtraViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="alertas")
    def alertas(self, request):
        qs = self._base(request)
        hoje = timezone.now().date()
        vencidas = [self._fmt(o) for o in qs if o.vencida]
        proximas = [self._fmt(o) for o in qs if o.proxima]
        pendentes = qs.count()
        return resposta_sucesso(data={"vencidas": vencidas, "proximas": proximas, "pendentes": pendentes})

    @action(detail=False, methods=["get"], url_path="resumo")
    def resumo(self, request):
        qs = self._base(request)
        return resposta_sucesso(data={
            "total": qs.count(),
            "concluidas": qs.filter(estado_execucao="concluida").count(),
            "canceladas": qs.filter(estado_execucao="cancelada").count(),
            "pendentes": qs.filter(estado_execucao="pendente").count(),
        })

    def _base(self, request):
        qs = ObrigacaoFiscal.objects.select_related("cliente", "categoria", "responsavel")
        u = request.user
        if u.perfil == Usuario.PerfilChoices.TECNICO:
            qs = qs.filter(responsavel=u)
        elif u.perfil == Usuario.PerfilChoices.CLIENTE:
            qs = qs.filter(cliente=u)
        return qs

    def _fmt(self, o):
        return {"id": str(o.id), "cliente": o.cliente.nome, "categoria": o.categoria.nome,
                "data_vencimento": str(o.data_vencimento), "estado": o.estado_execucao}

    @action(detail=False, methods=["post"], url_path="alertar")
    def alertar(self, request):
        from datetime import date
        from apps.sistema import evolution
        from apps.usuarios.models import Usuario
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            return resposta_sucesso(data={"erro": "Apenas admin."})
        hoje = date.today()
        alvos = ObrigacaoFiscal.objects.select_related("cliente", "categoria").filter(
            data_vencimento__lte=hoje, estado_execucao__in=("pendente", "preparacao", "validacao")
        )
        # acrescenta próximas (5 dias, ou dias_alerta da categoria)
        proximas = [o for o in ObrigacaoFiscal.objects.all() if o.proxima]
        admins = Usuario.objects.filter(perfil=Usuario.PerfilChoices.ADMIN).exclude(telefone="").exclude(telefone__isnull=True)
        enviados = 0
        texto = f"Calendário Fiscal: {len(alvos)} vencidas, {len(proximas)} próximas (5 dias)."
        for adm in admins:
            numero = evolution.normalizar_numero(adm.telefone)
            if numero:
                evolution.enviar_texto(numero, texto)
                enviados += 1
        return resposta_sucesso(data={"enviados": enviados, "vencidas": len(alvos), "proximas": len(proximas)})
