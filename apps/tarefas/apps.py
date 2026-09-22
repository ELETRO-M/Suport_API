from django.apps import AppConfig


class TarefasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tarefas"

    def ready(self):
        import apps.tarefas.signal