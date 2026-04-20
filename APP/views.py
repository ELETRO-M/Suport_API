from django.shortcuts import render
from rest_framework import viewsets,mixins,status
<<<<<<< HEAD
<<<<<<< HEAD
from .models import login 
from .serial import UserSerializer, LoginSerializer
=======
from .models import login, Cleintes
from .serial import UserSerializer, LoginSerializer, ClientesSerializer
>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)
=======
from .models import login, Cleintes
from .serial import UserSerializer, LoginSerializer, ClienteSerializer
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth import get_user_model, authenticate
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

class numberPage(PageNumberPagination):
        page_size_query_param = 'page_size'
        page_size = 100
        max_page_size = 100

#rota registro
#auth/register/
#auth/register/ - POST
"""
{
"username":"",
"email": ",
"password":,
"empresa",
"perfil":{admin, cliente,tecnico},
"conctact":opcional
}
"""
#auth/register/?email={email} $?id={id} - GET id ou email 
#auth/login/{id} - Delete

class UserViewSet(viewsets.ModelViewSet):
    queryset = login.objects.all()
    serializer_class = UserSerializer
<<<<<<< HEAD
<<<<<<< HEAD
    
    permission_classes = [IsAuthenticated]  # Permitir acesso sem autenticação para registro
    
=======
    permission_classes = [IsAuthenticated]
    ordering_fields = ['create_data']
    ordering= ['create_data'] 
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()  # pega o objeto pelo ID
        instance.delete()             # apaga do banco
        
        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
    ) 
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf


    def get_queryset(self):
        # Retorna um queryset vazio para evitar acesso a outros usuários
        
        queryset = login.objects.all()
        email = self.request.query_params.get('email')

<<<<<<< HEAD
=======
    permission_classes = [IsAuthenticated]  # Permitir acesso sem autenticação para registro
    
class ClientesViewSet(viewsets.ModelViewSet):
    queryset = Cleintes.objects.all()
    serializer_class = ClientesSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)
=======
        if email:
            queryset = queryset.filter(email=email)
        

        return queryset
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf
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
#admin senha123
        }, status=status.HTTP_200_OK)
class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cleintes.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]  
    pagination_class = numberPage
    ordering_fields = ['create_data']
    ordering= ['create_data']