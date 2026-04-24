from typing import cast

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.contratos.models import Contrato
from apps.contratos.serializers import (
    ContratoDetalheSerializer,
    ContratoEscritaSerializer,
    ContratoListaSerializer,
)


class ContratoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    ordering_fields = ("data_criacao", "data_inicio", "data_fim")
    filterset_fields = ("status", "tipo", "cliente")

    def get_queryset(self):
        request = cast(Request, self.request)
        queryset = Contrato.objects.select_related("cliente").all()
        cliente_id = request.query_params.get("cliente_id")
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            queryset = queryset.filter(cliente=request.user)
        return queryset.order_by("-data_criacao")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ContratoEscritaSerializer
        if self.action == "retrieve":
            return ContratoDetalheSerializer
        return ContratoListaSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and obj.cliente_id != request.user.id:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = self.get_serializer(obj)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem criar contratos.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(
            data={
                "id": str(obj.id),
                "cliente_id": str(obj.cliente_id),
                "tipo": obj.tipo,
                "status": obj.status,
            },
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atualizar contratos.")
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "status": obj.status})

    def destroy(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem deletar contratos.")
        instance = self.get_object()
        instance.delete()
        return resposta_sucesso(message="Contrato deletado com sucesso")
