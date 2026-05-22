from rest_framework import serializers

from apps.notificacoes.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ("id", "tipo", "titulo", "mensagem", "link", "lida","delete", "data_criacao")
