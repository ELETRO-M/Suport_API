from django.contrib import admin

from apps.contratos.models import Contrato


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "tipo_contrato","tipo_de_pagamento", "status", "horas_contratadas", "horas_utilizadas","delete","data_inicio", "data_fim")
    list_filter = ("tipo_contrato", "status", "data_inicio", "data_fim")
    search_fields = ("cliente__nome", "cliente__email", "observacoes")
    autocomplete_fields = ("cliente",)
