from rest_framework import serializers
from apps.usuarios.models import Usuario, empresa as Empresa
from apps.contratos.models import Contrato
from drf_spectacular.utils import extend_schema_field


class ContratoListaSerializer(serializers.ModelSerializer):
    empresa = serializers.CharField(source="Empresa.nome", read_only=True)
    empresa_id = serializers.UUIDField(source="Empresa.id", read_only=True)
    expiracao = serializers.IntegerField(read_only=True)
    horas_disponiveis = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


    class Meta:
        model = Contrato
        fields = (
            "id",
            "empresa_id",
            "empresa",
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
            "descricao_contrato",
            "observacoes",
        )


class ContratoDetalheSerializer(ContratoListaSerializer):
    empresa_detalhe = serializers.SerializerMethodField()
    intervencoes = serializers.SerializerMethodField()

    class Meta(ContratoListaSerializer.Meta):
        fields = ContratoListaSerializer.Meta.fields + ("empresa_detalhe", "valor_hora", "intervencoes")

    @extend_schema_field(serializers.DictField())
    def get_empresa_detalhe(self, obj):
        return {
            "id": str(obj.Empresa.id),
            "nome": obj.Empresa.nome,
            "email": obj.Empresa.Email_empresa,
            "nif": obj.Empresa.nif,
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
    empresa_id = serializers.PrimaryKeyRelatedField(
        source="Empresa",
        queryset=Empresa.objects.filter(is_deleted=False),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Contrato
        fields = (
            "empresa_id",
            "tipo_de_pagamento",
            "tipo_contrato",
            "descricao_contrato",
            "horas_contratadas",
            "valor_hora",
            "valor_total",
            "data_inicio",
            "data_fim",
            "status",
            "observacoes",
        )

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        if user.perfil == Usuario.PerfilChoices.CLIENTE:
            validated_data["Empresa"] = user.empresa
        elif user.perfil == Usuario.PerfilChoices.ADMIN and not validated_data.get("Empresa"):
            raise serializers.ValidationError({"empresa_id": "Este campo é obrigatório para administradores."})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            validated_data.pop("Empresa", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
