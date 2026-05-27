from django.contrib import admin

from apps.contratos.models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = (
        "descricao_contrato",
        "tipo_contrato",
        "tipo_de_pagamento",
        "status",
        "is_deleted",
        "horas_contratadas",
        "horas_utilizadas",
        "horas_disponiveis",
        "valor_total",
        "valor_hora",
        "data_inicio",
        "data_fim",
    )
    list_filter = ("tipo_contrato", "status","is_deleted", "data_inicio", "data_fim")
    search_fields = ("Empresa__nome", "Empresa__email", "observacoes")
    autocomplete_fields = ("Empresa",)

    def get_queryset(self, request):
        return Contrato.all_objects.all() 
    def delete_model(self, request, obj):
        obj.delete()
        
