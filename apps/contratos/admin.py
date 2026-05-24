from django.contrib import admin

from apps.contratos.models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = (
        "Empresa",
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
    search_fields = ("Empresa__nome", "Empresa__email", "observacoes")
    autocomplete_fields = ("Empresa",)

    def get_queryset(self, request):
        return Contrato.all_objects.all() 
