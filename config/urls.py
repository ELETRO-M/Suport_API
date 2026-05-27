from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.usuarios.views import (
    AutenticacaoViewSet,
    PerfilViewSet, 
    TecnicoViewSet, 
    RecuperarConta, 
    reset_password_confirm, 
    empresaviewset
)
from apps.contratos.views import ContratoViewSet
from apps.clientes.views import ClienteViewSet
from apps.intervencoes.views import  IntervencaoViewSet, HistoricoViewSet
from apps.notificacoes.views import NotificacaoViewSet
from apps.relatorios.views import RelatorioViewSet
from apps.sistema.views import ConfiguracaoSistemaViewSet


router = DefaultRouter()
router.register(r"auth", AutenticacaoViewSet, basename="auth")
router.register(r"clientes", ClienteViewSet, basename="clientes")
router.register(r"contratos", ContratoViewSet, basename="contratos")
router.register(r"intervencoes", IntervencaoViewSet, basename="intervencoes")
router.register(r"intervencoes-historicos", HistoricoViewSet, basename="historico")
router.register(r"tecnicos", TecnicoViewSet, basename="tecnicos")
router.register(r"relatorios", RelatorioViewSet, basename="relatorios")
router.register(r"notificacoes", NotificacaoViewSet, basename="notificacoes")
router.register(r"recuperar", RecuperarConta, basename="recuperar")
router.register(r'reset-password', reset_password_confirm, basename='restpassword' )
router.register(r"empresas", empresaviewset, basename="empresas")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/configuracoes", ConfiguracaoSistemaViewSet.as_view({"get": "list", "put": "update"}), name="configuracoes"),
    path("api/v1/perfil", PerfilViewSet.as_view({"get": "list", "put": "update"}), name="perfil"),
    path("api/v1/perfil/password", PerfilViewSet.as_view({"put": "password"}), name="perfil-password"),
    path("api/v1/", include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
