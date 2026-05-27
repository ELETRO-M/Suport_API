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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "cliente":

            contrato_id = request.GET.get("contrato")

            if contrato_id:

                from apps.contratos.models import Contrato

                contrato = Contrato.objects.filter(
                    id=contrato_id
                ).first()

                if contrato:
                    kwargs["queryset"] = Usuario.objects.filter(
                        empresa=contrato.empresa,
                        perfil=Usuario.PerfilChoices.CLIENTE,
                        is_deleted=False,
                        status=Usuario.StatusChoices.ACTIVO,
                    )

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )
    list_display = ("numero","is_deleted", "titulo", "cliente", "tecnico", "status", "prioridade", "data_abertura")
    list_filter = ("status", "prioridade", "data_abertura")
    search_fields = ("numero", "titulo", "descricao", "cliente__nome", "tecnico__nome")
    autocomplete_fields = ("cliente", "tecnico", "contrato")
    inlines = (
        HistoricoEstadoIntervencaoInline,
        ComentarioIntervencaoInline,
        AnexoIntervencaoInline,
        HoraTrabalhoInline,
    )
    def restaurar_view(self, request, object_id):
        intervencao = self.get_object(request, object_id)
        if intervencao is None:
            self.message_user(request, "Intervenção não encontrada.", level=messages.ERROR)
            return HttpResponseRedirect(reverse("admin:intervencoes_intervencao_changelist"))
        if not intervencao.is_deleted:
            self.message_user(request, "Esta intervenção já está activa.", level=messages.INFO)
            return HttpResponseRedirect(reverse("admin:intervencoes_intervencao_change", args=[intervencao.pk]))

        intervencao.recuperar()
        self.message_user(request, "Intervenção restaurada com sucesso.", level=messages.SUCCESS)
        return HttpResponseRedirect(reverse("admin:intervencoes_intervencao_change", args=[intervencao.pk]))

    def delete_model(self, request, obj):

        Intervencao.all_objects.filter(pk=obj.pk).delete()

    def delete_queryset(self, request, queryset):
        
        queryset.delete()
    def get_queryset(self, request):
        return Intervencao.all_objects.all()



@admin.register(HoraTrabalho)
class HoraTrabalhoAdmin(admin.ModelAdmin):
    list_display = ("intervencao", "tecnico", "horas", "data_trabalho", "tipo")
    list_filter = ("data_trabalho", "tipo")
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
