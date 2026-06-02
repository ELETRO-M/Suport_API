from datetime import timedelta
from pathlib import Path
import os

from decouple import config
import dj_database_url
import cloudinary


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-suport-api-secret-key-clacs-2026-xjf9!")
DEBUG =config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="*",
    cast=lambda v: [item.strip() for item in v.split(",") if item.strip()],
) + ["suport-api-1.onrender.com", "localhost", "127.0.0.1"]
CORS_ALLOW_ALL_ORIGINS = True

SITE_URL = config("SITE_URL", default="http://localhost:8000")

INSTALLED_APPS = [
    "apps.configuracoes",
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
    "corsheaders",
    "cloudinary",
    "cloudinary_storage",
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
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"



WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=60,
        ssl_require=not DEBUG,
    )
}
BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "Templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",       # <-- resolve E402
                "django.contrib.messages.context_processors.messages", # <-- resolve E404
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
SITE_URL=config("SITE_URL",default="http://localhost:8000")
FIREBASE_CREDENTIALS_JSON = config("FIREBASE_CREDENTIALS_JSON", default="")
FIREBASE_CREDENTIALS_PATH = config("FIREBASE_CREDENTIALS_PATH", default="")
FIREBASE_PROJECT_ID = config("FIREBASE_PROJECT_ID", default="")

LANGUAGE_CODE = "pt-pt"
TIME_ZONE = "Africa/Luanda"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = config("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET")

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
}

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

_STATIC_BACKEND = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
   # if DEBUG
    #else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.RawMediaCloudinaryStorage"

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.RawMediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": _STATIC_BACKEND,
    },
}
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
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Suporte API",
    "DESCRIPTION": "API de gestão de suporte técnico.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_FAVICON_HREF": "",
    "ENUM_NAME_OVERRIDES": {
        "IntervecoesStatusEnum": "apps.intervencoes.models.Intervencao.StatusChoices",
        "IntervecoesPrioridadeEnum": "apps.intervencoes.models.Intervencao.PrioridadeChoices",
        "HoraTrabalhoTipoEnum": "apps.intervencoes.models.HoraTrabalho.TipoChoices",
        "ContratoStatusEnum": "apps.contratos.models.Contrato.StatusChoices",
        "ContratoTipoEnum": "apps.contratos.models.Contrato.Tipo_de_contratos",
        "ContratoPagamentoEnum": "apps.contratos.models.Contrato.TipoPagamento",
        "UsuarioStatusEnum": "apps.usuarios.models.Usuario.StatusChoices",
        "UsuarioPerfilEnum": "apps.usuarios.models.Usuario.PerfilChoices",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS",  cast=bool)
EMAIL_HOST_USER = config("EMAIL_EMPRESA")
EMAIL_HOST_PASSWORD = config("EMAIL_PASSWORD")
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_TIMEOUT = 10

CSRF_TRUSTED_ORIGINS = [
    "https://suportapi-production.up.railway.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]




LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
