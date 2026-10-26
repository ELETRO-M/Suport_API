from django.core.management.base import BaseCommand

from apps.tarefas.signal import ANTECEDENCIA_ALERTA_INICIO, processar_alertas_inicio


class Command(BaseCommand):
    help = (
        "Alerta o técnico quando faltam duas horas (ou menos) para o início "
        "de uma tarefa atribuída."
    )

    def handle(self, *args, **options):
        total = processar_alertas_inicio()
        horas = int(ANTECEDENCIA_ALERTA_INICIO.total_seconds() // 3600)
        self.stdout.write(
            self.style.SUCCESS(
                f"{total} alerta(s) de início enviado(s) "
                f"(janela de {horas} horas)."
            )
        )
