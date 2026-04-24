from django.contrib import admin

from apps.sistema.models import ConfiguracaoSistema


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ("moeda", "fuso_horario", "email_notificacoes", "prazo_padrao_intervencao", "taxa_hora_padrao")
