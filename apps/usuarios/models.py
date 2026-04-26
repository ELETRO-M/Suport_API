from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.configuracoes.models import ModeloUUIDComTimestamps


class GestorUsuario(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O email é obrigatório.")
        email = self.normalize_email(email)
        utilizador = self.model(email=email, **extra_fields)
        utilizador.set_password(password)
        utilizador.save(using=self._db)
        return utilizador

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("perfil", Usuario.PerfilChoices.ADMIN)
        extra_fields.setdefault("status", Usuario.StatusChoices.ACTIVO)
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser, ModeloUUIDComTimestamps):
    class PerfilChoices(models.TextChoices):
        ADMIN = "admin", "Admin"
        TECNICO = "tecnico", "Técnico"
        CLIENTE = "cliente", "Cliente"

    class StatusChoices(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=255)
    perfil = models.CharField(max_length=20, choices=PerfilChoices.choices)
    telefone = models.CharField(max_length=50, blank=True)
    empresa = models.CharField(max_length=255, blank=True)
    nif = models.CharField(max_length=50, blank=True)
    endereco = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    preferencias = models.JSONField(default=dict, blank=True)
    especialidades = models.JSONField(default=list, blank=True)
    data_contratacao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    objects=GestorUsuario()

    def __str__(self):
        return f"{self.nome} <{self.email}>"

    @property
    def is_admin_role(self):
        return self.perfil == self.PerfilChoices.ADMIN

    @property
    def is_technician_role(self):
        return self.perfil == self.PerfilChoices.TECNICO

    @property
    def is_customer_role(self):
        return self.perfil == self.PerfilChoices.CLIENTE