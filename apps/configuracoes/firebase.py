import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None
    messaging = None


_client = None


def _carregar_credenciais():
    """Tenta carregar as credenciais Firebase com suporte a \n literais no private_key."""
    raw = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "") or ""
    if not raw:
        return None

    raw = raw.strip().strip('"').strip("'")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Tentar substituir \n literais (comum em env vars)
    raw = raw.replace("\\n", "\n")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Tentar remover quebras de linha e espaços extra
    raw = raw.replace("\n", "").replace("\r", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    return None


def _inicializar_firebase():
    if firebase_admin is None:
        return None

    if not firebase_admin._apps:
        credenciais_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
        project_id = getattr(settings, "FIREBASE_PROJECT_ID", "")

        dados = _carregar_credenciais()
        if dados:
            credenciais = credentials.Certificate(dados)
            firebase_admin.initialize_app(credenciais)
        elif credenciais_path:
            credenciais = credentials.Certificate(credenciais_path)
            firebase_admin.initialize_app(credenciais)
        elif project_id:
            credenciais = credentials.ApplicationDefault()
            firebase_admin.initialize_app(credenciais, {"projectId": project_id})
        else:
            return None

    return firestore.client()


def get_firestore_client():
    global _client
    if _client is None:
        try:
            _client = _inicializar_firebase()
        except Exception:
            logger.exception("Não foi possível inicializar o Firebase.")
            _client = None
    return _client


def publicar_documento(path, data):
    client = get_firestore_client()
    if client is None:
        return

    try:
        collection_path, document_id = path.rsplit("/", 1)
        client.collection(collection_path).document(document_id).set(data)
    except Exception:
        logger.exception("Não foi possível publicar no Firebase: %s", path)


def publicar_notificacao(notificacao):
    publicar_documento(
        f"notificacoes/{notificacao.utilizador_id}/items/{notificacao.id}",
        {
            "id": str(notificacao.id),
            "tipo": notificacao.tipo,
            "titulo": notificacao.titulo,
            "mensagem": notificacao.mensagem,
            "link": notificacao.link,
            "lida": notificacao.lida,
            "utilizador_id": str(notificacao.utilizador_id),
            "data_criacao": notificacao.data_criacao.isoformat(),
        },
    )


def publicar_comentario(comentario):
    publicar_documento(
        f"intervencoes/{comentario.intervencao_id}/comentarios/{comentario.id}",
        {
            "id": str(comentario.id),
            "intervencao_id": str(comentario.intervencao_id),
            "usuario_id": str(comentario.usuario_id),
            "usuario_nome": comentario.usuario.nome,
            "texto": comentario.texto,
            "visivel_cliente": comentario.visivel_cliente,
            "data_criacao": comentario.data_criacao.isoformat(),
        },
    )


def publicar_anexo(anexo):
    publicar_documento(
        f"intervencoes/{anexo.intervencao_id}/anexos/{anexo.id}",
        {
            "id": str(anexo.id),
            "intervencao_id": str(anexo.intervencao_id),
            "utilizador_id": str(anexo.utilizador_id) if anexo.utilizador_id else None,
            "utilizador_nome": anexo.utilizador.nome if anexo.utilizador else None,
            "arquivo": anexo.arquivo.url if anexo.arquivo else None,
            "nome_arquivo": anexo.arquivo.name.split("/")[-1] if anexo.arquivo else None,
            "descricao": anexo.descricao,
            "tamanho": anexo.tamanho,
            "data_criacao": anexo.data_criacao.isoformat(),
        },
    )


def enviar_push_notificacao(utilizador, titulo, corpo, dados=None):
    if messaging is None or not utilizador.fcm_token:
        return

    try:
        mensagem = messaging.Message(
            notification=messaging.Notification(title=titulo, body=corpo),
            token=utilizador.fcm_token,
            data=dados or {},
        )
        messaging.send(mensagem)
    except Exception:
        logger.exception("Erro ao enviar push para %s", utilizador.email)
