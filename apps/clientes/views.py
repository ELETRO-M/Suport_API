from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.clientes.serializers import (
    ClienteDetalheSerializer,
    ClienteEscritaSerializer,
    ClienteListaSerializer,
)
from drf_spectacular.utils import extend_schema
@extend_schema(tags=["Clientes"])
class ClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ("nome", "email", "empresa", "nif")
    ordering_fields = ("nome", "data_criacao")
    filterset_fields = ("status",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Usuario.objects.none()
            
        queryset = Usuario.objects.filter(perfil=Usuario.PerfilChoices.CLIENTE).order_by("nome")
        
        if self.request.user.is_authenticated and self.request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            queryset = queryset.filter(id=self.request.user.id)
            
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ClienteEscritaSerializer
        if self.action == "retrieve":
            return ClienteDetalheSerializer
        return ClienteListaSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.CLIENTE and obj.id != request.user.id:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = self.get_serializer(obj)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem criar clientes.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(
            data={"id": str(obj.id), "nome": obj.nome, "email": obj.email},
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atualizar clientes.")
            
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "nome": obj.nome, "email": obj.email})

    def destroy(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem deletar clientes.")
        instance = self.get_object()
        self.perform_destroy(instance)
        return resposta_sucesso(message="Cliente deletado com sucesso")
