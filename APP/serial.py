from rest_framework import serializers
from .models import login, Cleintes

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
        extra_kwargs = {'password': {'write_only': True}}
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
<<<<<<< HEAD
<<<<<<< HEAD
=======
class ClientesSerializer(serializers.ModelSerializer):
=======
class ClienteSerializer(serializers.ModelSerializer):
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf
    class Meta:
        model = Cleintes
        fields = [
            'id',
            'name', 
<<<<<<< HEAD
            'email',
=======
            'email', 
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf
            'empresa', 
            'contact', 
            'nif', 
            'status', 
            'endereco', 
            'password', 
            'create_data',
            'update_data'
<<<<<<< HEAD
          ]
        extra_kwargs = {'password': {'write_only': True}}
>>>>>>> 89caac7 (V1.1 resolvido bugs da auth)
=======
        ]
        
        extra_kwargs = {'password': {'write_only': False}}
>>>>>>> 4cae4f7771cbd65b2b411e8784a5a1617224aebf

