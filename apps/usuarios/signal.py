from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notificacoes.models import Notificacao
from apps.usuarios.models import Usuario
from apps.configuracoes.whatsapp import enviar_whatsapp


@receiver(post_save, sender=Usuario)
def criar_notificacao_admins(sender, instance, created, **kwargs):

    if created and instance.perfil == Usuario.PerfilChoices.CLIENTE:

        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )

        Notificacao.objects.create(
            utilizador=instance,
            tipo="sistema",
            titulo="Seja bem-vindo(a) ao nosso sistema!",
            mensagem="Seja bem-vindo(a) ao nosso sistema!",
        )
        enviar_whatsapp(numero=f"{instance.telefone}", texto="""👋 **Olá! Seja bem-vindo ao SOSTICKET!** 🎫

Estamos felizes por ter você conosco! O **SOSTICKET** é a nossa plataforma de suporte, criada para tornar o atendimento mais rápido, organizado e eficiente.

🛠️ **Através do SOSTICKET você pode:**
• Abrir chamados de suporte
• Acompanhar o andamento das solicitações
• Consultar o histórico dos atendimentos
• Receber atualizações sobre os seus chamados
• Entrar em contacto com a nossa equipa de suporte

💬 **Como podemos ajudar?**

Envie a sua solicitação e nossa equipa estará pronta para atender você.

🚀 **SOSTICKET — Seu suporte, simples e eficiente.**
"""
) 

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo="Novo cliente cadastrado",
                mensagem=f"O cliente {instance.nome} na empresa {instance.empresa.nome} foi cadastrado.",
            )
            enviar_whatsapp(numero=f"{admin.telefone}", texto = (
    "🔔 *Novo cliente cadastrado*\n\n"
    f"👤 *Cliente:* {instance.nome}\n"
    f"🏢 *Empresa:* {instance.empresa.nome}\n\n"
    f"🖊 *Criado por:* {instance.criado_por}"

    "O cliente foi cadastrado com sucesso."
))

    if created and instance.perfil == Usuario.PerfilChoices.TECNICO:

        admins = Usuario.objects.filter(
            perfil=Usuario.PerfilChoices.ADMIN,
            is_deleted=False,
            status=Usuario.StatusChoices.ACTIVO
        )

        Notificacao.objects.create(
            utilizador=instance,
            tipo="sistema",
            titulo="Seja bem-vindo(a) ao nosso sistema!",
            mensagem="Seja bem-vindo(a) ao nosso sistema!",
        )
        enviar_whatsapp(
            numero=instance.telefone,
            texto=(
                f"👋 *Olá, {instance.nome}!*\n\n"
                f"Foste adicionado como técnico no SOSTICKETS.\n"
                "A partir de agora vais receber aqui os tickets atribuídos a ti."
            ),
        )
        

        especialidades_list = instance.especialidades if isinstance(instance.especialidades, list) else []
        especialidades_str = ", ".join(str(e) for e in especialidades_list)

        for admin in admins:
            Notificacao.objects.create(
                utilizador=admin,
                tipo="sistema",
                titulo="Novo técnico cadastrado",
                mensagem=f"O técnico {instance.nome} com a(s) especialidade(s) ({especialidades_str}) foi cadastrado.",
            )
            enviar_whatsapp(
        numero=admin.telefone,  # ajusta ao campo onde guardas o número
        texto=(
            f"🛠️ *NOVO TECNICO ADICIONADO PELO*\n\n"
            f"👤 *Técnico:* {instance.nome}\n"
            f"🖊 *Criado por:* {instance.criado_por}\n"
            f"🏢 *Empresa:* {admin.empresa.nome if admin.empresa else '—'}\n"
            f"📞 *Contacto:* {instance.telefone}\n\n"
            "O técnico já pode receber tickets."
        ),
    )
