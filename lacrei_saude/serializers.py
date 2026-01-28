"""
Serializers base para Lacrei Saúde API
======================================
"""

from rest_framework import serializers
from django.utils import timezone


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Serializer base com campos comuns
    """
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        abstract = True
        fields = ['id', 'created_at', 'updated_at', 'is_active']


class TimestampsMixin:
    """
    Mixin para adicionar formatação de timestamps
    """
    def to_representation(self, instance):
        """Customizar representação dos timestamps"""
        data = super().to_representation(instance)
        
        # Formatar datas em português brasileiro
        if 'created_at' in data and data['created_at']:
            created_at = timezone.datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            data['created_at_formatted'] = created_at.strftime('%d/%m/%Y às %H:%M')
        
        if 'updated_at' in data and data['updated_at']:
            updated_at = timezone.datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            data['updated_at_formatted'] = updated_at.strftime('%d/%m/%Y às %H:%M')
        
        return data


class ValidationMixin:
    """
    Mixin para validações comuns
    """
    def validate_telefone(self, value):
        """Validação personalizada para telefone"""
        if value:
            # Remove espaços e caracteres especiais para validação
            digits = ''.join(filter(str.isdigit, value))
            if len(digits) < 10 or len(digits) > 11:
                raise serializers.ValidationError(
                    "Telefone deve ter 10 ou 11 dígitos (incluindo DDD)"
                )
        return value
    
    def validate_cep(self, value):
        """Validação personalizada para CEP"""
        if value:
            digits = ''.join(filter(str.isdigit, value))
            if len(digits) != 8:
                raise serializers.ValidationError(
                    "CEP deve ter 8 dígitos"
                )
        return value


class ReadOnlySerializer(serializers.ModelSerializer):
    """
    Serializer para endpoints read-only (listagem e detalhes)
    """
    class Meta:
        abstract = True
    
    def create(self, validated_data):
        raise serializers.ValidationError("Criação não permitida neste endpoint")
    
    def update(self, instance, validated_data):
        raise serializers.ValidationError("Atualização não permitida neste endpoint")