from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sistema", "0010_reatribuir_conversas_por_telefone"),
    ]

    operations = [
        migrations.AddField(
            model_name="mensagem",
            name="transcricao",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="mensagem",
            name="idioma_transcricao",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
