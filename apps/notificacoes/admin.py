from django.contrib import admin

from apps.notificacoes.models import Notificacao, FCMToken


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ("utilizador", "token_resumo", "dispositivo_id", "data_criacao")
    search_fields = ("utilizador__nome", "utilizador__email", "token", "dispositivo_id")
    autocomplete_fields = ("utilizador",)
    ordering = ("-data_criacao",)

    def token_resumo(self, obj):
        return f"{obj.token[:30]}..." if obj.token else ""
    token_resumo.short_description = "Token FCM"


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ("utilizador", "tipo", "titulo", "lida", "data_criacao")
    list_filter = ("tipo", "lida", "data_criacao")
    search_fields = ("utilizador__nome", "utilizador__email", "titulo", "mensagem")
    autocomplete_fields = ("utilizador",)
    ordering = ("-data_criacao",)
    
    def get_queryset(self, request):
        return Notificacao.all_objects.all()

    def delete_model(self, request, obj):
        obj.all_objects.filter(pk=obj.pk).hard_delete()

    def delete_queryset(self, request, queryset):
        
        queryset.delete()
