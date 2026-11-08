from django.db import models

from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel
from apps.usuarios.models import Usuario


class ContatoWhatsApp(ModeloUUIDComTimestamps, SoftDeleteModel):
    class SalvoDeChoices(models.TextChoices):
        MANUAL = "manual", "Manual"
        WEBHOOK = "webhook", "Webhook"
        EVOLUTION = "evolution", "Evolution"

    numero = models.CharField(max_length=30, unique=True, db_index=True)
    nome = models.CharField(max_length=255, blank=True, default="")
    push_name = models.CharField(max_length=255, blank=True, default="")
    salvo_de = models.CharField(
        max_length=20, choices=SalvoDeChoices.choices, default=SalvoDeChoices.MANUAL
    )
    cliente = models.ForeignKey(
        Usuario,
        related_name="contatos_whatsapp",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"perfil": Usuario.PerfilChoices.CLIENTE},
    )
    tecnico = models.ForeignKey(
        Usuario,
        related_name="conversas_whatsapp_atribuidas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"perfil": Usuario.PerfilChoices.TECNICO},
    )

    class Meta:
        ordering = ("-data_actualizacao",)

    def __str__(self):
        return f"{self.numero} - {self.nome or self.push_name}"


class MensagemWhatsApp(ModeloUUIDComTimestamps):
    class TipoChoices(models.TextChoices):
        CONVERSATION = "conversation", "Texto"
        DOCUMENT = "document", "Documento"
        IMAGE = "image", "Imagem"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        STICKER = "sticker", "Sticker"
        UNKNOWN = "unknown", "Desconhecido"

    contato = models.ForeignKey(
        ContatoWhatsApp, related_name="mensagens", on_delete=models.CASCADE
    )
    message_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    from_me = models.BooleanField(default=False)
    texto = models.TextField(blank=True, default="")
    tipo = models.CharField(
        max_length=20, choices=TipoChoices.choices, default=TipoChoices.CONVERSATION
    )
    file_name = models.CharField(max_length=255, blank=True, default="")
    mimetype = models.CharField(max_length=100, blank=True, default="")
    whatsapp_ts = models.BigIntegerField(null=True, blank=True)
    push_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ("whatsapp_ts", "data_criacao")
