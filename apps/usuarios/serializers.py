from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.encoding import force_str
from apps.notificacoes.models import Notificacao
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from drf_spectacular.utils import extend_schema_field
from django.db.models import Sum
from apps.usuarios.models import Usuario, empresa
from apps.contratos.models import Contrato
from apps.intervencoes.models import Intervencao
class notifySerialazrs(serializers.ModelSerializer):
    class Meta:
        model=Notificacao
        fields=(
            "id",
            "tipo",
            "titulo",
        )
class empresdatilserialazrs(serializers.ModelSerializer):
    class Meta():
        model=empresa
        fields=(
            "id",
            "nome",
            "Email_empresa",
            "nif",
            "endereco",
            "telefone",
            "status",
            "postos",
            "data_criacao",
            "data_actualizacao"
        )
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = empresa
        fields = (
            "nome",
            "Email_empresa",
            "telefone",
            "endereco",
            "nif",
            "postos"
          
        )
        read_only_fields = ("id", "perfil", "data_criacao")

class UsuarioSerializer(serializers.ModelSerializer):
    empresa = EmpresaSerializer(read_only=True)
    notificacao = notifySerialazrs(source="notificacoes", many=True, read_only=True)
    
    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "perfil",
            "telefone",
            "empresa",
            "ip_servidor",
            "avatar_url",
            "preferencias",
            "especialidades",
            "data_contratacao",
            "notificacao",
            "status",
            "is_deleted",
            "data_criacao",
        )
        read_only_fields = ("id", "perfil", "data_criacao")


class RegistoSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    empresa=EmpresaSerializer(read_only=True)
    class Meta:
        model = Usuario
        fields = (
            "email",
            "password",
            "nome",
            "perfil",
            "empresa",
            "telefone",
            "especialidades",
            "data_contratacao",
            "status",
        )
        extra_kwargs = {
            "telefone": {"required": False},
            "empresa": {"required": False},
            "ip_servidor": {"required": False},
            "especialidades": {"required": False},
            "data_contratacao": {"required": False},
            "status": {"required": False},
        }

    def validate(self, attrs):
        perfil = attrs.get("perfil")

        if perfil == Usuario.PerfilChoices.CLIENTE:
            required_fields = ("telefone", "empresa", "ip_servidor")
        elif perfil == Usuario.PerfilChoices.TECNICO:
            required_fields = ("telefone",  "especialidades", "data_contratacao")
        else:
            required_fields = ()

        errors = {}
        for field in required_fields:
            value = attrs.get(field)
            if value in (None, "", [], {}):
                errors[field] = "Este campo é obrigatório para este perfil."

        if errors:
            raise serializers.ValidationError(errors)

        if perfil != Usuario.PerfilChoices.CLIENTE and attrs.get("empresa"):
            raise serializers.ValidationError({
                "empresa": "Apenas clientes podem estar associados a uma empresa."
            })

        return attrs

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

        utilizador = Usuario.all_objects.filter(email=email).first()

        attrs["user"] = utilizador
        return attrs


class PerfilSerializer(serializers.ModelSerializer):
    empresa=EmpresaSerializer(read_only=True)
    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "perfil",
            "ip_servidor",
            "telefone",
            "avatar_url",
            "preferencias",
            "empresa"
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

        validate_password(attrs["new_password"], user)

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.recuperar()
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
    notificacao = notifySerialazrs(source="notificacoes", many=True, read_only=True)

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
            "notificacao",

        )
    @extend_schema_field(serializers.IntegerField())
    def get_intervencoes_ativas(self, obj):
        return Intervencao.objects.filter(
            tecnico=obj,
            status__in=["aberto", "em_andamento", "resolvido"],
        ).count()

    @extend_schema_field(serializers.IntegerField())
    def get_total_horas_mes(self, obj):
        return Intervencao.objects.filter(
            tecnico=obj
        ).aggregate(
            total=Sum("horas_trabalhadas")
        )["total"] or 0


class TecnicoDetalheSerializer(TecnicoListaSerializer):
    historico_intervencoes = serializers.SerializerMethodField()

    class Meta(TecnicoListaSerializer.Meta):
        fields = TecnicoListaSerializer.Meta.fields + (
            "data_contratacao",
            "historico_intervencoes",
        )

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
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
        password = validated_data.pop("password", "123456")
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
