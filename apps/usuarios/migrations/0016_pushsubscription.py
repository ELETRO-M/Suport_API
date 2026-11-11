# Migration: Add push_subscription field to Usuario
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0015_empresa_regime'),  # última migração conhecida boa
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='push_subscription',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='Dados da subscrição Web Push (endpoint, keys p256dh, auth)',
                default=dict,
            ),
        ),
    ]