from typing import Type, cast
from django.db.models import QuerySet

from rest_framework import status, viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.contratos.models import Contrato
from apps.contratos.serializers import (
    ContratoDetalheSerializer,
    ContratoEscritaSerializer,
    ContratoListaSerializer,
)

@extend_schema(tags=["Contratos"])
class ContratoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    ordering_fields = ("data_criacao", "data_inicio", "data_fim")
    filterset_fields = ("status", "tipo_contrato", "tipo_de_pagamento", "cliente")

    
    serializer_action_classes: dict[str, Type[serializers.Serializer]] = {
        "list": ContratoListaSerializer,
        "retrieve": ContratoDetalheSerializer,
        "create": ContratoEscritaSerializer,
        "update": ContratoEscritaSerializer,
        "partial_update": ContratoEscritaSerializer,
    }

    
    def get_queryset(self) -> QuerySet:
        if getattr(self, "swagger_fake_view", False):
            return Contrato.objects.none()

        request = cast(Request, self.request)

        queryset = Contrato.objects.select_related("cliente", "cliente__empresa")

        cliente_id = request.query_params.get("cliente_id")
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)

        if request.user.is_authenticated and request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            queryset = queryset.filter(cliente=request.user)

        return queryset.order_by("-data_criacao")


    def get_serializer_class(self) -> Type[serializers.Serializer]:
        return self.serializer_action_classes.get(
            self.action,
            ContratoListaSerializer
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and obj.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão.")

        serializer = self.get_serializer(obj)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN or Usuario.PerfilChoices.CLIENTE:
            self.permission_denied(request, message="Permissão negada para este recurso.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        return resposta_sucesso(
            data={
                "id": str(obj.id),
                "cliente_id": str(obj.cliente_id),
                "tipo_contrato": obj.tipo_contrato,
                "tipo_de_pagamento": obj.tipo_de_pagamento,
                "status": obj.status,
            },
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if request.user.perfil != Usuario.PerfilChoices.ADMIN and (
            request.user.perfil != Usuario.PerfilChoices.CLIENTE or instance.cliente_id != request.user.id
        ):
            self.permission_denied(request, message="Permissão negada para este recurso.")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        return resposta_sucesso(
            data={"id": str(obj.id), "status": obj.status}
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil != Usuario.PerfilChoices.ADMIN and (
            request.user.perfil != Usuario.PerfilChoices.CLIENTE or instance.cliente_id != request.user.id
        ):
            self.permission_denied(request, message="Permissão negada para este recurso.")

        instance.delete()

        return resposta_sucesso(message="Contrato deletado com sucesso")
