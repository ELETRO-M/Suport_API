from django.contrib import admin

from apps.notificacoes.models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ("utilizador", "tipo", "titulo", "lida", "data_criacao")
    list_filter = ("tipo", "lida", "data_criacao")
    search_fields = ("utilizador__nome", "utilizador__email", "titulo", "mensagem")
    autocomplete_fields = ("utilizador",)
