from rest_framework import serializers

from apps.notificacoes.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ("id", "tipo", "titulo", "mensagem", "link", "lida", "data_criacao")


class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.notificacoes.models import FCMToken
        model = FCMToken
        fields = ("token", "dispositivo_id")
        extra_kwargs = {
            "token": {"required": True, "allow_blank": False},
        }

