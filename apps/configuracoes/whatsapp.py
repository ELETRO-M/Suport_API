import logging
import os
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CODIGO_PAIS = "244"  # Angola

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
    numero = re.sub(r"\D", "", str(numero))
    if len(numero) == 9:
        numero = CODIGO_PAIS + numero
    return numero


def enviar_whatsapp(numero: str, texto: str) -> dict:
    """
    Envia uma mensagem de texto por WhatsApp.
    Nunca levanta excepção. Devolve sempre:
      {"ok": True,  "dados": {...}, "erro": None}
      {"ok": False, "dados": None,  "erro": "descrição"}
    """
    # Normaliza: deixa só dígitos e acrescenta o código do país se faltar
    numero = _normalizar_numero(numero)

    if not numero or not texto:
        return {"ok": False, "dados": None, "erro": "Número ou texto vazio"}

    url = f"{settings.WHATSAPP_API_URL}/message/sendText/{settings.WHATSAPP_INSTANCE}"
    headers = {"apikey": settings.WHATSAPP_API_KEY, "Content-Type": "application/json"}

    try:
        resp = requests.post(
            url, json={"number": numero, "text": texto}, headers=headers, timeout=15
        )
        resp.raise_for_status()
        return {"ok": True, "dados": resp.json(), "erro": None}

    except requests.HTTPError as e:
        erro = f"HTTP {e.response.status_code}: {e.response.text}"
    except requests.RequestException as e:
        erro = f"Falha de ligação: {e}"
    except ValueError:
        erro = "A API respondeu com algo que não é JSON"

    logger.error("WhatsApp para %s falhou: %s", numero, erro)
    return {"ok": False, "dados": None, "erro": erro}


def enviar_whatsapp_documento(numero: str, arquivo_url: str, nome_arquivo: str, descricao: str = "") -> dict:
    """
    Envia um documento (ficheiro) por WhatsApp.
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

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return {"ok": True, "dados": resp.json(), "erro": None}

    except requests.HTTPError as e:
        erro = f"HTTP {e.response.status_code}: {e.response.text}"
    except requests.RequestException as e:
        erro = f"Falha de ligação: {e}"
    except ValueError:
        erro = "A API respondeu com algo que não é JSON"

    logger.error("WhatsApp documento para %s falhou: %s", numero, erro)
    return {"ok": False, "dados": None, "erro": erro}

