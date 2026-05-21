from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import models
from django.core.validators import MinLengthValidator

from apps.configuracoes.models import ModeloUUIDComTimestamps, SoftDeleteModel

class empresa(ModeloUUIDComTimestamps, SoftDeleteModel):
    Email_empresa = models.EmailField(unique=True)
    nome = models.CharField(max_length=255, unique=True)
    nif = models.CharField(max_length=50, unique=True)
    endereco = models.TextField()
    postos = models.JSONField(default=dict)
    telefone = models.CharField(max_length=50)
    avatar_url = models.URLField(blank=True)
    class StatusChoices(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)
    def clean(self):
        if not self.Email_empresa:
            raise ValidationError({
                "ERRO": "O email é obrigatório.",
                })
        if not self.nome:
            raise ValidationError({
                "ERRO": "O nome é obrigatório.",
                })
        if not self.nif:
            raise ValidationError({
                "ERRO": "O NIF é obrigatório.",
                })
        if not self.endereco:
            raise ValidationError({
                "ERRO": "O endereço é obrigatório.",
                })
        if not self.postos:
            raise ValidationError({
                "ERRO": "Os postos são obrigatórios.",
                })
        if not self.telefone:
            raise ValidationError({
                "ERRO": "O telefone é obrigatório.",
                })
        
       
    def __str__(self):
        return self.nome
    def save(self, *args, **kwargs):
        try:
            self.full_clean()
        except ValidationError as e:
            raise DRFValidationError(e.message_dict)
        super().save(*args, **kwargs)


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
    


        
    def get_queryset(self):
        return UsuarioQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return UsuarioQuerySet(self.model, using=self._db)

    def only_deleted(self):
        return self.all_with_deleted().deleted()

class UsuarioQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True)
    def hard_delete(self):
        return super().delete()     

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


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
    ip_servidor = models.CharField(max_length=50, validators=[MinLengthValidator(7)], blank=True)
    empresa = models.ForeignKey(
        empresa, 
        related_name="clientes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    nome = models.CharField(max_length=255)
    perfil = models.CharField(max_length=20, choices=PerfilChoices.choices)
    telefone = models.CharField(max_length=50, blank=True)
    postos = models.CharField(max_length=50, blank=True)
    avatar_url = models.URLField(blank=True)
    is_deleted=models.BooleanField(default=False)

    preferencias = models.JSONField(default=dict, blank=True)
    especialidades = models.JSONField(default=list, blank=True)
    data_contratacao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVO)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    objects=GestorUsuario()
    all_objects = UsuarioQuerySet.as_manager()
    def clean(self):
        if self.perfil == self.PerfilChoices.CLIENTE:
            if not self.empresa:
                raise ValidationError({
                    "empresa": "Obrigatório para clientes.",
                    })
        elif self.empresa_id:
            raise ValidationError({
                "empresa": "Apenas clientes podem estar associados a uma empresa.",
                })

        if self.perfil == self.PerfilChoices.TECNICO:
            if not self.especialidades:
                raise ValidationError({
                    "especialidades": "Obrigatório para técnicos.",
                    })
            if not self.data_contratacao:
                raise ValidationError({
                    "data_contratacao": "Obrigatório para técnicos.",
                    })
            if not self.telefone:
                raise ValidationError({
                    "telefone": "Obrigatório para técnicos.",
                    })
            

        if self.ip_servidor and self.empresa:
            postos_empresa = self.empresa.postos or {}
            ip_valido = False
            
            for posto_key, posto_info in postos_empresa.items():
                if isinstance(posto_info, dict) and posto_info.get("ip") == self.ip_servidor:
                    ip_valido = True
                    break
            
            if not ip_valido:
                raise ValidationError({
                    "ip_servidor": "O IP do servidor não corresponde a nenhum IP dos postos da empresa."
                })
#____________________________________________________________________________________
    def save(self, *args, **kwargs):
        try:
            self.full_clean()
        except ValidationError as e:
            raise DRFValidationError(e.message_dict)
        super().save(*args, **kwargs)

    def recuperar(self):
        self.is_deleted = False
        self.status = self.StatusChoices.ACTIVO
        type(self).all_objects.filter(pk=self.pk).update(
            is_deleted=False,
            status=self.StatusChoices.ACTIVO,
        )

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.status = self.StatusChoices.INACTIVO
        type(self).all_objects.filter(pk=self.pk).update(
            is_deleted=True,
            status=self.StatusChoices.INACTIVO,
        )
    def hard_delete(self):
        return super().delete()

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
