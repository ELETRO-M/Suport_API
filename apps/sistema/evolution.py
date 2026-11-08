import re

import cloudinary
import cloudinary.uploader
import httpx
from decouple import config as dj


def _base():
    return dj("EVOLUTION_BASE_URL", default="https://whatsapp-api.electrosoftwares.com").rstrip("/")


def _inst():
    return dj("EVOLUTION_INSTANCE", default="hunter-7121b9c32eecee07e41087f83ed0c650")


def _key():
    return dj("EVOLUTION_APIKEY", default="DE5DAE35-30FF-4C20-B475-D8876093A0C2")


def normalizar_numero(num) -> str:
    return re.sub(r"\D", "", str(num or ""))


def _request(method, path, **kwargs):
    try:
        resp = httpx.request(method, f"{_base()}{path}",
                             headers={"apikey": _key(), "Content-Type": "application/json"},
                             timeout=30.0, **kwargs)
    except Exception as e:
        return {"status_code": 502, "data": {"erro": "Falha Evolution", "detalhe": str(e)}}
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return {"status_code": resp.status_code, "data": data}


def enviar_texto(numero, texto):
    return _request("POST", f"/message/sendText/{_inst()}", json={"number": numero, "text": texto})


def enviar_media(numero, media=None, url=None, mediatype="document",
                 mimetype="application/pdf", filename="documento.pdf", caption=None):
    payload = {"number": numero, "mediatype": mediatype, "mimetype": mimetype, "fileName": filename}
    if url:
        payload["media"] = url  # Evolution espera URL dentro de media
    if media:
        payload["media"] = media
    if caption:
        payload["caption"] = caption
    return _request("POST", f"/message/sendMedia/{_inst()}", json=payload)


def find_messages(numero=None):
    if numero:
        payload = {"where": {"remoteJid": f"{numero}@s.whatsapp.net"}, "options": {"limit": 50}}
    else:
        payload = {"options": {"limit": 50}}
    return _request("POST", f"/chat/findMessages/{_inst()}", json=payload)


def subir_cloudinary(conteudo: bytes, nome="arquivo") -> str:
    cloudinary.config(
        cloud_name=dj("CLOUDINARY_CLOUD_NAME", default="dhpain7wq"),
        api_key=dj("CLOUDINARY_API_KEY", default="772767193863469"),
        api_secret=dj("CLOUDINARY_API_SECRET", default="wJH5akhlGNv1Ltg-OURGSpTODTQ"),
        secure=True,
    )
    res = cloudinary.uploader.upload(conteudo, folder="whatsapp", public_id=f"arq-{nome}", resource_type="auto")
    return res.get("secure_url", "")


def extrair_mensagem(msg: dict):
    if not isinstance(msg, dict):
        return "", "unknown", "", ""
    if msg.get("conversation"):
        return msg["conversation"], "conversation", "", ""
    ext = msg.get("extendedTextMessage") or {}
    if ext.get("text"):
        return ext["text"], "conversation", "", ""
    for tipo, chave in [("document", "documentMessage"), ("image", "imageMessage"),
                        ("video", "videoMessage"), ("audio", "audioMessage"),
                        ("sticker", "stickerMessage")]:
        bloco = msg.get(chave) or {}
        if bloco:
            return (bloco.get("caption") or "", tipo, bloco.get("fileName") or "", bloco.get("mimetype") or "")
    return "", "unknown", "", ""
