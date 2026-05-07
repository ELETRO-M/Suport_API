from django.db.models import Avg, Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.contratos.models import Contrato
from apps.intervencoes.models import HoraTrabalho, Intervencao

@extend_schema(tags=["Admin"])
class RelatorioViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Intervencao.objects.none()

    @action(detail=False, methods=["get"], url_path="dashboard-admin")
    def dashboard_admin(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        data = {
            "total_clientes": Usuario.objects.filter(perfil=Usuario.PerfilChoices.CLIENTE).count(),
            "total_contratos_ativos": Contrato.objects.filter(status="activo").count(),
            "total_intervencoes": Intervencao.objects.count(),
            "intervencoes_abertas": Intervencao.objects.filter(status="aberto").count(),
            "intervencoes_em_andamento": Intervencao.objects.filter(status="em_andamento").count(),
            "intervencoes_resolvidas": Intervencao.objects.filter(status="resolvido").count(),
            "intervencoes_fechadas": Intervencao.objects.filter(status="fechado").count(),
            "intervencoes_concluidas": Intervencao.objects.filter(status="concluido").count(),
            "total_horas_trabalhadas": HoraTrabalho.objects.aggregate(total=Sum("horas"))["total"] or 0,
            "receita_total": Contrato.objects.aggregate(total=Sum("valor_total"))["total"] or 0,
            "tecnicos_ativos": Usuario.objects.filter(perfil=Usuario.PerfilChoices.TECNICO, status="activo").count(),
            "grafico_intervencoes_mes": [],
            "grafico_horas_tecnico": [],
            "top_clientes": [],
        }
        return resposta_sucesso(data=data)

    @action(detail=False, methods=["get"], url_path="dashboard-tecnico")
    def dashboard_tecnico(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        data = {
            "intervencoes_atribuidas": Intervencao.objects.filter(tecnico=request.user).count(),
            "intervencoes_em_andamento": Intervencao.objects.filter(tecnico=request.user, status="em_andamento").count(),
            "intervencoes_concluidas_mes": Intervencao.objects.filter(
                tecnico=request.user,
                status="concluido",
            ).count(),
            "total_horas_mes": HoraTrabalho.objects.filter(tecnico=request.user).aggregate(total=Sum("horas"))["total"] or 0,
            "media_horas_dia": HoraTrabalho.objects.filter(tecnico=request.user).aggregate(media=Avg("horas"))["media"] or 0,
            "proximas_intervencoes": [],
            "grafico_horas_semana": [],
        }
        return resposta_sucesso(data=data)

    @action(detail=False, methods=["get"], url_path="dashboard-cliente")
    def dashboard_cliente(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        contratos = Contrato.objects.filter(cliente=request.user, status="activo")
        total_horas_contratadas = sum((item.horas_contratadas for item in contratos), 0)
        total_horas_utilizadas = sum((item.horas_utilizadas for item in contratos), 0)
        total_horas_disponiveis = sum((item.horas_disponiveis for item in contratos), 0)
        percentual = 0
        if total_horas_contratadas:
            percentual = float(total_horas_utilizadas / total_horas_contratadas) * 100
        data = {
            "contratos_ativos": contratos.count(),
            "total_horas_contratadas": total_horas_contratadas,
            "total_horas_utilizadas": total_horas_utilizadas,
            "total_horas_disponiveis": total_horas_disponiveis,
            "percentual_utilizacao": round(percentual, 2),
            "intervencoes_abertas": Intervencao.objects.filter(cliente=request.user, status="aberto").count(),
            "intervencoes_em_andamento": Intervencao.objects.filter(cliente=request.user, status="em_andamento").count(),
            "intervencoes_concluidas_mes": Intervencao.objects.filter(cliente=request.user, status="concluido").count(),
            "grafico_uso_horas": [],
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

        data = {
            "total_intervencoes": queryset.count(),
            "por_status": list(queryset.values("status").annotate(total=Count("id"))),
            "por_prioridade": list(queryset.values("prioridade").annotate(total=Count("id"))),
            "tempo_medio_resolucao": 0,
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

    @action(detail=False, methods=["get"], url_path="financeiro")
    def relatorio_financeiro(self, request: Request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        contratos = Contrato.objects.all()
        data = {
            "receita_total": contratos.aggregate(total=Sum("valor_total"))["total"] or 0,
            "receita_mes": 0,
            "por_cliente": list(contratos.values("cliente__nome").annotate(total=Sum("valor_total"))),
            "por_contrato": list(contratos.values("tipo").annotate(total=Sum("valor_total"))),
            "contratos_vencendo": [
                {
                    "id": str(item.id),
                    "cliente_nome": item.cliente.nome,
                    "data_fim": item.data_fim,
                }
                for item in contratos.order_by("data_fim")[:10]
            ],
            "previsao_receita": contratos.aggregate(total=Sum("valor_total"))["total"] or 0,
        }
        return resposta_sucesso(data=data)
