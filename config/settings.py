from datetime import timedelta
from pathlib import Path
import dj_database_url, os

from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*").split(",") 

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "apps.configuracoes",
    "apps.usuarios",
    "apps.clientes",
    "apps.contratos",
    "apps.intervencoes",
    "apps.relatorios",
    "apps.notificacoes",
    "apps.sistema",
    
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", 
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {
      "default": dj_database_url.config(default='sqlite:///db.sqlite3')
}




AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "pt-pt"
TIME_ZONE = "Africa/Luanda"
USE_I18N = True
USE_TZ = True
SITE_URL = config("DOMAIN_URL", default="http://localhost:8000")
STATICFILES_DIRS = []

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "usuarios.Usuario"
APPEND_SLASH = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.configuracoes.pagination.PaginacaoPadraoResultados",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.configuracoes.exceptions.manipulador_excecao_personalizado",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(config("ACCESS_TOKEN_LIFETIME_MINUTES"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(config("REFRESH_TOKEN_LIFETIME_DAYS"))),
    "PASSWORD_RESET_TIMEOUT": 900,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Suporte API",
    "DESCRIPTION": "API de gestão.",
    "VERSION": "1.0.0",
    "SWAGGER_UI_FAVICON_HREF": "data:,",
    'SERVERS': [
        {'url': config("DOMAIN_URL", default="http://localhost:8000")},
    ]
}
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    EMAIL_HOST = config("EMAIL_HOST")
    EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
    EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)
    EMAIL_USE_SSL = config("EMAIL_USE_SSL", cast=bool, default=False)
    EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", cast=int, default=30)

    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default=config("EMAIL_EMPRESA", default=""))
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default=config("PASSWORD_EMAIL", default=""))
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
