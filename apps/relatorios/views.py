from django.db.models import Avg, Count, Sum
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from apps.usuarios.models import Usuario, empresa
from apps.configuracoes.responses import resposta_sucesso
from apps.contratos.models import Contrato
from apps.intervencoes.models import HoraTrabalho, Intervencao
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone


class RelatorioSerializer(serializers.Serializer):
    pass


@extend_schema(tags=["Admin"])
class RelatorioViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Intervencao.objects.none()
    serializer_class = RelatorioSerializer

    @action(detail=False, methods=["get"], url_path="dashboard-admin")
    def dashboard_admin(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")

        grafico_intervencoes_mes = list(
        Intervencao.objects
        .annotate(mes=TruncMonth("data_abertura"))
        .values("mes")
        .annotate(
            total=Count("id")
        )
        .order_by("mes")
        )
        grafico_horas_tecnico = list(
            Intervencao.objects
            .values("tecnico__nome")
            .annotate(
                total=Sum("horas_trabalhadas")
            )
            .order_by("-total")
        )
        top_clientes = list(
            Intervencao.objects
            .values("cliente__nome","cliente__empresa__nome")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        top_tecnico = list(
            Intervencao.objects
            .values("tecnico__nome")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        data = {
            "total_empresas": empresa.objects.count(),
            "total_clientes": Usuario.objects.filter(perfil=Usuario.PerfilChoices.CLIENTE).count(),
            "total_contratos_ativos": Contrato.objects.filter(status="activo").count(),
            "total_intervencoes": Intervencao.objects.count(),
            "intervencoes_abertas": Intervencao.objects.filter(status="aberto").count(),
            "intervencoes_em_andamento": Intervencao.objects.filter(status="em_andamento").count(),
            "intervencoes_resolvidas": Intervencao.objects.filter(status="resolvido").count(),
            "intervencoes_fechadas": Intervencao.objects.filter(status="fechado").count(),
            "intervencoes_concluidas": Intervencao.objects.filter(status="concluido").count(),
            "receita_total": Contrato.objects.aggregate(total=Sum("valor_total"))["total"] or 0,
            "tecnicos_ativos": Usuario.objects.filter(perfil=Usuario.PerfilChoices.TECNICO, status="activo").count(),
            "grafico_intervencoes_mes": grafico_intervencoes_mes,
            "grafico_horas_tecnico": grafico_horas_tecnico,
            "top_clientes": top_clientes,
            
        }
        return resposta_sucesso(data=data)

    @action(detail=False, methods=["get"], url_path="dashboard-tecnico")
    def dashboard_tecnico(self, request: Request):

        if request.user.perfil not in [
            Usuario.PerfilChoices.ADMIN,
            Usuario.PerfilChoices.TECNICO
        ]:
            self.permission_denied(request)

        agora = timezone.now()

        intervencoes = Intervencao.objects.filter(tecnico=request.user)

        base = {
            "intervencoes_atribuidas": intervencoes.count(),

            "intervencoes_em_andamento": intervencoes.filter(
                status=Intervencao.StatusChoices.EM_ANDAMENTO
            ).count(),

            "intervencoes_concluidas_mes": intervencoes.filter(
                status=Intervencao.StatusChoices.CONCLUIDO,
                data_conclusao__year=agora.year,
                data_conclusao__month=agora.month
            ).count(),

            "total_horas_mes": float(
                intervencoes.filter(
                    data_conclusao__year=agora.year,
                    data_conclusao__month=agora.month
                ).aggregate(
                    total=Sum("horas_trabalhadas")
                )["total"] or 0
            ),

            "media_horas_dia": float(
                intervencoes.aggregate(
                    media=Avg("horas_trabalhadas")
                )["media"] or 0
            ),
        }

        base["proximas_intervencoes"] = [
            {
                "id": str(i.id),
                "numero": i.numero,
                "titulo": i.titulo,
                "status": i.status,
            }
            for i in intervencoes.exclude(
                status__in=[
                    Intervencao.StatusChoices.FECHADO,
                    Intervencao.StatusChoices.CONCLUIDO
                ]
            )[:5]
        ]

        base["grafico_horas_semana"] = list(
            intervencoes
            .annotate(semana=TruncWeek("data_abertura"))
            .values("semana")
            .annotate(total=Sum("horas_trabalhadas"))
            .order_by("semana")
        )

        return resposta_sucesso(data=base)

    @action(detail=False, methods=["get"], url_path="dashboard-cliente")
    def dashboard_cliente(self, request: Request):

        if request.user.perfil not in [
            Usuario.PerfilChoices.ADMIN,
            Usuario.PerfilChoices.CLIENTE
        ]:
            self.permission_denied(request, message="Sem permissão para este recurso.")

        contratos = Contrato.objects.filter(cliente=request.user, status="activo")

        total_horas_contratadas = sum(c.horas_contratadas for c in contratos)
        total_horas_utilizadas = sum(c.horas_utilizadas for c in contratos)
        total_horas_disponiveis = sum(c.horas_disponiveis for c in contratos)

        percentual = (
            float(total_horas_utilizadas / total_horas_contratadas) * 100
            if total_horas_contratadas else 0
        )

        data = {
            "contratos_ativos": contratos.count(),
            "total_horas_contratadas": total_horas_contratadas,
            "total_horas_utilizadas": total_horas_utilizadas,
            "total_horas_disponiveis": total_horas_disponiveis,
            "percentual_utilizacao": round(percentual, 2),

            "intervencoes_abertas": Intervencao.objects.filter(
                cliente=request.user,
                status="aberto"
            ).count(),

            "intervencoes_em_andamento": Intervencao.objects.filter(
                cliente=request.user,
                status="em_andamento"
            ).count(),

            "intervencoes_concluidas": Intervencao.objects.filter(
                cliente=request.user,
                status="concluido"
            ).count(),

            "grafico_uso_horas": Intervencao.objects.filter(
                cliente=request.user
            ).annotate(
                mes=TruncMonth("data_abertura")
            ).values("mes").annotate(
                total=Sum("horas_trabalhadas")
            )
        }

        return resposta_sucesso(data=data)
    

    @action(detail=False, methods=["get"], url_path="intervencoes")
    def relatorio_intervencoes(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        queryset = Intervencao.objects.all()
        if request.query_params.get("cliente_id"):
            queryset = queryset.filter(cliente_id=request.query_params["cliente_id"])
        if request.query_params.get("tecnico_id"):
            queryset = queryset.filter(tecnico_id=request.query_params["tecnico_id"])
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        if request.query_params.get("data_inicio"):
            queryset = queryset.filter(data_abertura__date__gte=request.query_params["data_inicio"])
        if request.query_params.get("data_fim"):
            queryset = queryset.filter(data_abertura__date__lte=request.query_params["data_fim"])
        intervencoes = Intervencao.objects.filter(data_conclusao__isnull=False)

        total_horas = 0

        for item in intervencoes:

            diferenca = item.data_fim_intervencao - item.data_inicio_intervencao

            horas = diferenca.total_seconds() / 86400

            total_horas += horas

        tempo_medio_resolucao = 0

        if intervencoes.count() > 0:

            tempo_medio_resolucao = round(
                total_horas / intervencoes.count(),
                2
            )

        data = {
            "total_intervencoes": queryset.count(),
            "por_status": list(queryset.values("status").annotate(total=Count("id"))),
            "por_prioridade": list(queryset.values("prioridade").annotate(total=Count("id"))),
            "tempo_medio_resolucao": f"{tempo_medio_resolucao} dias",
            "intervencoes": [
                {
                    "id": str(item.id),
                    "numero": item.numero,
                    "titulo": item.titulo,
                    "status": item.status,
                    "prioridade": item.prioridade,
                }
                for item in queryset[:100]
            ],
        }
        return resposta_sucesso(data=data)
        '''

    @action(detail=False, methods=["get"], url_path="horas")
    def relatorio_horas(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        queryset = HoraTrabalho.objects.select_related("tecnico", "intervencao", "intervencao__cliente")
        if request.query_params.get("tecnico_id"):
            queryset = queryset.filter(tecnico_id=request.query_params["tecnico_id"])
        if request.query_params.get("cliente_id"):
            queryset = queryset.filter(intervencao__cliente_id=request.query_params["cliente_id"])
        if request.query_params.get("data_inicio"):
            queryset = queryset.filter(data_trabalho__gte=request.query_params["data_inicio"])
        if request.query_params.get("data_fim"):
            queryset = queryset.filter(data_trabalho__lte=request.query_params["data_fim"])
        data = {
            "total_horas": queryset.aggregate(total=Sum("horas"))["total"] or 0,
            "por_tecnico": list(queryset.values("tecnico__nome").annotate(total=Sum("horas"))),
            "por_cliente": list(queryset.values("intervencao__cliente__nome").annotate(total=Sum("horas"))),
            "por_tipo": list(queryset.values("tipo").annotate(total=Sum("horas"))),
            "media_horas_intervencao": queryset.aggregate(media=Avg("horas"))["media"] or 0,
            "detalhes": [
                {
                    "id": str(item.id),
                    "intervencao": item.intervencao.numero,
                    "tecnico": item.tecnico.nome,
                    "horas": item.horas,
                }
                for item in queryset[:100]
            ],
        }
        return resposta_sucesso(data=data)
        '''

    @action(detail=False, methods=["get"], url_path="financeiro")
    def relatorio_financeiro(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        contratos = Contrato.objects.all()
        receita_mes = Contrato.objects.filter(
            data_criacao__month=timezone.now().month,
            data_criacao__year=timezone.now().year
        ).aggregate(
            total=Sum("valor_total")
        )["total"] or 0
        data = {
            "receita_total": contratos.aggregate(total=Sum("valor_total"))["total"] or 0,
            "receita_mes": receita_mes,
            "por_cliente": list(contratos.values("cliente__nome").annotate(total=Sum("valor_total"))),
            "por_contrato": list(contratos.values("tipo_contrato").annotate(total=Sum("valor_total"))),
            "contratos_vencendo": [
                {
                    "id": str(item.id),
                    "cliente_nome": item.cliente.nome if item.cliente else None,
                    "empresa_nome": item.cliente.empresa.nome if item.cliente and getattr(item.cliente, "empresa", None) else None,
                    "data_fim": item.data_fim,
                }
                for item in contratos.order_by("data_fim")[:10]
            ],
            "previsao_receita": contratos.aggregate(total=Sum("valor_total"))["total"] or 0,
        }
        return resposta_sucesso(data=data)
    
