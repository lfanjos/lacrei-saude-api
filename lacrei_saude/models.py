"""
Modelos base para Lacrei Saúde API
==================================
"""

import uuid

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Modelo base abstrato com campos de auditoria
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="Identificador único universal")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Data e hora de criação")
    updated_at = models.DateTimeField(auto_now=True, help_text="Data e hora da última atualização")
    is_active = models.BooleanField(default=True, help_text="Indica se o registro está ativo")

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self):
        """Exclusão lógica do registro"""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def restore(self):
        """Restaurar registro excluído logicamente"""
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])


class ActiveManager(models.Manager):
    """Manager personalizado para filtrar apenas registros ativos"""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class BaseModelWithManager(BaseModel):
    """
    Modelo base com managers personalizados
    """

    objects = models.Manager()  # Manager padrão
    active = ActiveManager()  # Manager para registros ativos

    class Meta:
        abstract = True
