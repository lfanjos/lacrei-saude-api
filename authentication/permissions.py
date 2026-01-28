"""
Permissões personalizadas para Autenticação - Lacrei Saúde API
==============================================================
"""

from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permissão para permitir acesso apenas ao próprio usuário ou admins
    """

    def has_object_permission(self, request, view, obj):
        # Admins e superusers podem acessar tudo
        if request.user.is_superuser or request.user.is_admin:
            return True
        
        # Usuários podem acessar apenas seus próprios dados
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Para modelos User
        if hasattr(obj, 'id'):
            return obj.id == request.user.id
            
        return False


class IsProfissionalOrAdmin(permissions.BasePermission):
    """
    Permissão para profissionais e admins
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_profissional or request.user.is_admin or request.user.is_superuser)
        )


class IsOwnerProfissionalOrAdmin(permissions.BasePermission):
    """
    Permissão para o profissional responsável, proprietário ou admin
    """

    def has_object_permission(self, request, view, obj):
        # Admins sempre podem acessar
        if request.user.is_superuser or request.user.is_admin:
            return True
        
        # Profissional responsável pela consulta
        if hasattr(obj, 'profissional') and obj.profissional:
            if (request.user.is_profissional and 
                request.user.profissional == obj.profissional):
                return True
        
        # Proprietário do objeto (para usuários/pacientes)
        if hasattr(obj, 'user'):
            return obj.user == request.user
            
        return False


class IsVerifiedUser(permissions.BasePermission):
    """
    Permissão apenas para usuários verificados
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_verified or request.user.is_admin or request.user.is_superuser)
        )


class CanManageUsers(permissions.BasePermission):
    """
    Permissão para gerenciar usuários (admins e staff autorizado)
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_admin or request.user.is_superuser or 
             (request.user.is_staff and request.user.user_type == 'STAFF'))
        )


class ReadOnlyOrOwner(permissions.BasePermission):
    """
    Permissão de leitura para todos, escrita apenas para o proprietário
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Leitura permitida para usuários autenticados
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Escrita apenas para o proprietário ou admins
        if request.user.is_admin or request.user.is_superuser:
            return True
            
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user


class APIKeyPermission(permissions.BasePermission):
    """
    Permissão baseada em API Key com permissões específicas
    """

    def has_permission(self, request, view):
        # Se não é autenticação por API Key, usar permissões padrão
        if not hasattr(request, 'auth') or not hasattr(request.auth, 'permissions'):
            return True
        
        api_key = request.auth
        endpoint = f"{request.method.lower()}:{view.get_view_name().lower()}"
        
        # Verificar se a API Key tem permissão para este endpoint
        allowed_endpoints = api_key.permissions.get('endpoints', [])
        
        if '*' in allowed_endpoints:
            return True
            
        return endpoint in allowed_endpoints


class ThrottlePermission(permissions.BasePermission):
    """
    Permissão que considera rate limiting por tipo de usuário
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Rate limiting será aplicado pelo middleware
        
        # Admins têm rate limits mais altos
        if request.user.is_admin or request.user.is_superuser:
            return True
            
        # Rate limiting específico será aplicado pelo middleware
        return True