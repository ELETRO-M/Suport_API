from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.usuarios.models import Usuario
from apps.contratos.models import Contrato
from apps.intervencoes.models import (
    AnexoIntervencao,
    ComentarioIntervencao,
    HistoricoEstadoIntervencao,
    HoraTrabalho,
    Intervencao,
)


class AnexoIntervencaoSerializer(serializers.ModelSerializer):
    nome_arquivo = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = AnexoIntervencao
        fields = ("id", "nome_arquivo", "url", "tamanho", "descricao", "data_criacao")

    @extend_schema_field(serializers.CharField())
    def get_nome_arquivo(self, obj):
        return obj.arquivo.name.split("/")[-1]

    @extend_schema_field(serializers.URLField())
    def get_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.arquivo.url)
        return obj.arquivo.url


class ComentarioIntervencaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome", read_only=True)
    data_criacao = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ComentarioIntervencao
        fields = ("id", "intervencao", "usuario_nome", "texto", "visivel_cliente", "data_criacao")
        read_only_fields = ("id", "intervencao", "usuario_nome", "data_criacao")


class HistoricoEstadoIntervencaoSerializer(serializers.ModelSerializer):
    alterado_por_nome = serializers.CharField(source="alterado_por.nome", read_only=True)

    class Meta:
        model = HistoricoEstadoIntervencao
        fields = ("id", "status", "alterado_por_nome", "nota", "data_criacao")


class IntervencaoListaSerializer(serializers.ModelSerializer):
    cliente_id = serializers.UUIDField(source="cliente.id", read_only=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    tecnico_id = serializers.UUIDField(source="tecnico.id", read_only=True)
    tecnico_nome = serializers.CharField(source="tecnico.nome", read_only=True)
    contrato_id = serializers.UUIDField(source="contrato.id", read_only=True)
    anexos = AnexoIntervencaoSerializer(many=True, read_only=True)

    class Meta:
        model = Intervencao
        fields = (
            "id",
            "numero",
            "titulo",
            "descricao",
            "cliente_id",
            "cliente_nome",
            "tecnico_id",
            "tecnico_nome",
            "contrato_id",
            "status",
            "prioridade",
            "horas_trabalhadas",
            "data_abertura",
            "data_conclusao",
            "anexos",
        )


class IntervencaoDetalheSerializer(IntervencaoListaSerializer):
    cliente = serializers.SerializerMethodField()
    tecnico = serializers.SerializerMethodField()
    contrato = serializers.SerializerMethodField()
    historico_status = HistoricoEstadoIntervencaoSerializer(many=True, read_only=True)
    comentarios = ComentarioIntervencaoSerializer(many=True, read_only=True)

    class Meta(IntervencaoListaSerializer.Meta):
        fields = IntervencaoListaSerializer.Meta.fields + (
            "cliente",
            "tecnico",
            "contrato",
            "historico_status",
            "comentarios",
        )

    @extend_schema_field(serializers.DictField())
    def get_cliente(self, obj):
        return {
            "id": str(obj.cliente.id),
            "nome": obj.cliente.nome,
            "empresa": obj.cliente.empresa,
        }

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_tecnico(self, obj):
        if not obj.tecnico:
            return None
        return {
            "id": str(obj.tecnico.id),
            "nome": obj.tecnico.nome,
        }

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_contrato(self, obj):
        if not obj.contrato:
            return None
        return {
            "id": str(obj.contrato.id),
            "tipo": obj.contrato.tipo,
        }


class IntervencaoEscritaSerializer(serializers.ModelSerializer):
    cliente_id = serializers.UUIDField(write_only=True)
    contrato_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    anexos = serializers.ListField(child=serializers.FileField(), required=False, write_only=True)

    class Meta:
        model = Intervencao
        fields = (
            "titulo",
            "descricao",
            "cliente_id",
            "contrato_id",
            "prioridade",
            "anexos",
        )

    def validate(self, attrs):
        try:
            attrs["cliente"] = Usuario.objects.get(id=attrs.pop("cliente_id"), perfil=Usuario.PerfilChoices.CLIENTE)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError({"cliente_id": "Cliente não encontrado."}) from exc

        contrato_id = attrs.pop("contrato_id", None)
        if contrato_id:
            try:
                attrs["contrato"] = Contrato.objects.get(id=contrato_id, cliente=attrs["cliente"])
            except Contrato.DoesNotExist as exc:
                raise serializers.ValidationError({"contrato_id": "Contrato não encontrado para este cliente."}) from exc
        return attrs

    def create(self, validated_data):
        anexos = validated_data.pop("anexos", [])
        intervencao = Intervencao.objects.create(**validated_data)
        for arquivo in anexos:
            AnexoIntervencao.objects.create(
                intervencao=intervencao,
                utilizador=self.context["request"].user,
                arquivo=arquivo,
            )
        HistoricoEstadoIntervencao.objects.create(
            intervencao=intervencao,
            status=intervencao.status,
            alterado_por=self.context["request"].user,
            nota="Intervenção criada.",
        )
        return intervencao


class IntervencaoAtualizacaoSerializer(serializers.ModelSerializer):
    tecnico_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Intervencao
        fields = ("titulo", "descricao", "tecnico_id", "status", "prioridade")

    def validate_tecnico_id(self, value):
        if value is None:
            return value
        try:
            return Usuario.objects.get(id=value, perfil=Usuario.PerfilChoices.TECNICO)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError("Técnico não encontrado.") from exc

    def update(self, instance, validated_data):
        tecnico = validated_data.pop("tecnico_id", None)
        previous_status = instance.status
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if tecnico is not None:
            instance.tecnico = tecnico
        instance.save()
        if previous_status != instance.status:
            HistoricoEstadoIntervencao.objects.create(
                intervencao=instance,
                status=instance.status,
                alterado_por=self.context["request"].user,
                nota="Status atualizado.",
            )
        return instance


class AtribuirTecnicoSerializer(serializers.Serializer):
    tecnico_id = serializers.UUIDField()

    def validate_tecnico_id(self, value):
        try:
            return Usuario.objects.get(id=value, perfil=Usuario.PerfilChoices.TECNICO)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError("Técnico não encontrado.") from exc


class AdicionarComentarioSerializer(serializers.Serializer):
    texto = serializers.CharField()
    visivel_cliente = serializers.BooleanField(default=True)


class CarregarAnexoSerializer(serializers.Serializer):
    ficheiro = serializers.FileField()
    descricao = serializers.CharField(required=False, allow_blank=True)


class HoraTrabalhoListaSerializer(serializers.ModelSerializer):
    intervencao = serializers.SerializerMethodField()
    tecnico = serializers.SerializerMethodField()

    class Meta:
        model = HoraTrabalho
        fields = (
            "id",
            "intervencao",
            "tecnico",
            "horas",
            "data_trabalho",
            "descricao",
            "tipo",
        )

    @extend_schema_field(serializers.DictField())
    def get_intervencao(self, obj):
        return {
            "id": str(obj.intervencao.id),
            "numero": obj.intervencao.numero,
            "titulo": obj.intervencao.titulo,
        }

    @extend_schema_field(serializers.DictField())
    def get_tecnico(self, obj):
        return {
            "id": str(obj.tecnico.id),
            "nome": obj.tecnico.nome,
        }


class HoraTrabalhoEscritaSerializer(serializers.ModelSerializer):
    intervencao_id = serializers.UUIDField(write_only=True)
    tecnico_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = HoraTrabalho
        fields = ("intervencao_id", "tecnico_id", "horas", "data_trabalho", "descricao", "tipo")

    def validate(self, attrs):
        request = self.context["request"]
        try:
            attrs["intervencao"] = Intervencao.objects.get(id=attrs.pop("intervencao_id"))
        except Intervencao.DoesNotExist as exc:
            raise serializers.ValidationError({"intervencao_id": "Intervenção não encontrada."}) from exc

        tecnico_id = attrs.pop("tecnico_id", None)
        if request.user.perfil == Usuario.PerfilChoices.TECNICO:
            attrs["tecnico"] = request.user
        elif tecnico_id:
            try:
                attrs["tecnico"] = Usuario.objects.get(id=tecnico_id, perfil=Usuario.PerfilChoices.TECNICO)
            except Usuario.DoesNotExist as exc:
                raise serializers.ValidationError({"tecnico_id": "Técnico não encontrado."}) from exc
        else:
            raise serializers.ValidationError({"tecnico_id": "Este campo é obrigatório para admin."})
        return attrs


class HoraTrabalhoAtualizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoraTrabalho
        fields = ("horas", "descricao")
