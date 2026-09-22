from django.contrib import admin

from apps.tarefas.models import AnexoTarefa, ComentarioTarefa, Tarefa


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("numero", "titulo", "estado", "prioridade", "atribuido_a", "data_fim")
    list_filter = ("estado", "prioridade")
    search_fields = ("numero", "titulo", "descricao")
    readonly_fields = ("numero", "data_criacao", "data_actualizacao")


@admin.register(ComentarioTarefa)
class ComentarioTarefaAdmin(admin.ModelAdmin):
    list_display = ("tarefa", "utilizador", "texto", "data_criacao")
    search_fields = ("tarefa__numero", "texto")


@admin.register(AnexoTarefa)
class AnexoTarefaAdmin(admin.ModelAdmin):
    list_display = ("tarefa", "arquivo", "descricao", "tamanho")