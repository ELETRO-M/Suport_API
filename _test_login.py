import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '.')
django.setup()
from apps.usuarios.models import Usuario
from django.contrib.auth import authenticate

email = sys.argv[1]
pw = sys.argv[2]

user = Usuario.objects.filter(email=email).first()
if not user:
    print('ERRO: User nao encontrado')
    sys.exit(1)

user.set_password(pw)
try:
    user.save()
    print('Password alterada com sucesso')
except Exception as e:
    print('ERRO ao salvar:', e)
    sys.exit(1)

auth = authenticate(username=email, password=pw)
print('Login com nova password:', 'OK' if auth else 'FALHOU')
