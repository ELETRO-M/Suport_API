from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.usuarios.models import Usuario
from apps.usuarios.serializers import UtilizadorCriadoSerializer
from apps.configuracoes.responses import resposta_sucesso
from apps.configuracoes.schema import (
    resposta_criar as esquema_criar,
    resposta_erro as esquema_erro,
    resposta_sucesso as esquema_resposta,
)
from apps.clientes.serializers import (
    ClienteDetalheSerializer,
    ClienteEscritaSerializer,
    ClienteListaSerializer,
)
from drf_spectacular.utils import extend_schema
@extend_schema(tags=["Clientes"])
class ClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ("nome", "email", "empresa__nome", "nif")
    ordering_fields = ("nome", "data_criacao")
    filterset_fields = ("status",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Usuario.objects.none()
            
        queryset = Usuario.objects.select_related("empresa").filter(
            perfil=Usuario.PerfilChoices.CLIENTE
        ).order_by("nome")
        
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

    @extend_schema(
        summary="Criar cliente",
        description=(
            "Cria um cliente. **Apenas administradores.** Aceita `multipart/form-data` para fazer "
            "upload da imagem do avatar (`avatar_url`)."
        ),
        request={"multipart/form-data": ClienteEscritaSerializer, "application/json": ClienteEscritaSerializer},
        responses={
            201: esquema_criar(
                UtilizadorCriadoSerializer,
                "Cliente criado.",
                "ClienteCriado",
            ),
            400: esquema_erro("Dados inválidos."),
            403: esquema_erro("Apenas administradores podem criar clientes."),
        },
    )
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

    @extend_schema(
        summary="Atualizar cliente",
        description=(
            "Atualiza um cliente. O **admin** pode atualizar qualquer cliente; o **cliente** apenas a "
            "própria conta. Aceita `multipart/form-data` para alterar a imagem do avatar (`avatar_url`)."
        ),
        request={"multipart/form-data": ClienteEscritaSerializer, "application/json": ClienteEscritaSerializer},
        responses={
            200: esquema_resposta(
                UtilizadorCriadoSerializer,
                "Cliente atualizado.",
                "ClienteAtualizado",
            ),
            403: esquema_erro("Alteração de perfil não permitida."),
        },
    )
    def update(self, request, *args, **kwargs):
        
        if request.user.perfil != Usuario.PerfilChoices.ADMIN and (
            request.user.perfil != Usuario.PerfilChoices.CLIENTE or instance.id != request.user.id
        ):
            self.permission_denied(request, message="Alteração de perfil não permitida.")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "nome": obj.nome, "email": obj.email})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.perfil != Usuario.PerfilChoices.ADMIN and (
            request.user.perfil != Usuario.PerfilChoices.CLIENTE or instance.id != request.user.id
        ):
            self.permission_denied(request, message="Delete de perfil não permitido.")
        self.perform_destroy(instance)
        return resposta_sucesso(message="Cliente deletado com sucesso")
