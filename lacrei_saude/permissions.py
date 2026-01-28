"""
Permissions customizadas para Lacrei Saúde API
===============================================
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permissão customizada que permite apenas proprietários editarem o objeto.
    """

    def has_object_permission(self, request, view, obj):
        # Permissões de leitura são permitidas para qualquer request,
        # portanto sempre permitiremos requests GET, HEAD ou OPTIONS.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Permissões de escrita são apenas permitidas ao proprietário do objeto.
        # Para modelos que não têm campo 'owner', permitir para usuários autenticados
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Para objetos sem proprietário específico, permitir para usuários autenticados
        return request.user.is_authenticated


class IsAuthenticatedOrReadOnlyForSafeObjects(permissions.BasePermission):
    """
    Permissão que permite leitura para todos e escrita apenas para usuários autenticados
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated


class IsProfissionalOrReadOnly(permissions.BasePermission):
    """
    Permissão específica para profissionais - apenas o próprio profissional pode editar
    """

    def has_object_permission(self, request, view, obj):
        # Leitura para todos os usuários autenticados
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Escrita apenas para o próprio profissional
        # Assumindo que existe um relacionamento user no modelo Profissional
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Se não há relacionamento com user, permitir para usuários autenticados
        return request.user.is_authenticated


class CanManageConsultas(permissions.BasePermission):
    """
    Permissão para gerenciar consultas
    """

    def has_permission(self, request, view):
        # Usuário deve estar autenticado
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Leitura para usuários autenticados
        if request.method in permissions.SAFE_METHODS:
            return True

        # Para consultas, permitir edição para:
        # 1. Profissional responsável pela consulta
        # 2. Staff/admin
        if hasattr(obj, 'profissional') and hasattr(obj.profissional, 'user'):
            if obj.profissional.user == request.user:
                return True

        # Staff pode editar tudo
        return request.user.is_staff


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Permissão que permite leitura para usuários autenticados e escrita apenas para staff
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permissão que permite leitura para usuários autenticados e escrita apenas para admins
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_superuser