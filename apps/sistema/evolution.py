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
    n = re.sub(r"\D", "", str(num or ""))
    if len(n) == 9 and n[0] == "9":
        return "244" + n
    if len(n) == 10 and n[0] == "0":
        return "244" + n[1:]
    return n


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
    return _request("POST", f"/message/sendText/{_inst()}", json={"number": normalizar_numero(numero), "text": texto})


def enviar_media(numero, media=None, url=None, mediatype="document",
                 mimetype="application/pdf", filename="documento.pdf", caption=None):
    payload = {"number": normalizar_numero(numero), "mediatype": mediatype, "mimetype": mimetype, "fileName": filename}
    if url:
        payload["media"] = url  # Evolution espera URL dentro de media
    if media:
        payload["media"] = media
    if caption:
        payload["caption"] = caption
    return _request("POST", f"/message/sendMedia/{_inst()}", json=payload)


def enviar_audio(numero, url=None, conteudo=None, mimetype="audio/webm",
                 filename="audio.webm", caption=None):
    """Nota de voz (PTT). Tenta sendWhatsAppAudio; se falhar, envia como media de audio."""
    b64 = None
    if conteudo:
        import base64 as b64mod
        b64 = b64mod.b64encode(conteudo).decode()

    res = _request("POST", f"/message/sendWhatsAppAudio/{_inst()}",
                   json={"number": normalizar_numero(numero), "audio": b64 or url})
    if res["status_code"] in (200, 201):
        return res

    return enviar_media(numero, media=b64, url=url, mediatype="audio",
                        mimetype=mimetype, filename=filename, caption=caption)


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
