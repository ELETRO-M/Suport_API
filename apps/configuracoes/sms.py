import logging
import threading
import time

import requests
from django.conf import settings

from apps.configuracoes.telefone import normalizar_numero

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 15
MAX_TENTATIVAS = 3
ESPERA_BASE_SEGUNDOS = 2


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


def _normalizar_lista(numeros) -> list[str]:
    if isinstance(numeros, str):
        numeros = [numeros]
    return [n for n in (normalizar_numero(numero) for numero in numeros or []) if n]


def enviar_sms(numeros, texto: str) -> dict:
    """
    Envia um ou vários SMS através do SMS Hub (síncrono, com retry).
    Nunca levanta excepção. Devolve sempre:
      {"ok": True,  "dados": {...}, "erro": None}
      {"ok": False, "dados": None,  "erro": "descrição"}
    """
    contactos = _normalizar_lista(numeros)

    if not contactos or not texto:
        return {"ok": False, "dados": None, "erro": "Número ou texto vazio"}

    if not getattr(settings, "SMS_HUB_URL", ""):
        return {"ok": False, "dados": None, "erro": "SMS_HUB_URL não configurado"}

    url = f"{settings.SMS_HUB_URL.rstrip('/')}/api/v1/sms/send"
    headers = {"Content-Type": "application/json"}
    payload = {"contactNo": contactos, "message": texto}

    resultado = _post_com_retry(url, payload, headers, TIMEOUT_SEGUNDOS)
    if not resultado["ok"]:
        logger.error("SMS para %s falhou: %s", ", ".join(contactos), resultado["erro"])
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
            logger.exception("Falha inesperada ao enviar SMS em segundo plano.")

    threading.Thread(target=_executar, daemon=True).start()


def enviar_sms_async(numeros, texto: str) -> None:
    """Versão não bloqueante de `enviar_sms`."""
    _enviar_em_segundo_plano(enviar_sms, numeros, texto)
