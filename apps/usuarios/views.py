
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.db.models import Sum
from django.utils import timezone
from rest_framework.response import Response
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
    RecuperaSerializer,
    ResetSenhaSerializer
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

            return TokenRefreshSerializer
        if self.action == "lista":
            return UsuarioSerializer
        if self.action =='reset-password':
         return AlterarSenhaSerializer
    @action(detail=False, methods=["get"], url_path="register",permission_classes=[IsAuthenticated])
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
    @action(detail=False, methods=["post"], url_path="register/",permission_classes=[IsAuthenticated])
    def register(self, request):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            raise PermissionDenied("Permissão Negada.")

        serializer = RegistoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utilizador = serializer.save()
        run=send_mail(
            subject=f"Seja bem-vindo ao API de Gestão de Serviços.",
            message=(f"Olá,{utilizador.nome} \nSeja bem-vindo(a) ao nosso sistema!\n\n"
            "O seu cadastro foi realizado com sucesso e já pode começar a utilizar todas as funcionalidades disponíveis.\n"
            "Aqui estão alguns dados importantes:\n\n"
            "1- Utilize o seu email e senha para acessar a plataforma\n"
            "2- Mantenha os seus dados sempre atualizados\n"
            "3- Em caso de dúvidas, entre em contacto com o nosso suporte Estamos felizes por tê-lo(a) connosco e esperamos que tenha uma excelente experiência.\n\n"
            "Atenciosamente,"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[utilizador.email],
        )
        if not run:
            utilizador.delete()
            raise serializers.ValidationError({"email": "Email de confirmação não enviado."})
      
        data = {
            "usuario_id": str(utilizador.id),
            "email": utilizador.email,
            "perfil": utilizador.perfil,
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
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return resposta_sucesso(data=serializer.validated_data)

    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        if request.user.uid != self.get_object().uid:
            raise PermissionDenied("Permissão negada.")
        serializer = RedefinirSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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



@extend_schema(tags=['Recuperação'])
class RecuperarConta(viewsets.GenericViewSet):

    permission_classes=[]
    authentication_classes=[]
    queryset = Usuario.all_objects.all()
    serializer_class=RecuperaSerializer


    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        utilizador = serializer.validated_data["user"]
        if not utilizador:
            return resposta_erro("Utilizador não encontrado", status_code=status.HTTP_404_NOT_FOUND)
        
        uid = urlsafe_base64_encode(force_bytes(utilizador.pk))
        token=default_token_generator.make_token(utilizador)

    

        link = f"{settings.SITE_URL}{reverse('restpassword-list')}?uid={uid}"

        send_mail(
            subject="Recuperação de Senha - API Gestão de Serviços",
            message=(
                f"Olá, {utilizador.nome}\n\n"
                "Recebemos um pedido para redefinir a senha da sua conta.\n"
                "Para redefinir a sua senha, clique no link abaixo:\n"
                f"Token: {token}\n"
                f"Link: {link}\n"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[utilizador.email], 
        )

        utilizador.recuperar()
        utilizador.save()


        return Response(
            {"detail": "Enviámos um email para recuperar a conta"},
            status=status.HTTP_200_OK
        )
@extend_schema(tags=['Recuperação'])
class reset_password_confirm(viewsets.GenericViewSet):
    permission_classes=[]
    authentication_classes=[]
    queryset = Usuario.all_objects.all()
    serializer_class=ResetSenhaSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return resposta_sucesso(message="Senha resetada com sucesso")