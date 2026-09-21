import uuid

from django.conf import settings
from django.db import models


class ModeloUUIDComTimestamps(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_actualizacao = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_criados",
        editable=False,
    )

    class Meta:
        abstract = True

class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True)

    def alive(self):
        return self.filter(is_deleted=False)
    


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
