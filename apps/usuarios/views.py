from datetime import timedelta
from typing import Type

from django.db.models import Sum
from django.utils import timezone
from rest_framework import mixins, status, viewsets,serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import extend_schema
from apps.usuarios.models import Usuario
from apps.usuarios.serializers import (
    AlterarSenhaSerializer,
    InicioSessaoSerializer,
    PerfilPainelSerializer,
    UsuarioSerializer,
    RegistoSerializer,
    TecnicoDetalheSerializer,
    TecnicoEscritaSerializer,
    TecnicoListaSerializer,
)
from apps.configuracoes.responses import resposta_sucesso
@extend_schema(tags=["Autenticação"])
class AutenticacaoViewSet(viewsets.GenericViewSet):
    queryset = Usuario.objects.all()

    def get_permissions(self):
        if self.action in {"register", "login", "refresh", "reset_password"}:
            return []
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "lista":
            return UsuarioSerializer
        if self.action == "register":
            return RegistoSerializer
        if self.action == "login":
            return InicioSessaoSerializer
        if self.action == "refresh":
            from rest_framework_simplejwt.serializers import TokenRefreshSerializer
            return TokenRefreshSerializer
        if self.action == "lista":
            return UsuarioSerializer
        from rest_framework import serializers
        return serializers.Serializer
    @action(detail=False, methods=["get","put"], url_path="register/",permission_classes=[IsAuthenticated])
    def lista(self, request, *args, **kwargs):
        queryset=Usuario.all_objects.all()
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        if request.method == "PUT":
            
            return self.update(request, *args, **kwargs)
        
        if request.method=="GET":
            queryset = self.filter_queryset(queryset)
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_data = self.get_paginated_response(serializer.data).data
                
                return resposta_sucesso(data=paginated_data)

            serializer = self.get_serializer(queryset, many=True)
            return resposta_sucesso(data=serializer.data)

        
#_________________________________________________________________________________________________________________
    @action(detail=True, methods=["delete"], url_path="register")
    def delete_usuario(self, request, *args, **kwargs):

        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            raise PermissionDenied("Permissão Negada.")

        usuario = self.get_object()

        if usuario.is_deleted:
            return resposta_sucesso(message="Usuário já deletado")

        usuario.delete()

        return resposta_sucesso(message="Usuário deletado com sucesso")
#__________________________________________________________________________________________________________
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        if request.user.perfil == Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = RegistoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilizador = serializer.save()
        data = {
            "usuario_id": str(utilizador.id),
            "email": utilizador.email,
            "perfil": utilizador.perfil,
        }
        return resposta_sucesso(data=data, status_code=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = InicioSessaoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return resposta_sucesso(data=InicioSessaoSerializer.construir_payload(serializer.validated_data["user"]))

    @action(detail=False, methods=["post"], url_path="logout", permission_classes=[IsAuthenticated])
    def logout(self, request):
        return resposta_sucesso(message="Logout realizado com sucesso")

    @action(detail=False, methods=["post"], url_path="refresh", authentication_classes=[])
    def refresh(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return resposta_sucesso(data=serializer.validated_data)

    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        serializer = RedefinirSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return resposta_sucesso(message="Email de recuperação enviado")

@extend_schema(tags=["Perfis"])
class PerfilViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.all()

    def get_serializer_class (self) ->type[serializers.Serializer]:
        if self.action == "password":
            return AlterarSenhaSerializer
        if self.action == "list":
            return PerfilPainelSerializer
        return PerfilSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return resposta_sucesso(data=serializer.data)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return resposta_sucesso(data=serializer.data)

    @action(detail=False, methods=["put"], url_path="password")
    def password(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password_nova"])
        request.user.save(update_fields=["password"])
        return resposta_sucesso(message="Password alterada com sucesso")

@extend_schema(tags=["Tecnicos"])
class TecnicoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ("nome", "email", "especialidades")
    ordering_fields = ("nome", "data_criacao")
    filterset_fields = ("status",)

    def get_queryset(self):
        queryset = (
            Usuario.objects.filter(perfil=Usuario.PerfilChoices.TECNICO)
            .annotate(total_horas_mes=Sum("horas_registadas__horas"))
            .order_by("nome")
        )
        if self.request.user.perfil == Usuario.PerfilChoices.TECNICO:
            return queryset.filter(id=self.request.user.id)
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return TecnicoEscritaSerializer
        if self.action == "retrieve":
            return TecnicoDetalheSerializer
        return TecnicoListaSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.perfil == Usuario.PerfilChoices.TECNICO and obj.id != request.user.id:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = self.get_serializer(obj)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem criar técnicos.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(
            data={"id": str(obj.id), "nome": obj.nome, "email": obj.email},
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atualizar técnicos.")
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "nome": obj.nome})

    def destroy(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem remover técnicos.")
        instance = self.get_object()
        self.perform_destroy(instance)
        return resposta_sucesso(message="Técnico deletado com sucesso")
