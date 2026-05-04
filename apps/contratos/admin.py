from django.contrib import admin

from apps.contratos.models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "tipo", "status", "horas_contratadas", "horas_utilizadas","delete","data_inicio", "data_fim")
    list_filter = ("tipo", "status", "data_inicio", "data_fim")
    search_fields = ("cliente__nome", "cliente__email", "observacoes")
    autocomplete_fields = ("cliente",)
