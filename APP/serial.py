from rest_framework import serializers
from .models import login

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = login
        fields = [
            'id',
            'username', 
            'email',
            'empresa', 
            'perfil',
            'contact', 
            'password', 
            'create_data',
            'update_data'
          ]
          #Para Nao imprimir as senhas ou hash dos user.
          #obs neste momento estou a dixa as hash das senhas visiveis,
          # para facilitar os testes, mas depois vou retirar isso.
          #caso deseje deixa nao visivel, basta passar o write_only para true, e o campo password nao sera impresso.
        extra_kwargs = {'password': {'write_only': False}}
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

