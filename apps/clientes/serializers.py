from rest_framework import serializers

from apps.usuarios.models import Usuario
from apps.contratos.models import Contrato


class ClienteListaSerializer(serializers.ModelSerializer):
    contratos_ativos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            "id",
            "nome",
            "email",
            "telefone",
            "empresa",
            "nif",
            "endereco",
            "status",
            "data_criacao",
            "contratos_ativos",
        )

    def get_contratos_ativos(self, obj):
        return obj.contratos.alive().filter(status=Contrato.StatusChoices.ACTIVO).count()


class ClienteDetalheSerializer(ClienteListaSerializer):
    contratos = serializers.SerializerMethodField()
    intervencoes = serializers.SerializerMethodField()

    class Meta(ClienteListaSerializer.Meta):
        fields = ClienteListaSerializer.Meta.fields + ("contratos", "intervencoes")

    def get_contratos(self, obj):
        return [
            {
                "id": str(item.id),
                "tipo": item.tipo,
                "status": item.status,
                "horas_disponiveis": item.horas_disponiveis,
            }
            for item in obj.contratos.alive().order_by("-data_criacao")[:20]
        ]

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
            "nif",
            "endereco",
            "password",
            "status",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(
            password=password,
            perfil=Usuario.PerfilChoices.CLIENTE,
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
