from rest_framework import serializers
from django.db import IntegrityError
from apps.usuarios.models import Usuario, empresa as Empresa
from apps.contratos.models import Contrato
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from apps.notificacoes.models import Notificacao

class notifySerialazrs(serializers.ModelSerializer):
    class Meta:
        model=Notificacao
        fields=(
            "id",
            "tipo",
            "titulo",
        )
class ClienteEmpresaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Empresa
        fields = (
            "id",
            "Email_empresa",
            "nome",
            "nif",
            "endereco",
            "postos",
            "telefone",
            "avatar_url",
            "status",
            "is_deleted",
            "data_criacao",
            "data_actualizacao",
            
            
        )


class ClienteListaSerializer(serializers.ModelSerializer):
    contratos_ativos = serializers.SerializerMethodField()
    empresa = ClienteEmpresaSerializer(read_only=True)
    

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
            "status",
            "data_criacao",
            "contratos_ativos",
            
        )

    @extend_schema_field(serializers.IntegerField())
    def get_contratos_ativos(self, obj):
        return Contrato.objects.filter(
            cliente=obj,
            is_deleted=False,
            status=Contrato.StatusChoices.ACTIVO
        ).count()
    
   


class ClienteDetalheSerializer(ClienteListaSerializer):
    contratos = serializers.SerializerMethodField()
    intervencoes = serializers.SerializerMethodField()

    class Meta(ClienteListaSerializer.Meta):
        fields = ClienteListaSerializer.Meta.fields + ("contratos", "intervencoes")

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_contratos(self, obj):
        return [
            {
                "id": str(item.id),
                "tipo": item.tipo_contrato,
                "status": item.status,
                "horas_disponiveis": item.horas_disponiveis,
            }
            for item in obj.contratos.alive().order_by("-data_criacao")[:20]
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_intervencoes(self, obj):
        return [
            {
                "id": str(item.id),
                "numero": item.numero,
                "titulo": item.titulo,
                "status": item.status,
            }
            for item in obj.intervencoes.order_by("-data_abertura")[:20]
        ]


class ClienteEscritaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = (
            "nome",
            "email",
            "telefone",
            "empresa",
            "ip_servidor",
            "password",
            "status",
        )

    def create(self, validated_data):
        try:
            password = validated_data.pop("password")
            return Usuario.objects.create_user(
                password=password,
                perfil=Usuario.PerfilChoices.CLIENTE,
                **validated_data,
            )
        except IntegrityError:
            raise serializers.ValidationError({
                "email": f"Este email já foi registado. Tente recuperar a conta em: {settings.SITE_URL}/api/v1/recuperar"
            })
       

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value
