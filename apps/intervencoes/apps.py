from django.apps import AppConfig


class IntervencoesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.intervencoes"

    def ready(self):
        import apps.intervencoes.signal
