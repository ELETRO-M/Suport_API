from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from apps.intervencoes.models import Intervencao
from apps.tarefas.models import AnexoTarefa, ComentarioTarefa, Tarefa
from apps.usuarios.models import Usuario


class UtilizadorResumoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nome = serializers.CharField()
    email = serializers.EmailField()
    perfil = serializers.CharField()


class PrazoTarefaSerializer(serializers.Serializer):
    total_horas = serializers.FloatField(
        help_text="Duração total prevista (diferença entre início e fim), em horas."
    )
    restantes_horas = serializers.FloatField(
        help_text="Horas que ainda restam até ao fim do prazo (nunca negativas)."
    )
    expirado = serializers.BooleanField(help_text="`true` quando o prazo já passou.")


def _resumo_utilizador(utilizador):
    if not utilizador:
        return None
    return {
        "id": str(utilizador.id),
        "nome": utilizador.nome,
        "email": utilizador.email,
        "perfil": utilizador.perfil,
    }


@extend_schema_serializer(component_name="Tarefa")
class TarefaListaSerializer(serializers.ModelSerializer):
    numero = serializers.CharField(read_only=True, help_text="Número gerado automaticamente.")
    criado_por = serializers.SerializerMethodField(help_text="Admin que criou a tarefa.")
    atribuido_a = serializers.SerializerMethodField(help_text="Técnico a quem está atribuída.")
    intervencao = serializers.SerializerMethodField(help_text="Intervenção associada (opcional).")
    prazo = serializers.SerializerMethodField(help_text="Cálculo do prazo da tarefa.")

    class Meta:
        model = Tarefa
        fields = (
            "id",
            "numero",
            "titulo",
            "descricao",
            "estado",
            "prioridade",
            "atribuido_a",
            "criado_por",
            "intervencao",
            "data_inicio",
            "data_fim",
            "prazo",
            "data_conclusao",
            "data_criacao",
        )

    @extend_schema_field(UtilizadorResumoSerializer(allow_null=True))
    def get_atribuido_a(self, obj):
        return _resumo_utilizador(obj.atribuido_a)

    @extend_schema_field(UtilizadorResumoSerializer(allow_null=True))
    def get_criado_por(self, obj):
        return _resumo_utilizador(obj.criado_por)

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_intervencao(self, obj):
        if not obj.intervencao_id:
            return None
        return {
            "id": str(obj.intervencao_id),
            "numero": obj.intervencao.numero,
            "titulo": obj.intervencao.titulo,
        }

    @extend_schema_field(PrazoTarefaSerializer(allow_null=True))
    def get_prazo(self, obj):
        return obj.prazo


class ComentarioResumoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    utilizador = UtilizadorResumoSerializer(allow_null=True)
    texto = serializers.CharField()
    data_criacao = serializers.DateTimeField()


class AnexoResumoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    arquivo = serializers.URLField()
    nome = serializers.CharField()
    descricao = serializers.CharField()


@extend_schema_serializer(component_name="TarefaDetalhe")
class TarefaDetalheSerializer(TarefaListaSerializer):
    comentarios = serializers.SerializerMethodField(help_text="Comentários da tarefa.")
    anexos = serializers.SerializerMethodField(help_text="Ficheiros anexados à tarefa.")

    class Meta(TarefaListaSerializer.Meta):
        fields = TarefaListaSerializer.Meta.fields + ("comentarios", "anexos")

    @extend_schema_field(ComentarioResumoSerializer(many=True))
    def get_comentarios(self, obj):
        return [
            {
                "id": str(c.id),
                "utilizador": _resumo_utilizador(c.utilizador),
                "texto": c.texto,
                "data_criacao": c.data_criacao,
            }
            for c in obj.comentarios.all()
        ]

    @extend_schema_field(AnexoResumoSerializer(many=True))
    def get_anexos(self, obj):
        return [
            {
                "id": str(a.id),
                "arquivo": a.arquivo.url,
                "nome": str(a.arquivo.name).split("/")[-1],
                "descricao": a.descricao,
            }
            for a in obj.anexos.all()
        ]


class TarefaEscritaSerializer(serializers.ModelSerializer):
    titulo = serializers.CharField(help_text="Título curto da tarefa (máx. 255 carateres).")
    descricao = serializers.CharField(help_text="Descrição detalhada da tarefa.")
    estado = serializers.ChoiceField(
        choices=Tarefa.EstadoChoices.choices,
        required=False,
        help_text="Estado inicial da tarefa (opcional; por defeito `pendente`).",
    )
    prioridade = serializers.ChoiceField(
        choices=Tarefa.PrioridadeChoices.choices,
        required=False,
        help_text="Prioridade da tarefa (opcional; por defeito `media`).",
    )
    atribuido_a_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="ID do admin/técnico activo a quem a tarefa é atribuída.",
    )
    intervencao_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="ID da intervenção associada (opcional).",
    )
    data_inicio = serializers.DateTimeField(
        required=True,
        help_text="Início previsto da tarefa (ex.: 2026-09-22T09:00:00).",
    )
    data_fim = serializers.DateTimeField(
        required=True,
        help_text="Prazo/fim da tarefa — quando chega e a tarefa não foi concluída, o estado passa a `expirado` (ex.: 2026-09-22T18:00:00).",
    )

    class Meta:
        model = Tarefa
        fields = (
            "titulo",
            "descricao",
            "estado",
            "prioridade",
            "atribuido_a_id",
            "intervencao_id",
            "data_inicio",
            "data_fim",
        )

    def validate(self, attrs):
        data_inicio = attrs.get("data_inicio") or getattr(self.instance, "data_inicio", None)
        data_fim = attrs.get("data_fim") or getattr(self.instance, "data_fim", None)
        if data_inicio and data_fim and data_fim <= data_inicio:
            raise serializers.ValidationError({
                "data_fim": "A data de término deve ser posterior à data de início."
            })
        return attrs

    def validate_atribuido_a_id(self, value):
        if value is None:
            return value
        destino = Usuario.all_objects.filter(id=value, is_deleted=False).first()
        invalido = not (
            destino
            and destino.perfil in (Usuario.PerfilChoices.ADMIN, Usuario.PerfilChoices.TECNICO)
            and destino.status == Usuario.StatusChoices.ACTIVO
        )
        if invalido:
            raise serializers.ValidationError(
                "O destinatário deve ser um admin ou técnico activo."
            )
        return value

    def validate_intervencao_id(self, value):
        if value is None:
            return value
        intervencao = Intervencao.all_objects.filter(id=value, is_deleted=False).first()
        if not intervencao:
            raise serializers.ValidationError("A intervenção informada não existe.")
        return value


class AtribuirTarefaSerializer(serializers.Serializer):
    atribuido_a_id = serializers.UUIDField(
        help_text="ID do admin/técnico activo que passa a ser o responsável."
    )

    def validate_atribuido_a_id(self, value):
        candidato = Usuario.all_objects.filter(
            id=value,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO,
        ).first()
        if not candidato or candidato.perfil not in (
            Usuario.PerfilChoices.ADMIN,
            Usuario.PerfilChoices.TECNICO,
        ):
            raise serializers.ValidationError("Destinatário inválido.")
        return candidato


class AlterarEstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=Tarefa.EstadoChoices.choices,
        help_text="Novo estado da tarefa. O técnico atribuído só pode usar `em_progresso` e `concluida`; cancelar é exclusivo do admin criador.",
    )


class ComentarioTarefaSerializer(serializers.ModelSerializer):
    utilizador = serializers.SerializerMethodField()

    class Meta:
        model = ComentarioTarefa
        fields = ("id", "utilizador", "texto", "data_criacao")

    def get_utilizador(self, obj):
        return _resumo_utilizador(obj.utilizador)


@extend_schema_serializer(component_name="AdicionarComentarioTarefa")
class AdicionarComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComentarioTarefa
        fields = ("texto",)
        extra_kwargs = {"texto": {"help_text": "Texto do comentário (não pode ser vazio)."}}

    def validate_texto(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("O comentário não pode estar vazio.")
        return value


@extend_schema_serializer(component_name="CarregarAnexoTarefa")
class CarregarAnexoSerializer(serializers.ModelSerializer):
    arquivo = serializers.FileField(help_text="Ficheiro a anexar (um ou mais).")
    descricao = serializers.CharField(required=False, help_text="Descrição opcional do ficheiro.")

    class Meta:
        model = AnexoTarefa
        fields = ("arquivo", "descricao")


class TarefaCriadaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    numero = serializers.CharField(help_text="Número gerado automaticamente (TAR-AAAA-NNN).")
    estado = serializers.CharField(help_text="Estado da tarefa após a operação.")
    data_conclusao = serializers.DateTimeField(required=False, help_text="Data de conclusão (quando aplicável).")


class AtribuirRespostaSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="ID da tarefa.")
    atribuido_a_id = serializers.UUIDField(help_text="ID do responsável atribuído.")
    atribuido_a_nome = serializers.CharField(help_text="Nome do responsável atribuído.")