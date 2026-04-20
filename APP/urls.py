from rest_framework.routers import DefaultRouter
from .views import UserViewSet, LoginViewSet, ClienteViewSet
router = DefaultRouter()
router.register(r'auth/register', UserViewSet, basename='user')
router.register(r'auth/login', LoginViewSet, basename='login')
router.register(r'clientes', ClienteViewSet, basename='clientes')

