import time
from django.core.management.base import BaseCommand
from apps.intervencoes.models import AnexoIntervencao


class Command(BaseCommand):
    help = "Regenera marcas d'água de todos os anexos"

    def handle(self, *args, **options):
        ids = list(
            AnexoIntervencao.objects.filter(
                intervencao__tecnico__isnull=False
            ).values_list("id", flat=True)
        )

        total = len(ids)
        ok = 0
        erros = 0

        self.stdout.write(f"A regenerar marcas de {total} anexos...")

        for i, anexo_id in enumerate(ids, 1):
            anexo = AnexoIntervencao.objects.get(pk=anexo_id)
            try:
                anexo.arquivo_marcado_url = ""
                anexo.save(update_fields=["arquivo_marcado_url"])
                anexo.gerar_marca_dagua()
                ok += 1
            except Exception as e:
                self.stderr.write(f"  ERRO [{anexo_id}]: {e}")
                erros += 1

            if i % 10 == 0 or i == total:
                self.stdout.write(f"  Progresso: {i}/{total}")

            if ok > 0 and ok % 5 == 0:
                time.sleep(2)

        self.stdout.write(self.style.SUCCESS(f"Concluído: {ok} ok, {erros} erros"))
