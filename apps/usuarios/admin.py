from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("email",)
    list_display = ("email", "nome", "perfil", "status", "is_staff", "is_superuser")
    list_filter = ("perfil", "status", "is_staff", "is_superuser")
    search_fields = ("email", "nome", "telefone", "empresa")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informacao Pessoal", {"fields": ("nome", "telefone", "empresa", "nif", "endereco", "avatar_url")}),
        ("Perfil", {"fields": ("perfil", "status", "especialidades", "data_contratacao", "preferencias")}),
        ("Permissoes", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "data_criacao", "data_actualizacao")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nome", "perfil", "status", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )
    readonly_fields = ("data_criacao", "data_actualizacao", "last_login")
