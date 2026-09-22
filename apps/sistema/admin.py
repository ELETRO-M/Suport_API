from django.contrib import admin

from apps.sistema.models import ConfiguracaoSistema, Conversa, Mensagem


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ("moeda", "fuso_horario", "email_notificacoes", "prazo_padrao_intervencao", "taxa_hora","taxa_mensal","taxa_anual")


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome", "ultima_mensagem_em", "nao_lidas")
    search_fields = ("numero", "nome")


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("conversa", "direcao", "texto", "data_criacao")
    list_filter = ("direcao",)
