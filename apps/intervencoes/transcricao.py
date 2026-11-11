"""Transcrição local de notas de voz com faster-whisper.

Sem Google e sem serviços externos: o modelo corre no próprio servidor.
O modelo é carregado uma única vez e reutilizado (é pesado).
"""

import io
import os
import threading

import requests

_MODELO = None
_LOCK_MODELO = threading.Lock()
_LOCK_TRANSCRICAO = threading.Lock()

# Idiomas aceites pelo Whisper. Arbëresh não é suportado oficialmente;
# usamos albanês como aproximação quando for pedido.
_ALIAS = {
    "ar": "sq",   # Arbëresh -> albanês (aproximação)
    "alb": "sq",
    "zh": "zh",
    "pt": "pt",
    "en": "en",
    "fr": "fr",
    "th": "th",
}


def _obter_modelo():
    global _MODELO
    if _MODELO is not None:
        return _MODELO
    with _LOCK_MODELO:
        if _MODELO is None:
            from faster_whisper import WhisperModel

            nome = os.environ.get("WHISPER_MODEL", "small")
            device = os.environ.get("WHISPER_DEVICE", "cpu")
            compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
            _MODELO = WhisperModel(nome, device=device, compute_type=compute_type)
    return _MODELO


def normalizar_idioma(idioma):
    if not idioma:
        return None
    return _ALIAS.get(idioma, idioma)


def transcrever_url(url, idioma=None):
    """Descarrega o áudio do URL e devolve (texto, idioma_detectado)."""
    resposta = requests.get(url, timeout=180)
    resposta.raise_for_status()

    audio = io.BytesIO(resposta.content)
    audio.name = "audio.webm"

    modelo = _obter_modelo()
    # O modelo não deve ser usado em paralelo: serializa as transcrições.
    with _LOCK_TRANSCRICAO:
        segmentos, info = modelo.transcribe(
            audio,
            language=normalizar_idioma(idioma),
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        texto = " ".join(s.text.strip() for s in segmentos if s.text and s.text.strip())

    return texto.strip(), (info.language or "").strip()


def aquecer():
    """Carrega o modelo no arranque (opcional) para evitar atraso na 1.ª vez."""
    try:
        _obter_modelo()
        return True
    except Exception:
        return False
