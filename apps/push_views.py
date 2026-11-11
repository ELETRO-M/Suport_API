# views do Web Push
import json

import httpx
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import connection


@api_view(["POST"])
@permission_classes([])  # Allow any user (including anonymous) to register push subscription
def push_subscribe(request):
    """
    Recebe a subscrição do frontend e guarda no banco.
    Body JSON: { "endpoint": "...", "keys": { "p256dh": "...", "auth": "..." } }
    """
    try:
        data = request.data
        endpoint = data.get("endpoint")

        if not endpoint:
            return Response(
                {"erro": "endpoint é obrigatório"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Tenta obter usuário da requisição (pode ser anonimo)
        usuario = None
        if hasattr(request, "user") and request.user.is_authenticated:
            usuario = request.user
        else:
            from apps.usuarios.models import Usuario
            try:
                usuario = Usuario.objects.first()
            except Exception:
                usuario = None

        if usuario is None:
            return Response(
                {"erro": "Nenhum usuário encontrado no sistema"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Salvar/atualizar subscrição usando raw SQL para contornar validação do _meta
        keys = data.get("keys", {})
        # Converter UUID para string de 32 caracteres (formato char(32) do banco)
        usuario_id_str = usuario.id.hex if hasattr(usuario.id, 'hex') else str(usuario.id)
        if len(usuario_id_str) > 32:
            usuario_id_str = usuario_id_str[:32]
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios_usuario SET push_subscription = %s WHERE id = %s",
                [json.dumps({"endpoint": endpoint, "keys": keys}), usuario_id_str],
            )

        return Response(
            {"status": "inscrita", "id": usuario.id},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"erro": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([])  # Allow any user to send push notifications
def push_enviar(request):
    """
    Disparar notificação push para todos os clientes inscritos.
    Body JSON: { "tipo": "nova_mensagem" | "novo_audio", "intervencao_id": int, "texto": "...", "email": "usuario@email.com" }
    """
    try:
        data = request.data
        tipo = data.get("tipo")
        intervencao_id = data.get("intervencao_id")
        texto = data.get("texto", "")
        # Email opcional para enviar apenas para um usuário específico
        email_para = data.get("email", None)

        if not tipo or not intervencao_id:
            return Response(
                {"erro": "tipo e intervencao_id são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar subscrições - usuários que têm push_subscription preenchido no banco
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, push_subscription FROM usuarios_usuario WHERE push_subscription IS NOT NULL AND push_subscription != '{}'"
            )
            rows = cursor.fetchall()

        subs = []
        for row in rows:
            usuario_id, email, push_json = row
            if push_json:
                try:
                    sub = json.loads(push_json) if isinstance(push_json, str) else push_json
                    if sub and sub.get("endpoint"):
                        sub_copy = dict(sub) if not isinstance(sub, dict) else sub
                        sub_copy["usuario_email"] = email
                        subs.append(sub_copy)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not subs:
            return Response(
                {"aviso": "Nenhuma subscrição registrada ainda"},
                status=status.HTTP_200_OK,
            )

        # Carregar chaves VAPID
        try:
            from config.vapid_keys import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_ADMIN_EMAIL
        except ImportError:
            return Response(
                {"erro": "VAPID_PRIVATE_KEY não configurada no servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not VAPID_PRIVATE_KEY:
            return Response(
                {"erro": "VAPID_PRIVATE_KEY não configurada no servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Derivar keys VAPID a partir da private key
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend

        private_key = serialization.load_pem_private_key(
            VAPID_PRIVATE_KEY.encode(), password=None, backend=default_backend()
        )
        public_key = private_key.public_key()

        # Public key em formato SubjectPublicKeyInfo (SPKI) -> base64url
        pub_spki = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        import base64

        def _b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

        pub_b64url = _b64url(pub_spki)

        # Auth secret: primeiros 7 bytes da private key em DER format
        auth_raw = (
            private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            [:7]
        )
        auth_b64url = _b64url(auth_raw)

        # Montar payload
        payload_base = {
            "title": "Nova mensagem" if tipo == "nova_mensagem" else "Novo áudio",
            "body": texto or "Você tem uma nova atualização no sistema.",
            "icon": "/static/icons/logo192.png",
            "vapid": {
                "publicKey": pub_b64url,
                "email": VAPID_ADMIN_EMAIL,
            },
        }

        sent_count = 0
        failed_count = 0

        for sub in subs:
            try:
                # Preparar authorization header VAPID
                auth_header = f"BN={auth_b64url}"

                # Endpoint do usuário
                sub_endpoint = sub.get("endpoint", "")

                if not sub_endpoint:
                    failed_count += 1
                    continue

                # Enviar via httpx
                response = httpx.post(
                    sub_endpoint,
                    json=payload_base,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json",
                    },
                    timeout=10,
                )

                if response.status_code in (200, 201, 203):
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Erro ao enviar push: {e}")
                failed_count += 1

        return Response(
            {
                "status": "processado",
                "total": len(subs),
                "sent": sent_count,
                "failed": failed_count,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"erro": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)