from django.contrib import admin

from apps.whatsapp.models import ContatoWhatsApp, MensagemWhatsApp


@admin.register(ContatoWhatsApp)
class ContatoWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome", "salvo_de", "tecnico", "data_actualizacao")
    search_fields = ("numero", "nome")


@admin.register(MensagemWhatsApp)
class MensagemWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("contato", "tipo", "from_me", "whatsapp_ts")
    list_filter = ("tipo", "from_me")
