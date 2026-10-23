from apps.configuracoes.sms import enviar_sms_async
from apps.configuracoes.whatsapp import (
    enviar_whatsapp_async,
    enviar_whatsapp_documento_async,
)


def notificar_async(numero: str, texto: str) -> None:
    """Envia a mesma mensagem por WhatsApp e por SMS, sem bloquear o request."""
    enviar_whatsapp_async(numero=numero, texto=texto)
    enviar_sms_async(numeros=numero, texto=texto)


def notificar_documento_async(
    numero: str, arquivo_url: str, nome_arquivo: str, descricao: str = ""
) -> None:
    """
    Envia o documento por WhatsApp e um SMS com o link do ficheiro.
    O SMS não suporta anexos, por isso segue apenas o link.
    """
    enviar_whatsapp_documento_async(
        numero=numero,
        arquivo_url=arquivo_url,
        nome_arquivo=nome_arquivo,
        descricao=descricao,
    )
    enviar_sms_async(
        numeros=numero,
        texto=f"{descricao or nome_arquivo}\n{arquivo_url}",
    )
