# Configurações VAPID para Web Push no Django
#
# COPIE este ficheiro para config/vapid_keys.py e preencha com as suas chaves.
# O ficheiro config/vapid_keys.py NÃO vai para o git (contém a chave privada).
#
# Gerar chaves com: python -c "
# from cryptography.hazmat.primitives.asymmetric import ec
# from cryptography.hazmat.primitives import serialization
# private_key = ec.generate_private_key(ec.SECP256R1())
# private_pem = private_key.private_bytes(
#     encoding=serialization.Encoding.PEM,
#     format=serialization.PrivateFormat.PKCS8,
#     encryption_algorithm=serialization.NoEncryption(),
# )
# public_key = private_key.public_key()
# public_pem = public_key.public_bytes(
#     encoding=serialization.Encoding.PEM,
#     format=serialization.PublicFormat.SubjectPublicKeyInfo,
# )
# print('VAPID_PRIVATE_KEY =', repr(private_pem.decode()))
# print('VAPID_PUBLIC_KEY =', repr(public_pem.decode()))
# "

VAPID_PRIVATE_KEY = '-----BEGIN PRIVATE KEY-----\nSUBSTITUA-PELA-CHAVE-PRIVADA\n-----END PRIVATE KEY-----\n'

VAPID_PUBLIC_KEY = '-----BEGIN PUBLIC KEY-----\nSUBSTITUA-PELA-CHAVE-PUBLICA\n-----END PUBLIC KEY-----\n'

VAPID_ADMIN_EMAIL = 'admin@exemplo.com'

# Em produção, defina também via environment variables:
#   set VAPID_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
#   set VAPID_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
