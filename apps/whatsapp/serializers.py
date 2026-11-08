from rest_framework import serializers

from apps.whatsapp.models import ContatoWhatsApp, MensagemWhatsApp


class ContatoWhatsAppSerializer(serializers.ModelSerializer):
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True, allow_null=True)
    tecnico_nome = serializers.CharField(source="tecnico.nome", read_only=True, allow_null=True)

    class Meta:
        model = ContatoWhatsApp
        fields = (
            "id", "numero", "nome", "push_name", "salvo_de",
            "cliente", "cliente_nome", "tecnico", "tecnico_nome",
            "data_criacao", "data_actualizacao",
        )
        read_only_fields = ("id", "salvo_de", "data_criacao", "data_actualizacao")


class MensagemWhatsAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensagemWhatsApp
        fields = (
            "id", "contato", "message_id", "from_me", "texto", "tipo",
            "file_name", "mimetype", "whatsapp_ts", "push_name", "data_criacao",
        )
        read_only_fields = fields
