from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ("email",)

    def get_queryset(self, request):
        return Usuario.all_objects.all()  # ❗ ignora soft delete completamente

    list_display = (
        "email",
        "nome",
        "perfil",
        "status",
        "is_deleted",
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
        "empresa__nome",
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
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    readonly_fields = ("data_criacao", "data_actualizacao", "last_login")

    

    def delete_model(self, request, obj):
        
        Usuario.all_objects.filter(pk=obj.pk).hard_delete()

    def delete_queryset(self, request, queryset):
        
        queryset.delete()