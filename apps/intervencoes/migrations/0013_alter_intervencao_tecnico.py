from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('intervencoes', '0012_alter_anexointervencao_criado_por_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='intervencao',
            name='tecnico',
            field=models.ForeignKey(blank=True, limit_choices_to={'is_deleted': False, 'perfil__in': ['tecnico', 'admin']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='intervencoes_atribuidas', to=settings.AUTH_USER_MODEL),
        ),
    ]
