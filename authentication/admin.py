"""
Admin para Autenticação - Lacrei Saúde API
==========================================
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import APIKey, LoginAttempt, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin customizado para User
    """

    list_display = ["email", "username", "user_type", "is_verified", "is_active", "is_staff", "date_joined"]
    list_filter = ["user_type", "is_verified", "is_active", "is_staff", "is_superuser", "date_joined"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Informações Adicionais", {"fields": ("user_type", "is_verified", "phone_number", "profissional")}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Informações Adicionais", {"fields": ("email", "user_type", "phone_number")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profissional")


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """
    Admin para API Keys
    """

    list_display = ["name", "user", "key_preview", "is_active", "last_used", "created_at"]
    list_filter = ["is_active", "created_at", "last_used"]
    search_fields = ["name", "user__email", "user__username"]
    readonly_fields = ["key", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def key_preview(self, obj):
        """Mostrar preview da chave"""
        if obj.key:
            return f"{obj.key[:8]}...{obj.key[-4:]}"
        return "-"

    key_preview.short_description = "Chave (Preview)"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """
    Admin para tentativas de login
    """

    list_display = ["email", "ip_address", "success_icon", "created_at", "failure_reason"]
    list_filter = ["success", "created_at"]
    search_fields = ["email", "ip_address"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def success_icon(self, obj):
        """Ícone para sucesso/falha"""
        if obj.success:
            return format_html('<span style="color: green;">✓ Sucesso</span>')
        else:
            return format_html('<span style="color: red;">✗ Falha</span>')

    success_icon.short_description = "Status"

    def has_add_permission(self, request):
        """Não permitir adicionar tentativas manualmente"""
        return False

    def has_change_permission(self, request, obj=None):
        """Não permitir editar tentativas"""
        return False
