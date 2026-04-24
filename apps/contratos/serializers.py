from rest_framework import serializers

from apps.contratos.models import Contrato


class ContratoListaSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    cliente_id = serializers.UUIDField(source="cliente.id", read_only=True)
    horas_disponiveis = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Contrato
        fields = (
            "id",
            "cliente_id",
            "cliente_nome",
            "tipo",
            "horas_contratadas",
            "horas_utilizadas",
            "horas_disponiveis",
            "valor_total",
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

    def get_cliente(self, obj):
        return {
            "id": str(obj.cliente.id),
            "nome": obj.cliente.nome,
            "empresa": obj.cliente.empresa,
        }

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

    class Meta:
        model = Contrato
        fields = (
            "cliente_id",
            "tipo",
            "horas_contratadas",
            "valor_total",
            "data_inicio",
            "data_fim",
            "status",
            "observacoes",
        )

    def validate(self, attrs):
        from apps.usuarios.models import Usuario

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
