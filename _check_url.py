import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '.')
django.setup()
from apps.intervencoes.models import AnexoIntervencao
from apps.usuarios.models import Usuario

tec = Usuario.objects.filter(perfil='tecnico').first()
admin = Usuario.objects.filter(perfil='admin').first()
print('Tecnico: {} | perfil={} | is_staff={}'.format(tec.email, tec.perfil, tec.is_staff))
print('Admin:   {} | perfil={} | is_staff={}'.format(admin.email, admin.perfil, admin.is_staff))
print()

anexo = AnexoIntervencao.objects.filter(arquivo_marcado_url__gt='').first()
if anexo:
    url_tec = anexo.url_para(tec)
    url_admin = anexo.url_para(admin)
    print('=== URL para TECNICO ===')
    print(url_tec)
    print()
    print('=== URL para ADMIN ===')
    print(url_admin)
    print()
    same = 'SIM' if url_tec == url_admin else 'NAO'
    print('MESMA URL? ' + same)
    from urllib.parse import urlparse
    print('Tecnico path: ' + urlparse(url_tec).path)
    print('Admin path:   ' + urlparse(url_admin).path)
else:
    print('Nenhum anexo com arquivo_marcado_url')
