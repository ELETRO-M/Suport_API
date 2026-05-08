from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from drf_spectacular.utils import extend_schema_field

from apps.usuarios.models import Usuario
from apps.contratos.models import Contrato
from apps.intervencoes.models import Intervencao


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "perfil",
            "telefone",
            "empresa",
            "nif",
            "endereco",
            "avatar_url",
            "preferencias",
            "especialidades",
            "data_contratacao",
            "status",
            "is_deleted",
            "data_criacao",
        )
        read_only_fields = ("id", "perfil", "data_criacao")


class RegistoSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Usuario
        fields = ("email", "password", "nome", "perfil", "telefone", "empresa")

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(password=password, **validated_data)


class InicioSessaoSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        utilizador = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if not utilizador:
            raise serializers.ValidationError("Credenciais inválidas.")
        if utilizador.status != Usuario.StatusChoices.ACTIVO:
            raise serializers.ValidationError("Esta conta está inactiva.")
        attrs["user"] = utilizador
        return attrs

    @staticmethod
    def construir_payload(utilizador):
        refresh = RefreshToken.for_user(utilizador)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "usuario": {
                "id": str(utilizador.id),
                "email": utilizador.email,
                "perfil": utilizador.perfil,
                "nome": utilizador.nome,
            },
        }


class RecuperaSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")

        try:
            utilizador = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Conta não existe.")

        attrs["user"] = utilizador
        return attrs

class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "perfil",
            "telefone",
            "avatar_url",
            "preferencias",
        )
        read_only_fields = ("id", "email", "perfil")


class ResetSenhaSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context["request"]

        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            raise serializers.ValidationError("Link inválido.")

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = Usuario.all_objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
            raise serializers.ValidationError("Link inválido.")

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError("Token inválido ou expirado.")

        from django.contrib.auth.password_validation import validate_password
        validate_password(attrs["new_password"], user)

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
class AlterarSenhaSerializer(serializers.Serializer):
    password_atual = serializers.CharField(write_only=True)
    password_nova = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs):
        utilizador = self.context["request"].user
        if not utilizador.check_password(attrs["password_atual"]):
            raise serializers.ValidationError({"password_atual": "Password atual inválida."})
        return attrs


class TecnicoListaSerializer(serializers.ModelSerializer):
    intervencoes_ativas = serializers.SerializerMethodField()
    total_horas_mes = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "telefone",
            "especialidades",
            "status",
            "intervencoes_ativas",
            "total_horas_mes",
        )
    @extend_schema_field(serializers.IntegerField())
    def get_intervencoes_ativas(self, obj):
        return Intervencao.objects.filter(
            tecnico=obj,
            status__in=["aberto", "em_andamento", "resolvido"],
        ).count()

    def get_total_horas_mes(self, obj):
        return getattr(obj, "total_horas_mes", 0) or 0


class TecnicoDetalheSerializer(TecnicoListaSerializer):
    historico_intervencoes = serializers.SerializerMethodField()

    class Meta(TecnicoListaSerializer.Meta):
        fields = TecnicoListaSerializer.Meta.fields + (
            "data_contratacao",
            "historico_intervencoes",
        )

    def get_historico_intervencoes(self, obj):
        return [
            {
                "id": str(item.id),
                "numero": item.numero,
                "titulo": item.titulo,
                "status": item.status,
            }
            for item in obj.intervencoes_atribuidas.order_by("-data_abertura")[:20]
        ]


class TecnicoEscritaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = (
            "nome",
            "email",
            "telefone",
            "password",
            "especialidades",
            "data_contratacao",
            "status",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(
            password=password,
            perfil=Usuario.PerfilChoices.TECNICO,
            **validated_data,
        )

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class PerfilPainelSerializer(serializers.ModelSerializer):
    from drf_spectacular.utils import extend_schema_field
    from rest_framework import serializers
    contratos_ativos = serializers.SerializerMethodField()
    intervencoes_abertas = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "perfil",
            "telefone",
            "avatar_url",
            "preferencias",
            "contratos_ativos",
            "intervencoes_abertas",
        )

    @extend_schema_field(serializers.IntegerField())
    def get_contratos_ativos(self, obj):
        if obj.perfil != Usuario.PerfilChoices.CLIENTE:
            return 0
        return Contrato.objects.filter(cliente=obj, status="ativo").count()
    
    @extend_schema_field(serializers.IntegerField())
    def get_intervencoes_abertas(self, obj):
        if obj.perfil == Usuario.PerfilChoices.CLIENTE:
            return Intervencao.objects.filter(cliente=obj, status__in=["aberto", "em_andamento"]).count()
        if obj.perfil == Usuario.PerfilChoices.TECNICO:
            return Intervencao.objects.filter(tecnico=obj, status__in=["aberto", "em_andamento"]).count()
        return Intervencao.objects.filter(status__in=["aberto", "em_andamento"]).count()