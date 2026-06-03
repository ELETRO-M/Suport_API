import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None


_client = None


def _inicializar_firebase():
    if firebase_admin is None:
        return None

    if not firebase_admin._apps:
        credenciais_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")
        credenciais_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
        project_id = getattr(settings, "FIREBASE_PROJECT_ID", "")

        if credenciais_json:
            credenciais = credentials.Certificate(json.loads(credenciais_json))
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


def enviar_notificacao_push(utilizador, titulo, mensagem, data=None):
    if firebase_admin is None:
        logger.warning("Firebase Admin SDK não está instalado.")
        return

    from firebase_admin import messaging
    from apps.notificacoes.models import FCMToken

    # Obter os tokens FCM associados ao utilizador
    tokens = list(FCMToken.objects.filter(utilizador=utilizador).values_list("token", flat=True))
    if not tokens:
        logger.info("Nenhum token FCM registrado para o utilizador: %s", utilizador.email)
        return

    # Formatar dados adicionais (os valores do FCM 'data' devem ser obrigatoriamente strings)
    fcm_data = {}
    if data:
        for k, v in data.items():
            fcm_data[k] = str(v) if v is not None else ""

    # Construir e enviar a mensagem multicast
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=titulo,
            body=mensagem,
        ),
        data=fcm_data,
        tokens=tokens,
    )

    try:
        # Garante a inicialização do Firebase Admin SDK se necessário
        get_firestore_client()

        response = messaging.send_each_for_multicast(message)
        logger.info(
            "Mensagens FCM enviadas: %d com sucesso, %d falhas.",
            response.success_count,
            response.failure_count,
        )

        # Limpeza de tokens inválidos
        if response.failure_count > 0:
            stale_tokens = []
            for index, resp in enumerate(response.responses):
                if not resp.success:
                    stale_token = tokens[index]
                    stale_tokens.append(stale_token)
            
            if stale_tokens:
                FCMToken.objects.filter(token__in=stale_tokens).delete()
                logger.info("Removidos %d tokens FCM inválidos/antigos.", len(stale_tokens))

    except Exception:
        logger.exception("Falha ao enviar notificações push com Firebase.")

