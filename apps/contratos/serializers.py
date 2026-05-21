from rest_framework import serializers
from apps.usuarios.models import Usuario
from apps.contratos.models import Contrato
from drf_spectacular.utils import extend_schema_field


class ContratoListaSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    cliente_id = serializers.UUIDField(source="cliente.id", read_only=True)
    cliente_empresa = serializers.CharField(source="cliente.empresa.nome", read_only=True, allow_null=True, default=None)
    horas_disponiveis = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    


    class Meta:
        model = Contrato
        fields = (
            "id",
            "cliente_id",
            "cliente_nome",
            "cliente_empresa",
            "expiracao",
            "tipo_contrato",
            "tipo_de_pagamento",
            "horas_contratadas",
            "horas_utilizadas",
            "horas_disponiveis",
            "valor_total",
            "valor_hora",
            "data_inicio",
            "data_fim",
            "status",
            "observacoes",
        )


class ContratoDetalheSerializer(ContratoListaSerializer):
    cliente = serializers.SerializerMethodField()
    intervencoes = serializers.SerializerMethodField()

    class Meta(ContratoListaSerializer.Meta):
        fields = ContratoListaSerializer.Meta.fields + ("cliente", "valor_hora", "intervencoes")

    @extend_schema_field(serializers.DictField())
    def get_cliente(self, obj):
        return {
            "id": str(obj.cliente.id),
            "nome": obj.cliente.nome,
            "empresa": obj.cliente.empresa.nome if obj.cliente.empresa else None,
        }

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


class ContratoEscritaSerializer(serializers.ModelSerializer):
    cliente_id = serializers.UUIDField(write_only=True)
    cliente_empresa = serializers.CharField(source="cliente.empresa.nome", read_only=True, allow_null=True, default=None)

    class Meta:
        model = Contrato
        fields = (
            "cliente_id",
            "cliente_empresa",
            "tipo_contrato",
            "tipo_de_pagamento",
            "horas_contratadas",
            "horas_utilizadas",
            "valor_total",
            "data_inicio",
            "data_fim",
            "status",
            "observacoes",
        )

    def validate(self, attrs):
        

        try:
            attrs["cliente"] = Usuario.objects.get(id=attrs.pop("cliente_id"), perfil=Usuario.PerfilChoices.CLIENTE)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError({"cliente_id": "Cliente não encontrado."}) from exc
        return attrs

    def create(self, validated_data):
        return Contrato.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("cliente", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
