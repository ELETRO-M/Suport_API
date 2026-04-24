from typing import cast

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.configuracoes.responses import resposta_sucesso
from apps.notificacoes.models import Notificacao
from apps.notificacoes.serializers import NotificacaoSerializer


class NotificacaoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificacaoSerializer

    def get_queryset(self):
        request = cast(Request, self.request)
        queryset = Notificacao.objects.filter(utilizador=request.user)
        lidas = request.query_params.get("lidas")
        if lidas in {"true", "false"}:
            queryset = queryset.filter(lida=(lidas == "true"))
        limit = request.query_params.get("limit")
        if limit and limit.isdigit():
            return queryset[: int(limit)]
        return queryset

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return resposta_sucesso(data=serializer.data)

    @action(detail=True, methods=["put"], url_path="lida")
    def lida(self, request, pk=None):
        notificacao = self.get_object()
        notificacao.lida = True
        notificacao.save(update_fields=["lida"])
        return resposta_sucesso(message="Notificação marcada como lida")

    @action(detail=False, methods=["put"], url_path="marcar-todas-lidas")
    def marcar_todas_lidas(self, request):
        self.get_queryset().update(lida=True)
        return resposta_sucesso(message="Todas notificações marcadas como lidas")
