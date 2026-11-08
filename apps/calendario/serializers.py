from rest_framework import serializers

from apps.calendario.models import (
    CategoriaObrigacao, DocumentoObrigacao, HistoricoObrigacao,
    ObrigacaoFiscal, TarefaFiscal,
)


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaObrigacao
        fields = ("id", "nome", "descricao", "dias_alerta", "data_criacao")


class ObrigacaoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    responsavel_nome = serializers.CharField(source="responsavel.nome", read_only=True, allow_null=True)
    vencida = serializers.BooleanField(read_only=True)
    proxima = serializers.BooleanField(read_only=True)

    class Meta:
        model = ObrigacaoFiscal
        fields = (
            "id", "cliente", "cliente_nome", "categoria", "categoria_nome",
            "periodicidade", "meses_custom", "periodo_inicio", "dia_vencimento",
            "data_vencimento", "data_execucao", "responsavel", "responsavel_nome",
            "estado_execucao", "observacoes", "vencida", "proxima", "data_criacao",
        )


class TarefaSerializer(serializers.ModelSerializer):
    obrigacao_numero = serializers.SerializerMethodField()
    responsavel_nome = serializers.CharField(source="responsavel.nome", read_only=True, allow_null=True)

    class Meta:
        model = TarefaFiscal
        fields = ("id", "obrigacao", "obrigacao_numero", "titulo", "responsavel", "responsavel_nome", "prazo_execucao", "status", "concluida_em")

    def get_obrigacao_numero(self, obj):
        return str(obj.obrigacao_id)


class DocumentoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoObrigacao
        fields = ("id", "obrigacao", "nome", "descricao", "ficheiro", "url", "data_criacao")

    def get_url(self, obj):
        req = self.context.get("request")
        return req.build_absolute_uri(obj.ficheiro.url) if req else obj.ficheiro.url


class HistoricoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoObrigacao
        fields = ("id", "obrigacao", "alteracao", "detalhe", "data_criacao")
