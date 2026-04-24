from django.contrib import admin

from apps.intervencoes.models import (
    AnexoIntervencao,
    ComentarioIntervencao,
    HistoricoEstadoIntervencao,
    HoraTrabalho,
    Intervencao,
)


class ComentarioIntervencaoInline(admin.TabularInline):
    model = ComentarioIntervencao
    extra = 0


class AnexoIntervencaoInline(admin.TabularInline):
    model = AnexoIntervencao
    extra = 0


class HistoricoEstadoIntervencaoInline(admin.TabularInline):
    model = HistoricoEstadoIntervencao
    extra = 0


class HoraTrabalhoInline(admin.TabularInline):
    model = HoraTrabalho
    extra = 0


@admin.register(Intervencao)
class IntervencaoAdmin(admin.ModelAdmin):
    list_display = ("numero", "titulo", "cliente", "tecnico", "status", "prioridade", "data_abertura")
    list_filter = ("status", "prioridade", "data_abertura")
    search_fields = ("numero", "titulo", "descricao", "cliente__nome", "tecnico__nome")
    autocomplete_fields = ("cliente", "tecnico", "contrato")
    inlines = (
        HistoricoEstadoIntervencaoInline,
        ComentarioIntervencaoInline,
        AnexoIntervencaoInline,
        HoraTrabalhoInline,
    )


@admin.register(HoraTrabalho)
class HoraTrabalhoAdmin(admin.ModelAdmin):
    list_display = ("intervencao", "tecnico", "horas", "data_trabalho", "tipo")
    list_filter = ("tipo", "data_trabalho")
    search_fields = ("intervencao__numero", "tecnico__nome", "descricao")
    autocomplete_fields = ("intervencao", "tecnico")


@admin.register(ComentarioIntervencao)
class ComentarioIntervencaoAdmin(admin.ModelAdmin):
    list_display = ("intervencao", "usuario", "visivel_cliente", "data_criacao")
    list_filter = ("visivel_cliente", "data_criacao")
    search_fields = ("intervencao__numero", "usuario__nome", "texto")
    autocomplete_fields = ("intervencao", "usuario")


@admin.register(AnexoIntervencao)
class AnexoIntervencaoAdmin(admin.ModelAdmin):
    list_display = ("intervencao", "utilizador", "descricao", "tamanho", "data_criacao")
    search_fields = ("intervencao__numero", "utilizador__nome", "descricao")
    autocomplete_fields = ("intervencao", "utilizador")


@admin.register(HistoricoEstadoIntervencao)
class HistoricoEstadoIntervencaoAdmin(admin.ModelAdmin):
    list_display = ("intervencao", "status", "alterado_por", "data_criacao")
    list_filter = ("status", "data_criacao")
    search_fields = ("intervencao__numero", "alterado_por__nome", "nota")
    autocomplete_fields = ("intervencao", "alterado_por")
