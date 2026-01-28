"""
Modelos de Autenticação - Lacrei Saúde API
==========================================
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from lacrei_saude.models import BaseModel


class User(AbstractUser):
    """
    Modelo de usuário customizado
    """

    USER_TYPES = [
        ("ADMIN", "Administrador"),
        ("PROFISSIONAL", "Profissional"),
        ("PACIENTE", "Paciente"),
        ("STAFF", "Funcionário"),
    ]

    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=15, choices=USER_TYPES, default="PACIENTE")
    is_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True)

    # Relacionamentos opcionais
    profissional = models.ForeignKey(
        "profissionais.Profissional", on_delete=models.SET_NULL, null=True, blank=True, related_name="user_account"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"

    @property
    def is_admin(self):
        return self.user_type == "ADMIN"

    @property
    def is_profissional(self):
        return self.user_type == "PROFISSIONAL"

    @property
    def is_paciente(self):
        return self.user_type == "PACIENTE"


class APIKey(BaseModel):
    """
    Modelo para API Keys
    """

    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    permissions = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if not self.key:
            import secrets

            self.key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        return f"{self.name} - {self.user.email}"


class LoginAttempt(BaseModel):
    """
    Modelo para controle de tentativas de login
    """

    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Tentativa de Login"
        verbose_name_plural = "Tentativas de Login"
        indexes = [
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]
