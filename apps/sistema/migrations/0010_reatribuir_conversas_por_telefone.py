"""Reatribui as conversas pelo telefone, corrigindo tambem atribuicoes erradas.

A migracao 0009 so preenchia ``tecnico``/``cliente`` quando estavam vazios.
Se uma conversa ja estava ligada ao utilizador errado (ex.: mensagens do
tecnico Stenio dentro da conversa de outra pessoa), ficava por corrigir.

Regra (a mesma do runtime em ``apps/sistema/whatsapp.py``):
  - numero da conversa == telefone completo -> prioridade maxima
  - mesmos 9 digitos finais -> aceite como o mesmo contacto
  - tecnico correspondente -> conversa.tecnico = esse tecnico
  - cliente correspondente -> conversa.cliente = esse cliente
  - nome vazio -> nome do utilizador encontrado
"""

import re

from django.db import migrations


def _digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


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
        alvo = _digitos(conversa.numero)
        if not alvo:
            continue

        candidatos = []
        for u in utilizadores:
            tel = _digitos(u["telefone"])
            if not tel:
                continue
            if tel == alvo:
                candidatos.append((2, u))
            elif len(tel) >= 9 and len(alvo) >= 9 and tel[-9:] == alvo[-9:]:
                candidatos.append((1, u))
        if not candidatos:
            continue

        candidatos.sort(key=lambda par: par[0], reverse=True)
        decidido = set()
        alterados = []
        dono_nome = ""

        for _, u in candidatos:
            if u["perfil"] == "tecnico" and "tecnico" not in decidido:
                decidido.add("tecnico")
                if conversa.tecnico_id != u["id"]:
                    conversa.tecnico_id = u["id"]
                    alterados.append("tecnico")
                dono_nome = dono_nome or u["nome"]
            elif u["perfil"] == "cliente" and "cliente" not in decidido:
                decidido.add("cliente")
                if conversa.cliente_id != u["id"]:
                    conversa.cliente_id = u["id"]
                    alterados.append("cliente")
                dono_nome = dono_nome or u["nome"]
            if len(decidido) == 2:
                break

        if not conversa.nome and dono_nome:
            conversa.nome = dono_nome
            alterados.append("nome")

        if alterados:
            conversa.save(update_fields=alterados)


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0009_atribuir_conversas_por_telefone"),
    ]

    operations = [
        migrations.RunPython(atribuir_conversas, migrations.RunPython.noop),
    ]
