from django.shortcuts import render
from rest_framework import viewsets,mixins,status
from .models import login 
from .serial import UserSerializer, LoginSerializer
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth import get_user_model, authenticate

#rota registro
class UserViewSet(viewsets.ModelViewSet):
    queryset = login.objects.all()
    serializer_class = UserSerializer
    
    permission_classes = [IsAuthenticated]  # Permitir acesso sem autenticação para registro
    



# ViewSet para login

class LoginViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        
        user = login.objects.filter(email=email).first()
        if user and user.check_password(password):
            user = authenticate(request, email=email, password=password)

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        refresh = RefreshToken.for_user(user) # Gerar token de atualização
        acess = AccessToken.for_user(user) # Gerar token de acesso
        data = UserSerializer(user).data
        return Response({
            "refresh": str(refresh),
            "access": str(acess),
            "user": data['id'],
            "username": data['username'],
            "email": data['email'], 
            "perfil": data['perfil']    

        }, status=status.HTTP_200_OK)