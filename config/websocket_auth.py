from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def get_user_from_token(token):
    close_old_connections()
    if not token:
        return AnonymousUser()

    authenticator = JWTAuthentication()
    try:
        validated_token = authenticator.get_validated_token(token)
        return authenticator.get_user(validated_token)
    except Exception:
        return AnonymousUser()


class JWTQueryStringAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await get_user_from_token(token)
        return await self.app(scope, receive, send)


def JWTQueryStringAuthMiddlewareStack(app):
    return JWTQueryStringAuthMiddleware(app)
