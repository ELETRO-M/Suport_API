from django.contrib import admin

from apps.contratos.models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = (
        "cliente",
        "tipo_contrato",
        "tipo_de_pagamento",
        "status",
        "is_deleted",
        "horas_contratadas",
        "horas_utilizadas",
        "horas_disponiveis",
        "valor_total",
        "data_inicio",
        "data_fim",
    )
    list_filter = ("tipo_contrato", "status","is_deleted", "data_inicio", "data_fim")
    search_fields = ("cliente__nome", "cliente__email", "observacoes")
    autocomplete_fields = ("cliente",)

    def get_queryset(self, request):
        return Contrato.all_objects.all() 
