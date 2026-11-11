from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("intervencoes", "0013_ordenar_comentarios"),
    ]

    operations = [
        migrations.AddField(
            model_name="anexointervencao",
            name="transcricao",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="anexointervencao",
            name="idioma_transcricao",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
