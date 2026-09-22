from decimal import Decimal

from django.db.models import Avg, Count, F, Sum
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from apps.usuarios.models import Usuario, empresa
from apps.configuracoes.responses import resposta_sucesso
from apps.configuracoes.schema import resposta_erro as esquema_erro, resposta_sucesso as esquema_resposta
from apps.contratos.models import Contrato
from apps.intervencoes.models import HoraTrabalho, Intervencao
from apps.tarefas.models import Tarefa
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone


class RelatorioSerializer(serializers.Serializer):
    pass


@extend_schema(tags=["Relatórios"])
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
                status=Intervencao.StatusChoices.FECHADO,
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

        contratos = Contrato.objects.filter(Empresa=request.user.empresa, status="activo")

        total_horas_contratadas = sum(
            (c.horas_contratadas or Decimal("0.00")) for c in contratos
        )
        total_horas_utilizadas = sum(
            (c.horas_utilizadas or Decimal("0.00")) for c in contratos
        )
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
            "Tickets Abertos":Intervencao.objects.filter(cliente=request.user).count(),
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
                status="fechado"
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

            total_horas += float(item.horas_trabalhadas or 0)

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
            "tempo_medio_resolucao": f"{tempo_medio_resolucao} horas",
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
            "por_empresa": list(contratos.values("Empresa__nome").annotate(total=Sum("valor_total"))),
            "por_contrato": list(contratos.values("tipo_contrato").annotate(total=Sum("valor_total"))),
            "contratos_vencendo": [
                {
                    "id": str(item.id),
                    "empresa_nome": item.Empresa.nome if item.Empresa else None,
                    "data_fim": item.data_fim,
                }
                for item in contratos.order_by("data_fim")[:10]
            ],
            "previsao_receita": contratos.aggregate(total=Sum("valor_total"))["total"] or 0,
        }
        return resposta_sucesso(data=data)

    @extend_schema(
        summary="Relatório de tarefas",
        operation_id="relatorio_tarefas",
        description=(
            "Relatório das tarefas internas da equipa. O **admin** vê todas as tarefas; o **técnico** "
            "vê apenas as que lhe estão atribuídas. Inclui totais por estado/prioridade, taxa de "
            "cumprimento de prazo e tempo médio de conclusão."
        ),
        parameters=[
            OpenApiParameter(name="atribuido_a_id", description="Filtra pelo responsável (ID).", required=False),
            OpenApiParameter(name="intervencao_id", description="Filtra pela intervenção associada (ID).", required=False),
            OpenApiParameter(
                name="estado",
                description="Filtra pelo estado.",
                required=False,
                enum=["pendente", "em_progresso", "concluida", "cancelada", "expirado"],
            ),
            OpenApiParameter(
                name="prioridade",
                description="Filtra pela prioridade.",
                required=False,
                enum=["baixa", "media", "alta", "urgente"],
            ),
            OpenApiParameter(name="data_inicio", description="Data de criação mínima (YYYY-MM-DD).", required=False),
            OpenApiParameter(name="data_fim", description="Data de criação máxima (YYYY-MM-DD).", required=False),
        ],
        responses={
            200: esquema_resposta(
                serializers.DictField(),
                "Relatório de tarefas.",
                "RelatorioTarefas",
                exemplos=[
                    OpenApiExample(
                        "Exemplo",
                        value={
                            "total_tarefas": 10,
                            "por_estado": [{"estado": "pendente", "total": 3}],
                            "por_prioridade": [{"prioridade": "alta", "total": 4}],
                            "total_concluidas": 5,
                            "concluidas_no_prazo": 4,
                            "expiradas": 1,
                            "taxa_cumprimento_prazo": 80.0,
                            "tempo_medio_conclusao_horas": 24.5,
                            "tarefas": [{"id": "uuid", "numero": "TAR-2026-001", "titulo": "…"}],
                        },
                    )
                ],
            ),
            403: esquema_erro("Sem permissão para este relatório."),
        },
    )
    @action(detail=False, methods=["get"], url_path="tarefas")
    def relatorio_tarefas(self, request: Request):
        if request.user.perfil not in [
            Usuario.PerfilChoices.ADMIN,
            Usuario.PerfilChoices.TECNICO,
        ]:
            self.permission_denied(request, message="Sem permissão para este relatório.")

        queryset = Tarefa.objects.all()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            queryset = queryset.filter(atribuido_a=request.user)
        if request.query_params.get("atribuido_a_id"):
            queryset = queryset.filter(atribuido_a_id=request.query_params["atribuido_a_id"])
        if request.query_params.get("intervencao_id"):
            queryset = queryset.filter(intervencao_id=request.query_params["intervencao_id"])
        if request.query_params.get("estado"):
            queryset = queryset.filter(estado=request.query_params["estado"])
        if request.query_params.get("prioridade"):
            queryset = queryset.filter(prioridade=request.query_params["prioridade"])
        if request.query_params.get("data_inicio"):
            queryset = queryset.filter(data_criacao__date__gte=request.query_params["data_inicio"])
        if request.query_params.get("data_fim"):
            queryset = queryset.filter(data_criacao__date__lte=request.query_params["data_fim"])

        concluidas = queryset.filter(estado=Tarefa.EstadoChoices.CONCLUIDA)
        concluidas_no_prazo = concluidas.filter(
            data_conclusao__isnull=False,
            data_fim__isnull=False,
            data_conclusao__lte=F("data_fim"),
        ).count()
        total_concluidas = concluidas.count()

        taxa_cumprimento = (
            round(concluidas_no_prazo * 100.0 / total_concluidas, 2)
            if total_concluidas
            else 0
        )

        duracao_media = concluidas.filter(
            data_conclusao__isnull=False,
            data_inicio__isnull=False,
        ).annotate(duracao=F("data_conclusao") - F("data_inicio")).aggregate(
            media=Avg("duracao")
        )["media"]

        tempo_medio_conclusao_horas = (
            round(duracao_media.total_seconds() / 3600, 2) if duracao_media else 0
        )

        data = {
            "total_tarefas": queryset.count(),
            "por_estado": list(queryset.values("estado").annotate(total=Count("id"))),
            "por_prioridade": list(queryset.values("prioridade").annotate(total=Count("id"))),
            "total_concluidas": total_concluidas,
            "concluidas_no_prazo": concluidas_no_prazo,
            "expiradas": queryset.filter(estado=Tarefa.EstadoChoices.EXPIRADO).count(),
            "taxa_cumprimento_prazo": taxa_cumprimento,
            "tempo_medio_conclusao_horas": tempo_medio_conclusao_horas,
            "tarefas": [
                {
                    "id": str(item.id),
                    "numero": item.numero,
                    "titulo": item.titulo,
                    "estado": item.estado,
                    "prioridade": item.prioridade,
                    "atribuido_a": item.atribuido_a.nome if item.atribuido_a else None,
                    "criado_por": item.criado_por.nome if item.criado_por else None,
                    "intervencao": item.intervencao.numero if item.intervencao else None,
                    "data_inicio": item.data_inicio,
                    "data_fim": item.data_fim,
                    "data_conclusao": item.data_conclusao,
                    "prazo_restante_horas": item.prazo["restantes_horas"] if item.prazo else None,
                    "expirado": bool(item.prazo and item.prazo["expirado"]),
                }
                for item in queryset.select_related("atribuido_a", "criado_por", "intervencao")[:100]
            ],
        }
        return resposta_sucesso(data=data)
    
