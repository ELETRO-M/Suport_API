from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.usuarios.models import Usuario
from apps.configuracoes.responses import resposta_sucesso
from apps.sistema.models import ConfiguracaoSistema
from apps.sistema.serializers import ConfiguracaoSistemaSerializer


class ConfiguracaoSistemaViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = ConfiguracaoSistemaSerializer
    queryset = ConfiguracaoSistema.objects.all()

    def list(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        serializer = self.get_serializer(ConfiguracaoSistema.load())
        return resposta_sucesso(data=serializer.data)

    def update(self, request, *args, **kwargs):
        if request.user.perfil != Usuario.PerfilChoices.ADMIN:
            self.permission_denied(request, message="Sem permissão para este recurso.")
        configuracao = ConfiguracaoSistema.load()
        serializer = self.get_serializer(configuracao, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return resposta_sucesso(message="Configurações atualizadas com sucesso")
