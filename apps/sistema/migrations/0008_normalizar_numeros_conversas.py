"""Normaliza os numeros das conversas e junta duplicados do mesmo contacto.

Antes do webhook normalizar o JID, a Evolution podia gravar o mesmo contacto
como "933863042", "244933863042" ou "244933863042:12" - o que partia a conversa
em varias e fazia as mensagens aparecerem no chat errado.
"""

import re

from django.db import migrations


def _normalizar(numero):
    n = re.sub(r"\D", "", str(numero or ""))
    if len(n) == 9 and n[0] == "9":
        return "244" + n
    if len(n) == 10 and n[0] == "0":
        return "244" + n[1:]
    return n


def normalizar_conversas(apps, schema_editor):
    Conversa = apps.get_model("sistema", "Conversa")
    Mensagem = apps.get_model("sistema", "Mensagem")

    for conversa in Conversa.objects.all().order_by("data_criacao"):
        alvo = _normalizar(conversa.numero)
        if not alvo or alvo == conversa.numero:
            continue

        existente = Conversa.objects.filter(numero=alvo).exclude(pk=conversa.pk).first()
        if existente:
            Mensagem.objects.filter(conversa=conversa).update(conversa=existente)
            existente.nao_lidas = (existente.nao_lidas or 0) + (conversa.nao_lidas or 0)
            if conversa.ultima_mensagem_em and (
                not existente.ultima_mensagem_em
                or conversa.ultima_mensagem_em > existente.ultima_mensagem_em
            ):
                existente.ultima_mensagem_em = conversa.ultima_mensagem_em
                existente.ultima_mensagem = conversa.ultima_mensagem
            if not existente.nome and conversa.nome:
                existente.nome = conversa.nome
            existente.save()
            conversa.delete()
        else:
            conversa.numero = alvo
            conversa.save(update_fields=["numero"])


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0007_configuracaosistema_calendario_agt_url"),
    ]

    operations = [
        migrations.RunPython(normalizar_conversas, migrations.RunPython.noop),
    ]
