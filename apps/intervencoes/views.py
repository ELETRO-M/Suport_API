from datetime import timedelta
from typing import cast

from django.db.models import Q
from django.utils import timezone
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.intervencoes.models import (
    AnexoIntervencao,
    ComentarioIntervencao,
    HoraTrabalho,
    Intervencao,
)
from apps.intervencoes.serializers import (
    AdicionarComentarioSerializer,
    AtribuirTecnicoSerializer,
    CarregarAnexoSerializer,
    HoraTrabalhoAtualizacaoSerializer,
    HoraTrabalhoEscritaSerializer,
    HoraTrabalhoListaSerializer,
    IntervencaoAtualizacaoSerializer,
    IntervencaoDetalheSerializer,
    IntervencaoEscritaSerializer,
    IntervencaoListaSerializer,
)
from apps.notificacoes.models import Notificacao


class IntervencaoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]
    ordering_fields = ("data_abertura", "data_conclusao")

    def get_queryset(self):
        request = cast(Request, self.request)
        queryset = Intervencao.objects.select_related("cliente", "tecnico", "contrato").prefetch_related(
            "historico_status",
            "comentarios",
            "anexos",
        )
        params = request.query_params
        if params.get("cliente_id"):
            queryset = queryset.filter(cliente_id=params["cliente_id"])
        if params.get("tecnico_id"):
            queryset = queryset.filter(tecnico_id=params["tecnico_id"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("prioridade"):
            queryset = queryset.filter(prioridade=params["prioridade"])
        if params.get("data_inicio"):
            queryset = queryset.filter(data_abertura__date__gte=params["data_inicio"])
        if params.get("data_fim"):
            queryset = queryset.filter(data_abertura__date__lte=params["data_fim"])

        utilizador = request.user
        if utilizador.perfil == Usuario.PerfilChoices.TECNICO:
            queryset = queryset.filter(tecnico=utilizador)
        elif utilizador.perfil == Usuario.PerfilChoices.CLIENTE:
            queryset = queryset.filter(cliente=utilizador)
        return queryset.order_by("-data_abertura")

    def get_serializer_class(self):#escolha de serialazers
        if self.action == "retrieve":
            return IntervencaoDetalheSerializer
        if self.action == "create":
            return IntervencaoEscritaSerializer
        if self.action in {"update", "partial_update"}:
            return IntervencaoAtualizacaoSerializer
        return IntervencaoListaSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, context={"request": request})
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil not in {Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.CLIENTE}:
            self.permission_denied(request, message="Sem permissão para criar intervenções.")
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        if obj.tecnico_id:
            Notificacao.objects.create(
                utilizador=obj.tecnico,
                tipo="intervencao_atribuida",
                titulo="Nova intervenção atribuída",
                mensagem=f"A intervenção {obj.numero} foi atribuída a si.",
                link=f"/intervencoes/{obj.id}",
            )
        return resposta_sucesso(
            data={"id": str(obj.id), "numero": obj.numero, "status": obj.status},
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="Apenas o técnico atribuído pode atualizar.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            self.permission_denied(request, message="Clientes não podem atualizar intervenções.")
        serializer = self.get_serializer(instance, data=request.data, partial=False, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "status": obj.status})

    def destroy(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem deletar intervenções.")
        instance = self.get_object()
        instance.delete()
        return resposta_sucesso(message="Intervenção deletada com sucesso")

    @action(detail=True, methods=["post"], url_path="atribuir")
    def atribuir(self, request, pk=None):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atribuir técnicos.")
        instance = self.get_object()
        serializer = AtribuirTecnicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tecnico = serializer.validated_data["tecnico_id"]
        instance.tecnico = tecnico
        instance.save(update_fields=["tecnico"])
        Notificacao.objects.create(
            utilizador=tecnico,
            tipo="intervencao_atribuida",
            titulo="Intervenção atribuída",
            mensagem=f"A intervenção {instance.numero} foi atribuída a si.",
            link=f"/intervencoes/{instance.id}",
        )
        return resposta_sucesso(
            data={"id": str(instance.id), "tecnico_id": str(tecnico.id), "tecnico_nome": tecnico.nome}
        )

    @action(detail=True, methods=["post"], url_path="comentarios")
    def comentarios(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para comentar esta intervenção.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and instance.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para comentar esta intervenção.")
        serializer = AdicionarComentarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comentario = ComentarioIntervencao.objects.create(
            intervencao=instance,
            usuario=request.user,
            **serializer.validated_data,
        )
        utilizador_destino = instance.cliente if request.user.perfil == Usuario.PerfilChoices.TECNICO else instance.tecnico
        if utilizador_destino:
            Notificacao.objects.create(
                utilizador=utilizador_destino,
                tipo="comentario_adicionado",
                titulo="Novo comentário",
                mensagem=f"Foi adicionado um comentário na intervenção {instance.numero}.",
                link=f"/intervencoes/{instance.id}",
            )
        return resposta_sucesso(
            data={
                "id": str(comentario.id),
                "intervencao_id": str(instance.id),
                "usuario_nome": request.user.nome,
                "texto": comentario.texto,
                "data_criacao": comentario.data_criacao,
            },
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="anexos")
    def anexos(self, request, pk=None):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para anexar ficheiros.")
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and instance.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para anexar ficheiros.")
        serializer = CarregarAnexoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        anexo = AnexoIntervencao.objects.create(
            intervencao=instance,
            utilizador=request.user,
            arquivo=serializer.validated_data["ficheiro"],
            descricao=serializer.validated_data.get("descricao", ""),
        )
        return resposta_sucesso(
            data={
                "id": str(anexo.id),
                "nome_arquivo": anexo.arquivo.name.split("/")[-1],
                "url": request.build_absolute_uri(anexo.arquivo.url),
                "tamanho": anexo.tamanho,
                "data_upload": anexo.data_criacao,
            },
            status_code=status.HTTP_201_CREATED,
        )


class HoraTrabalhoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        request = cast(Request, self.request)
        queryset = HoraTrabalho.objects.select_related("intervencao", "tecnico")
        params = request.query_params
        if params.get("intervencao_id"):
            queryset = queryset.filter(intervencao_id=params["intervencao_id"])
        if params.get("tecnico_id"):
            queryset = queryset.filter(tecnico_id=params["tecnico_id"])
        if params.get("data_inicio"):
            queryset = queryset.filter(data_trabalho__gte=params["data_inicio"])
        if params.get("data_fim"):
            queryset = queryset.filter(data_trabalho__lte=params["data_fim"])
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            queryset = queryset.filter(tecnico=request.user)
        return queryset.order_by("-data_trabalho", "-data_criacao")

    def get_serializer_class(self):
        if self.action == "create":
            return HoraTrabalhoEscritaSerializer
        if self.action in {"update", "partial_update"}:
            return HoraTrabalhoAtualizacaoSerializer
        return HoraTrabalhoListaSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil not in {Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.TECNICO}:
            self.permission_denied(request, message="Sem permissão para registar horas.")
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(
            data={
                "id": str(obj.id),
                "intervencao_id": str(obj.intervencao_id),
                "tecnico_id": str(obj.tecnico_id),
                "horas": obj.horas,
                "data_trabalho": obj.data_trabalho,
            },
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and instance.tecnico_id != request.user.id:
            self.permission_denied(request, message="Só pode atualizar as próprias horas.")
        serializer = self.get_serializer(instance, data=request.data, partial=False, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "horas": obj.horas})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            if instance.tecnico_id != request.user.id:
                self.permission_denied(request, message="Só pode apagar as próprias horas.")
            if timezone.now() - instance.data_criacao > timedelta(hours=24):
                self.permission_denied(request, message="Só pode apagar registos nas primeiras 24 horas.")
        instance.delete()
        return resposta_sucesso(message="Registo de horas deletado com sucesso")
