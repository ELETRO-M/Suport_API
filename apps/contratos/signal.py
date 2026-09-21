from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.configuracoes.whatsapp import enviar_whatsapp
from apps.contratos.models import Contrato
from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario


@receiver(post_save, sender=Contrato)
def criar_notificacao_admins(sender, instance, created, **kwargs):

    if created:

        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )
        criado_por = getattr(instance, "criado_por", None) or "sistema"
        texto_whatsapp = (
            "📄 *Novo contrato*\n\n"
            f"📋 *Tipo:* {instance.tipo_contrato}\n"
            f"🏢 *Empresa:* {instance.Empresa.nome}\n"
            f"⌚ *Horas contratadas:* {instance.horas_contratadas}\n"
            f"🖊 *Criado por:* {criado_por}\n"
            f"📄 *Descrição:* {instance.descricao_contrato}"
        )

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo="Novo contrato",
                mensagem=f"Novo contrato {instance.tipo_contrato} criado para a empresa {instance.Empresa.nome}.",
            )
            if admin.telefone:
                enviar_whatsapp(numero=admin.telefone, texto=texto_whatsapp)