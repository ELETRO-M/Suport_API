from rest_framework import serializers

from apps.sistema.models import ConfiguracaoSistema, Conversa, Mensagem, RespostaRapida


class ConfiguracaoSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoSistema
        fields = (
            "moeda",
            "fuso_horario",
            "email_notificacoes",
            "prazo_padrao_intervencao",
            "taxa_hora",
            "taxa_mensal",
            "taxa_anual"
        )


class ConversaSerializer(serializers.ModelSerializer):
    tecnico_nome = serializers.CharField(source="tecnico.nome", read_only=True, allow_null=True)
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True, allow_null=True)
    total_mensagens = serializers.SerializerMethodField()

    class Meta:
        model = Conversa
        fields = (
            "id", "numero", "nome", "ultima_mensagem", "ultima_mensagem_em",
            "nao_lidas", "tecnico", "tecnico_nome", "cliente", "cliente_nome",
            "total_mensagens", "data_criacao", "data_actualizacao",
        )
        read_only_fields = ("id", "ultima_mensagem", "ultima_mensagem_em", "nao_lidas", "data_criacao", "data_actualizacao")

    def get_total_mensagens(self, obj):
        return obj.mensagens.count()


class MensagemSerializer(serializers.ModelSerializer):
    enviado_por_nome = serializers.CharField(source="enviado_por.nome", read_only=True, allow_null=True)

    class Meta:
        model = Mensagem
        fields = (
            "id", "conversa", "wa_id", "direcao", "texto", "tipo",
            "file_name", "mimetype", "media_url", "enviado_por", "enviado_por_nome", "data_criacao",
        )
        read_only_fields = fields


class RespostaRapidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RespostaRapida
        fields = ("id", "titulo", "texto", "ativa", "data_criacao")
