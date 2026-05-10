from django.core.management.base import BaseCommand
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = "Cria o utilizador admin padrão se não existir"

    def handle(self, *args, **options):
        email = "linux@gmail.com"
        password = "12345"

        if Usuario.all_objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"Admin '{email}' já existe."))
            return

        try:
            user = Usuario.objects.create_superuser(
                email=email,
                password=password,
                nome="Administrador",
            )
            self.stdout.write(self.style.SUCCESS(f"Admin criado: {user.email}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao criar admin: {e}"))
