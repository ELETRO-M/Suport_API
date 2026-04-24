from rest_framework import serializers

from apps.sistema.models import ConfiguracaoSistema


class ConfiguracaoSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoSistema
        fields = (
            "moeda",
            "fuso_horario",
            "email_notificacoes",
            "prazo_padrao_intervencao",
            "taxa_hora_padrao",
        )
