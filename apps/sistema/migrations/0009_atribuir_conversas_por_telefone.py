"""Atribui as conversas existentes ao utilizador cujo telefone corresponde.

Corrige o historico: antes, uma conversa criada pelo webhook ficava sem
``tecnico`` e sem ``cliente`` (aparecia como "Por identificar" ou era
mostrada no chat errado). Agora cada numero e comparado com o telefone dos
utilizadores pelos ultimos 9 digitos:

    conversa.numero == telefone de um tecnico -> conversa.tecnico
    conversa.numero == telefone de um cliente -> conversa.cliente

O nome da conversa passa a ser o nome do utilizador quando estava vazio.
"""

import re

from django.db import migrations


def _sufixo(valor):
    n = re.sub(r"\D", "", str(valor or ""))
    return n[-9:] if len(n) >= 9 else ""


def atribuir_conversas(apps, schema_editor):
    Conversa = apps.get_model("sistema", "Conversa")
    Usuario = apps.get_model("usuarios", "Usuario")

    utilizadores = list(
        Usuario.objects.filter(
            is_deleted=False,
            perfil__in=("tecnico", "cliente"),
        ).values("id", "perfil", "telefone", "nome")
    )

    for conversa in Conversa.objects.all().iterator():
        sufixo = _sufixo(conversa.numero)
        if not sufixo:
            continue

        alterados = []
        dono_nome = ""

        for u in utilizadores:
            if _sufixo(u["telefone"]) != sufixo:
                continue
            if u["perfil"] == "tecnico" and conversa.tecnico_id is None:
                conversa.tecnico_id = u["id"]
                alterados.append("tecnico")
                dono_nome = dono_nome or u["nome"]
            elif u["perfil"] == "cliente" and conversa.cliente_id is None:
                conversa.cliente_id = u["id"]
                alterados.append("cliente")
                dono_nome = dono_nome or u["nome"]
            if conversa.tecnico_id and conversa.cliente_id:
                break

        if not conversa.nome and dono_nome:
            conversa.nome = dono_nome
            alterados.append("nome")

        if alterados:
            conversa.save(update_fields=alterados)


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0008_normalizar_numeros_conversas"),
        ("usuarios", "0015_empresa_regime"),
    ]

    operations = [
        migrations.RunPython(atribuir_conversas, migrations.RunPython.noop),
    ]
