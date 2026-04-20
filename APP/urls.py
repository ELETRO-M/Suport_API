from rest_framework.routers import DefaultRouter
from .views import UserViewSet, LoginViewSet
router = DefaultRouter()
router.register(r'register', UserViewSet, basename='user')
router.register(r'login', LoginViewSet, basename='login')

