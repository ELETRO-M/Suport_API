from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("email",)
    actions = ("restaurar_usuarios",)

    def get_queryset(self, request):
        return Usuario.all_objects.all() 

    list_display = (
        "email",
        "nome",
        "perfil",
        "status",
        "is_deleted",
        "restaurar_link",
        "is_superuser",
        "data_criacao",
        "data_actualizacao"
    )

    list_filter = (
        "perfil",
        "status",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "email",
        "nome",
        "telefone",
        "empresa",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informação Pessoal", {
            "fields": (
                "nome",
                "telefone",
                "empresa",
                "nif",
                "endereco",
                "avatar_url",
            )
        }),
        ("Perfil", {
            "fields": (
                "perfil",
                "status",
                "especialidades",
                "data_contratacao",
                "preferencias",
            )
        }),
        ("Permissões", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Datas", {
            "fields": (
                "last_login",
                "data_criacao",
                "data_actualizacao",
            )
        }),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome",
                    "perfil",
                    "status",
                    "telefone",
                    "empresa",
                    "ip_servidor",
                    "nif",
                    "endereco",
                    "especialidades",
                    "data_contratacao",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    readonly_fields = ("data_criacao", "data_actualizacao", "last_login")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/restaurar/",
                self.admin_site.admin_view(self.restaurar_view),
                name="usuarios_usuario_restaurar",
            ),
        ]
        return custom_urls + urls

    @admin.action(description="Restaurar usuários selecionados")
    def restaurar_usuarios(self, request, queryset):
        restaurados = 0
        for usuario in queryset.filter(is_deleted=True):
            usuario.recuperar()
            restaurados += 1
        self.message_user(
            request,
            f"{restaurados} usuário(s) restaurado(s) com sucesso.",
            level=messages.SUCCESS,
        )

    def restaurar_link(self, obj):
        if not obj.is_deleted:
            return "-"
        url = reverse("admin:usuarios_usuario_restaurar", args=[obj.pk])
        return format_html('<a class="button" href="{}">Restaurar</a>', url)
    restaurar_link.short_description = "Restaurar"

    def restaurar_view(self, request, object_id):
        usuario = self.get_object(request, object_id)
        if usuario is None:
            self.message_user(request, "Usuário não encontrado.", level=messages.ERROR)
            return HttpResponseRedirect(reverse("admin:usuarios_usuario_changelist"))
        if not usuario.is_deleted:
            self.message_user(request, "Este usuário já está activo.", level=messages.INFO)
            return HttpResponseRedirect(reverse("admin:usuarios_usuario_change", args=[usuario.pk]))

        usuario.recuperar()
        self.message_user(request, "Usuário restaurado com sucesso.", level=messages.SUCCESS)
        return HttpResponseRedirect(reverse("admin:usuarios_usuario_change", args=[usuario.pk]))

    def delete_model(self, request, obj):
        
        Usuario.all_objects.filter(pk=obj.pk).hard_delete()

    def delete_queryset(self, request, queryset):
        
        queryset.delete()
