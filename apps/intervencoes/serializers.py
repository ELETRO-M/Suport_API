from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.notificacoes.models import Notificacao
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
    comentario=ComentarioIntervencaoSerializer(many=True, read_only=True)
    sla= serializers.SerializerMethodField()

    class Meta:
        model = Intervencao
        fields = (
            "id",
            "numero",
            "titulo",
            "actuacao_tipo",
            "descricao",
            "cliente_id",
            "cliente_nome",
            "tecnico_id",
            "tecnico_nome",
            "contrato_id",
            "status",
            "estado",
            "sla",
            "prioridade",
            "horas_trabalhadas",
            "data_inicio_intervencao",
            "data_fim_intervencao",
            "data_abertura",
            "data_conclusao",
            "anexos",
            "comentario"
        )
    @extend_schema_field(serializers.DictField())
    def get_sla(self, obj):
        return obj.sla


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
            "empresa": obj.cliente.empresa.nome if obj.cliente.empresa else None,
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
            "tipo": obj.contrato.tipo_contrato,
        }


class IntervencaoEscritaSerializer(serializers.ModelSerializer):
    cliente_id = serializers.UUIDField(write_only=True, required=False)
    contrato_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    anexos = serializers.FileField(required=False, write_only=True)

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
        request = self.context.get("request")
        cliente_id = attrs.pop("cliente_id", None)

        if request and request.user.perfil == Usuario.PerfilChoices.CLIENTE:
            attrs["cliente"] = request.user
        else:
            if not cliente_id:
                raise serializers.ValidationError({"cliente_id": "Este campo Ã© obrigatÃ³rio para administradores."})
            try:
                attrs["cliente"] = Usuario.objects.get(id=cliente_id, perfil=Usuario.PerfilChoices.CLIENTE)
            except Usuario.DoesNotExist as exc:
                raise serializers.ValidationError({"cliente_id": "Cliente nÃ£o encontrado."}) from exc

        contrato_id = attrs.pop("contrato_id", None)
        empresa_id = attrs["cliente"].empresa_id
        if not empresa_id:
            raise serializers.ValidationError({"cliente_id": "Cliente sem empresa associada."})

        if contrato_id:
            try:
                attrs["contrato"] = Contrato.objects.get(
                    id=contrato_id,
                    Empresa_id=empresa_id,
                    status=Contrato.StatusChoices.ACTIVO,
                    is_deleted=False,
                )
            except Contrato.DoesNotExist as exc:
                raise serializers.ValidationError({"contrato_id": "Contrato activo não encontrado para a empresa deste cliente."}) from exc
        else:
            contratos_ativos = Contrato.objects.filter(
                Empresa_id=empresa_id,
                status=Contrato.StatusChoices.ACTIVO,
                is_deleted=False,
            ).order_by("data_fim", "data_criacao")
            attrs["contrato"] = next(
                (contrato for contrato in contratos_ativos if contrato.horas_disponiveis > 0),
                contratos_ativos.first(),
            )
        return attrs

    def create(self, validated_data):
        # Remove the single dummy file from validated_data
        validated_data.pop("anexos", None)
        intervencao = Intervencao.objects.create(**validated_data)
        
        # Get all uploaded files from the raw request (supports multiple files!)
        request = self.context.get("request")
        if request and request.FILES:
            ficheiros = request.FILES.getlist("anexos")
            for arquivo in ficheiros:
                AnexoIntervencao.objects.create(
                    intervencao=intervencao,
                    utilizador=request.user,
                    arquivo=arquivo,
                )
          
        HistoricoEstadoIntervencao.objects.create(
            intervencao=intervencao,
            status=intervencao.status,
            alterado_por=self.context["request"].user,
            nota="IntervenÃ§Ã£o criada.",
        )
        return intervencao


class IntervencaoAtualizacaoSerializer(serializers.ModelSerializer):
    STATUS_FLOW = (
        Intervencao.StatusChoices.ABERTO,
        Intervencao.StatusChoices.EM_ANDAMENTO,
        Intervencao.StatusChoices.CONCLUIDO,
        Intervencao.StatusChoices.FECHADO,
    )

    tecnico_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Intervencao
        fields = (
            "titulo",
            "actuacao_tipo",
            "descricao", 
            "tecnico_id", 
            "status", 
            "prioridade",
            "data_inicio_intervencao",
            "data_fim_intervencao",
            "horas_trabalhadas",

            )

    def validate_tecnico_id(self, value):
        if value is None:
            return value
        try:
            return Usuario.objects.get(id=value, perfil=Usuario.PerfilChoices.TECNICO)
        except Usuario.DoesNotExist as exc:
            raise serializers.ValidationError("TÃ©cnico nÃ£o encontrado.") from exc

    def validate_status(self, value):
        if not self.instance or value == self.instance.status:
            return value

        try:
            status_atual_index = self.STATUS_FLOW.index(self.instance.status)
            novo_status_index = self.STATUS_FLOW.index(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Status inválido para o fluxo da intervenção."
            ) from exc

        if novo_status_index != status_atual_index + 1:
            proximo_status_index = status_atual_index + 1
            status_esperado = (
                self.STATUS_FLOW[proximo_status_index]
                if proximo_status_index < len(self.STATUS_FLOW)
                else None
            )
            if status_esperado:
                raise serializers.ValidationError(
                    f"Transição inválida. O próximo status deve ser '{status_esperado}'."
                )
            raise serializers.ValidationError("Esta intervenção já está fechada.")

        return value

    def update(self, instance, validated_data):
        tecnico = validated_data.pop("tecnico_id", None)
        previous_status = instance.status
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            if tecnico is not None:
                instance.tecnico = tecnico
            try:
                instance.save()
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict or exc.messages) from exc
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
            raise serializers.ValidationError("TÃ©cnico nÃ£o encontrado.") from exc


class AdicionarComentarioSerializer(serializers.Serializer):
    texto = serializers.CharField()
    visivel_cliente = serializers.BooleanField(default=True)


class CarregarAnexoSerializer(serializers.Serializer):
    ficheiro = serializers.FileField()
    descricao = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        if "ficheiro" not in data and "anexos" in data:
            data = data.copy()
            data["ficheiro"] = data["anexos"]
        return super().to_internal_value(data)


class TecnicoRelatorioListaSerializer(serializers.ModelSerializer):
    intervencao = serializers.SerializerMethodField()
    tecnico_id = serializers.UUIDField(source="tecnico.id", read_only=True)
    tecnico_nome = serializers.CharField(source="tecnico.nome", read_only=True)

    class Meta:
        model = HoraTrabalho
        fields = (
            "id",
            "intervencao",
            "tecnico_id",
            "tecnico_nome",
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

class TecnicoRelatorioEscritaSerializer(serializers.ModelSerializer):
    intervencao_id = serializers.UUIDField(write_only=True)
    tecnico_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = HoraTrabalho
        fields = ("intervencao_id", "tecnico_id", "horas", "data_trabalho", "descricao", "tipo")

    def validate(self, attrs):
        try:
            attrs["intervencao"] = Intervencao.objects.get(id=attrs.pop("intervencao_id"))
        except Intervencao.DoesNotExist as exc:
            raise serializers.ValidationError({"intervencao_id": "IntervenÃ§Ã£o nÃ£o encontrada."}) from exc
        request = self.context.get("request")
        tecnico_id = attrs.pop("tecnico_id", None)
        if request and request.user.perfil == Usuario.PerfilChoices.TECNICO:
            attrs["tecnico"] = request.user
        elif tecnico_id:
            try:
                attrs["tecnico"] = Usuario.objects.get(id=tecnico_id, perfil=Usuario.PerfilChoices.TECNICO)
            except Usuario.DoesNotExist as exc:
                raise serializers.ValidationError({"tecnico_id": "Tecnico nao encontrado."}) from exc
        elif attrs["intervencao"].tecnico_id:
            attrs["tecnico"] = attrs["intervencao"].tecnico
        else:
            raise serializers.ValidationError({"tecnico_id": "Este campo e obrigatorio."})
        return attrs

class TecnicoRelatorioAtualizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HoraTrabalho
        fields = ("horas", "data_trabalho", "descricao", "tipo")


HoraTrabalhoListaSerializer = TecnicoRelatorioListaSerializer
HoraTrabalhoEscritaSerializer = TecnicoRelatorioEscritaSerializer
HoraTrabalhoAtualizacaoSerializer = TecnicoRelatorioAtualizacaoSerializer
