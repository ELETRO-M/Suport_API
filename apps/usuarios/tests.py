from rest_framework.test import APITestCase
from rest_framework import status
from apps.usuarios.models import Usuario

class UsuariosAPITest(APITestCase):
    def setUp(self):
        # Este método roda antes de cada teste.
        # Aqui nós criamos um usuário falso no banco de dados "de teste"
        self.usuario_teste = Usuario.objects.create_user(
            email="teste@exemplo.com",
            password="senhasegura123",
            first_name="Usuário",
            last_name="Teste"
        )
        
        # A URL de login que está no seu config/urls.py (usando o AutenticacaoViewSet)
        # Assumindo que a rota de login é /api/v1/auth/login
        self.url_login = '/api/v1/auth/login'

    def test_login_com_credenciais_corretas(self):
        """
        Testa se a API retorna sucesso ao fazer login com a senha correta
        """
        dados = {
            "email": "teste@exemplo.com",
            "password": "senhasegura123"
        }
        
        # Simulamos um POST na rota de login
        resposta = self.client.post(self.url_login, dados)
        
        # Verificamos se o status HTTP é 200 (OK)
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        
        # Verificamos se a API devolveu um token de acesso
        self.assertIn("access", resposta.data)

    def test_login_com_senha_errada(self):
        """
        Testa se a API bloqueia o login com a senha incorreta
        """
        dados = {
            "email": "teste@exemplo.com",
            "password": "senha_errada"
        }
        
        resposta = self.client.post(self.url_login, dados)
        
        # Esperamos que o status seja 401 Unauthorized
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)
