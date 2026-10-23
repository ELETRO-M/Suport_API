from django.core.management.base import BaseCommand

from apps.configuracoes.sms import enviar_sms


class Command(BaseCommand):
    help = "Envia um SMS de teste através do SMS Hub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--para",
            required=True,
            help="Número de destino (ex.: +244923456789)",
        )
        parser.add_argument(
            "--texto",
            default="Teste de envio de SMS do SOSTICKET.",
            help="Texto da mensagem",
        )

    def handle(self, *args, **options):
        resultado = enviar_sms(options["para"], options["texto"])

        if resultado["ok"]:
            self.stdout.write(self.style.SUCCESS(f"SMS enviado: {resultado['dados']}"))
        else:
            self.stderr.write(self.style.ERROR(f"Falha ao enviar SMS: {resultado['erro']}"))
