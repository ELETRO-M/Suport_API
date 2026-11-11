from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("intervencoes", "0014_anexointervencao_transcricao"),
        ("usuarios", "0015_empresa_regime"),
    ]

    operations = [
        migrations.CreateModel(
            name="SolicitacaoIntervencao",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        serialize=False,
                        editable=False,
                    ),
                ),
                ("data_criacao", models.DateTimeField(auto_now_add=True)),
                ("data_actualizacao", models.DateTimeField(auto_now=True)),
                (
                    "tipo",
                    models.CharField(
                        choices=[("intervencao", "Intervenção"), ("acesso", "Acesso")],
                        default="intervencao",
                        max_length=20,
                    ),
                ),
                ("justificativa", models.TextField(blank=True, default="")),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendente", "Pendente"),
                            ("aprovado", "Aprovado"),
                            ("rejeitado", "Rejeitado"),
                        ],
                        default="pendente",
                        max_length=20,
                    ),
                ),
                ("data_resposta", models.DateTimeField(blank=True, null=True)),
                ("motivo", models.CharField(blank=True, default="", max_length=255)),
                (
                    "intervencao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitacoes",
                        to="intervencoes.intervencao",
                    ),
                ),
                (
                    "utilizador",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitacoes_intervencao",
                        to="usuarios.usuario",
                    ),
                ),
                (
                    "respondido_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="solicitacoes_respondidas",
                        to="usuarios.usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Solicitação de intervenção",
                "verbose_name_plural": "Solicitações de intervenção",
                "ordering": ["-data_criacao"],
            },
        ),
    ]
