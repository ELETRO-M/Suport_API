import django.db.models.deletion
from django.db import migrations, models


def copiar_empresa_do_cliente(apps, schema_editor):
    Contrato = apps.get_model("contratos", "Contrato")
    Usuario = apps.get_model("usuarios", "Usuario")

    for contrato in Contrato._default_manager.filter(Empresa__isnull=True):
        cliente_id = getattr(contrato, "cliente_id", None)
        if not cliente_id:
            continue

        cliente = Usuario._default_manager.filter(pk=cliente_id).first()
        if cliente and cliente.empresa_id:
            contrato.Empresa_id = cliente.empresa_id
            contrato.save(update_fields=["Empresa"])


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0010_alter_contrato_horas_contratadas_and_more"),
        ("usuarios", "0011_remove_usuario_ip_servidor_usuario_id_postos"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrato",
            name="Empresa",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contratos",
                to="usuarios.empresa",
            ),
        ),
        migrations.RunPython(copiar_empresa_do_cliente, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contrato",
            name="Empresa",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contratos",
                to="usuarios.empresa",
            ),
        ),
        migrations.RemoveField(
            model_name="contrato",
            name="cliente",
        ),
    ]
