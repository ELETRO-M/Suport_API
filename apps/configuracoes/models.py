import uuid

from django.db import models


class ModeloUUIDComTimestamps(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_actualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
