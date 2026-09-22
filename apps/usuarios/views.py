
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.mail import BadHeaderError
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.conf import settings
from django.shortcuts import redirect
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework_simplejwt.exceptions import TokenError
from django.db.models import Sum
from smtplib import SMTPException
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import mixins, status, viewsets,serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import OpenApiExample, extend_schema
from apps.usuarios.models import Usuario, empresa
from apps.usuarios.serializers import (
    empresdatilserialazrs,
    AlterarSenhaSerializer,
    InicioSessaoSerializer,
    PerfilPainelSerializer,
    PerfilSerializer,
    UsuarioSerializer,
    RegistoSerializer,
    TecnicoDetalheSerializer,
    TecnicoEscritaSerializer,
    TecnicoListaSerializer,
    RecuperaSerializer,
    ResetSenhaSerializer,
    UtilizadorRegistadoSerializer,
    UtilizadorCriadoSerializer
)
from apps.configuracoes.responses import resposta_erro, resposta_sucesso
from apps.configuracoes.whatsapp import enviar_whatsapp
from apps.configuracoes.schema import (
    resposta_criar as esquema_criar,
    resposta_erro as esquema_erro,
    resposta_sucesso as esquema_resposta,
)
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
            return TokenRefreshSerializer

        if self.action == "reset_password":
            return AlterarSenhaSerializer

        
        return UsuarioSerializer
        

    @action(detail=False, methods=["get"], url_path="register", permission_classes=[IsAuthenticated])
    def lista(self, request, *args, **kwargs):
        queryset=Usuario.all_objects.all()  
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            
            return resposta_sucesso(data=paginated_data)

        serializer = self.get_serializer(queryset, many=True)
        return resposta_sucesso(data=serializer.data)

        
#_________________________________________________________________________________________________________________
    @action(detail=True, methods=["delete"], url_path="register", permission_classes=[IsAuthenticated])
    def delete_usuario(self, request, *args, **kwargs):

        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            raise PermissionDenied("Permissão Negada.")

        usuario = self.get_object()

        if usuario.is_deleted:
            return resposta_sucesso(message="Usuário já deletado")

        usuario.delete()

        return resposta_sucesso(message="Usuário deletado com sucesso")
#__________________________________________________________________________________________________________
    @extend_schema(
        summary="Registar utilizador (admin, técnico ou cliente)",
        description=(
            "Cria um utilizador. **Apenas administradores.** Aceita `multipart/form-data` para "
            "fazer upload da imagem do avatar (`avatar_url`); também pode ser enviada uma URL. "
            "Para `perfil=técnico` são obrigatórios `telefone`, `especialidades` e `data_contratacao`; "
            "para `perfil=cliente`, `telefone` e `empresa`."
        ),
        request={"multipart/form-data": RegistoSerializer, "application/json": RegistoSerializer},
        responses={
            201: esquema_criar(
                UtilizadorRegistadoSerializer,
                "Utilizador criado.",
                "UtilizadorRegistado",
                exemplos=[
                    OpenApiExample(
                        "Exemplo",
                        value={
                            "usuario_id": "uuid",
                            "email": "novo@sosticket.ao",
                            "perfil": "tecnico",
                            "avatar_url": "https://res.cloudinary.com/.../avatar.png",
                        },
                    )
                ],
            ),
            400: esquema_erro("Dados inválidos."),
            403: esquema_erro("Apenas administradores."),
        },
    )
    @action(detail=False, methods=["post"], url_path="register", permission_classes=[IsAuthenticated])
    def register(self, request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            raise PermissionDenied("Permissão Negada.")

        serializer = RegistoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        utilizador = serializer.save()
       
      
        data = {
            "usuario_id": str(utilizador.id),
            "email": utilizador.email,
            "perfil": utilizador.perfil,
            "avatar_url": utilizador.avatar_url,
        }
        return resposta_sucesso(data=data, status_code=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="login", authentication_classes=[], permission_classes=[])
    def login(self, request):
        serializer = InicioSessaoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return resposta_sucesso(data=InicioSessaoSerializer.construir_payload(serializer.validated_data["user"]))

    @action(detail=False, methods=["post"], url_path="logout", permission_classes=[IsAuthenticated])
    def logout(self, request):
        return resposta_sucesso(message="Logout realizado com sucesso")

    @action(detail=False, methods=["post"], url_path="refresh", authentication_classes=[])
    def refresh(self, request):
        try:
            serializer = TokenRefreshSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            return resposta_sucesso(
                data=serializer.validated_data
            )

        except TokenError as e:

            return resposta_erro(
                message=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        if not request.user.is_authenticated:
            raise PermissionDenied("Permissão negada.")
        serializer = AlterarSenhaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password_nova"])
        request.user.save(update_fields=["password"])
        def refresh(self, request):

            try:
                serializer = TokenRefreshSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)

                return Response(
                    {
                        "success": True,
                        "data": serializer.validated_data
                    },
                    status=status.HTTP_200_OK
                )

            except TokenError as e:

                return Response(
                    {
                        "success": False,
                        "message": str(e)
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
        return resposta_sucesso(message="Recuperado com sucesso")
    
   

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

    @extend_schema(
        summary="Atualizar o meu perfil",
        description=(
            "Atualiza o perfil do utilizador autenticado. Aceita `multipart/form-data` para fazer "
            "upload da imagem do avatar (`avatar_url`)."
        ),
        request={"multipart/form-data": PerfilSerializer, "application/json": PerfilSerializer},
        responses={
            200: esquema_resposta(PerfilSerializer, "Perfil atualizado.", "PerfilAtualizado"),
        },
    )
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
        if getattr(self, "swagger_fake_view", False):
            return Usuario.objects.none()
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

    @extend_schema(
        summary="Criar técnico",
        description=(
            "Cria um técnico. **Apenas administradores.** Aceita `multipart/form-data` para fazer "
            "upload da imagem do avatar (`avatar_url`)."
        ),
        request={"multipart/form-data": TecnicoEscritaSerializer, "application/json": TecnicoEscritaSerializer},
        responses={
            201: esquema_criar(
                UtilizadorCriadoSerializer,
                "Técnico criado.",
                "TecnicoCriado",
            ),
            400: esquema_erro("Dados inválidos."),
            403: esquema_erro("Apenas administradores podem criar técnicos."),
        },
    )
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

    @extend_schema(
        summary="Atualizar técnico",
        description=(
            "Atualiza um técnico. **Apenas administradores.** Aceita `multipart/form-data` "
            "para alterar a imagem do avatar (`avatar_url`)."
        ),
        request={"multipart/form-data": TecnicoEscritaSerializer, "application/json": TecnicoEscritaSerializer},
        responses={
            200: esquema_resposta(
                UtilizadorCriadoSerializer,
                "Técnico atualizado.",
                "TecnicoAtualizado",
            ),
            404: esquema_erro("Técnico não encontrado."),
            403: esquema_erro("Apenas administradores podem atualizar técnicos."),
        },
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



@extend_schema(tags=['Recuperação'])
class RecuperarConta(viewsets.GenericViewSet):
    

    permission_classes = []
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "recuperacao"
    queryset = Usuario.all_objects.all()
    serializer_class = RecuperaSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        utilizador = serializer.validated_data["user"]
        if not utilizador:
            return resposta_sucesso(
                message="Enviámos um email para recuperar a conta"
            )

        uid = urlsafe_base64_encode(force_bytes(utilizador.pk))
        token = default_token_generator.make_token(utilizador)

        link = (
            f"{settings.SITE_URL}"
            f"{reverse('restpassword-list')}?uid={uid}&token={token}"
        )
        enviar_whatsapp(numero=utilizador.telefone,texto=(
        f"Olá, {utilizador.nome}!\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta.\n"
        "Se foi você quem solicitou, clique no link abaixo para criar uma nova senha:\n\n"
        f"{link}\n\n"
        "Este link é válido por tempo limitado, por motivos de segurança.\n\n"
        "Se não foi você quem pediu esta alteração, pode ignorar este email —\n"
        "a sua senha atual continua a funcionar normalmente.\n\n"
        "—\n"
        "Equipa Gestão de Serviços"
    ))

        return resposta_sucesso(
            message="Enviámos um email para recuperar a conta"
        )
@extend_schema(tags=['Recuperação'])
class reset_password_confirm(viewsets.GenericViewSet):
    permission_classes=[]
    authentication_classes=[]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "recuperacao"
    queryset = Usuario.all_objects.all()
    serializer_class=ResetSenhaSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return resposta_sucesso(message="Senha resetada com sucesso")


@extend_schema(tags=['Empresa'])
class empresaviewset(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    queryset= empresa.all_objects.all()
    serializer_class= empresdatilserialazrs

    def list(self, request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return resposta_sucesso(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return resposta_sucesso(data=serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem criar empresas.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(
            data={"id": str(obj.id), "nome": obj.nome, "email": obj.Email_empresa},
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Apenas administradores podem atualizar empresas.")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return resposta_sucesso(data={"id": str(obj.id), "nome": obj.nome})
    

