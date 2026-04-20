from rest_framework.routers import DefaultRouter
<<<<<<< HEAD
<<<<<<< HEAD
from .views import UserViewSet, LoginViewSet
router = DefaultRouter()
router.register(r'register', UserViewSet, basename='user')
router.register(r'login', LoginViewSet, basename='login')
=======
from .views import UserViewSet, LoginViewSet, ClientesViewSet
router = DefaultRouter()
router.register(r'auth/register', UserViewSet, basename='user')
router.register(r'auth/login', LoginViewSet, basename='login')
router.register(r'clientes', ClientesViewSet, basename='clientes')
>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)
=======
from .views import UserViewSet, LoginViewSet, ClienteViewSet
router = DefaultRouter()
router.register(r'auth/register', UserViewSet, basename='user')
router.register(r'auth/login', LoginViewSet, basename='login')
router.register(r'clientes', ClienteViewSet, basename='clientes')
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf

