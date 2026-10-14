import logging
import os
import re
import threading
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CODIGO_PAIS = "244"  # Angola

TIMEOUT_SEGUNDOS = 15
TIMEOUT_DOCUMENTO_SEGUNDOS = 30
MAX_TENTATIVAS = 3
ESPERA_BASE_SEGUNDOS = 2

MIMETYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".zip": "application/zip",
    ".rar": "application/vnd.rar",
    ".mp4": "video/mp4",
}


def _normalizar_numero(numero: str) -> str:
    """
    Deixa apenas dígitos e garante o código do país (Angola) no início.

    Aceita, por exemplo: "+244 923 456 789", "923456789", "0923456789",
    "00244923456789" e devolve sempre "244923456789".
    """
    numero = re.sub(r"\D", "", str(numero or ""))
    if not numero:
        return ""

    if numero.startswith("00"):
        numero = numero[2:]

    if numero.startswith(CODIGO_PAIS):
        return numero

    if numero.startswith("0"):
        numero = numero.lstrip("0")

    if len(numero) == 9:
        return CODIGO_PAIS + numero

    return numero


def _post_com_retry(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    """
    Executa um POST com tentativas repetidas em caso de falha temporária.
    Erros do cliente (HTTP 4xx) não são repetidos. Devolve sempre um dict
    {"ok", "dados", "erro"}.
    """
    ultimo_erro = "Erro desconhecido"

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return {"ok": True, "dados": resp.json(), "erro": None}

        except requests.HTTPError as e:
            resposta = e.response
            status_code = resposta.status_code if resposta is not None else None
            corpo = resposta.text if resposta is not None else ""
            ultimo_erro = f"HTTP {status_code}: {corpo}"
            if status_code is not None and status_code < 500:
                break
        except requests.RequestException as e:
            ultimo_erro = f"Falha de ligação: {e}"
        except ValueError:
            ultimo_erro = "A API respondeu com algo que não é JSON"
            break

        if tentativa < MAX_TENTATIVAS:
            time.sleep(ESPERA_BASE_SEGUNDOS * tentativa)

    return {"ok": False, "dados": None, "erro": ultimo_erro}


def enviar_whatsapp(numero: str, texto: str) -> dict:
    """
    Envia uma mensagem de texto por WhatsApp (síncrono, com retry).
    Nunca levanta excepção. Devolve sempre:
      {"ok": True,  "dados": {...}, "erro": None}
      {"ok": False, "dados": None,  "erro": "descrição"}
    """
    numero = _normalizar_numero(numero)

    if not numero or not texto:
        return {"ok": False, "dados": None, "erro": "Número ou texto vazio"}

    url = f"{settings.WHATSAPP_API_URL}/message/sendText/{settings.WHATSAPP_INSTANCE}"
    headers = {"apikey": settings.WHATSAPP_API_KEY, "Content-Type": "application/json"}

    resultado = _post_com_retry(
        url, {"number": numero, "text": texto}, headers, TIMEOUT_SEGUNDOS
    )
    if not resultado["ok"]:
        logger.error("WhatsApp para %s falhou: %s", numero, resultado["erro"])
    return resultado


def enviar_whatsapp_documento(
    numero: str, arquivo_url: str, nome_arquivo: str, descricao: str = ""
) -> dict:
    """
    Envia um documento (ficheiro) por WhatsApp (síncrono, com retry).
    Nunca levanta excepção. Devolve sempre:
      {"ok": True,  "dados": {...}, "erro": None}
      {"ok": False, "dados": None,  "erro": "descrição"}
    """
    numero = _normalizar_numero(numero)

    if not numero or not arquivo_url:
        return {"ok": False, "dados": None, "erro": "Número ou arquivo vazio"}

    extensao = os.path.splitext(nome_arquivo or "")[1].lower()
    mimetype = MIMETYPES.get(extensao, "application/octet-stream")

    url = f"{settings.WHATSAPP_API_URL}/message/sendMedia/{settings.WHATSAPP_INSTANCE}"
    headers = {"apikey": settings.WHATSAPP_API_KEY, "Content-Type": "application/json"}
    payload = {
        "number": numero,
        "mediatype": "document",
        "mimetype": mimetype,
        "caption": descricao or nome_arquivo,
        "fileName": nome_arquivo,
        "media": arquivo_url,
    }

    resultado = _post_com_retry(
        url, payload, headers, TIMEOUT_DOCUMENTO_SEGUNDOS
    )
    if not resultado["ok"]:
        logger.error("WhatsApp documento para %s falhou: %s", numero, resultado["erro"])
    return resultado


def _enviar_em_segundo_plano(funcao, *args, **kwargs) -> None:
    """
    Corre uma função de envio numa thread daemon, para não bloquear o request.
    A thread não acede à base de dados: recebe apenas valores simples.
    """

    def _executar():
        try:
            funcao(*args, **kwargs)
        except Exception:
            logger.exception("Falha inesperada ao enviar WhatsApp em segundo plano.")

    threading.Thread(target=_executar, daemon=True).start()


def enviar_whatsapp_async(numero: str, texto: str) -> None:
    """Versão não bloqueante de `enviar_whatsapp`."""
    _enviar_em_segundo_plano(enviar_whatsapp, numero, texto)


def enviar_whatsapp_documento_async(
    numero: str, arquivo_url: str, nome_arquivo: str, descricao: str = ""
) -> None:
    """Versão não bloqueante de `enviar_whatsapp_documento`."""
    _enviar_em_segundo_plano(
        enviar_whatsapp_documento, numero, arquivo_url, nome_arquivo, descricao
    )
