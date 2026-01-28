"""
Serializers de Autenticação - Lacrei Saúde API
==============================================
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, APIKey


class LoginSerializer(TokenObtainPairSerializer):
    """
    Serializer customizado para login
    """
    username_field = 'email'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        self.fields['password'] = serializers.CharField()
        # Remover campo username padrão
        if 'username' in self.fields:
            del self.fields['username']

    def validate(self, attrs):
        """
        Validar credenciais usando email
        """
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Usar email como username
            attrs['username'] = email
            
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para User (leitura)
    """
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    profissional_info = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'user_type_display', 'is_verified', 'phone_number',
            'is_active', 'date_joined', 'last_login', 'profissional_info'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_profissional_info(self, obj):
        """
        Incluir informações do profissional se existir
        """
        if obj.profissional:
            return {
                'id': str(obj.profissional.id),
                'nome_social': obj.profissional.nome_social,
                'profissao': obj.profissional.get_profissao_display()
            }
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de usuários
    """
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'user_type', 'phone_number'
        ]

    def validate_email(self, value):
        """
        Validar email único
        """
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("Este email já está em uso")
        return value.lower()

    def validate_username(self, value):
        """
        Validar username único
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este username já está em uso")
        return value

    def validate_password(self, value):
        """
        Validar senha usando validadores do Django
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        """
        Validar confirmação de senha
        """
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'As senhas não coincidem'
            })
        return data

    def create(self, validated_data):
        """
        Criar usuário com senha criptografada
        """
        # Remover campo de confirmação
        validated_data.pop('password_confirm')
        
        # Criar usuário
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para mudança de senha
    """
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()

    def validate_new_password(self, value):
        """
        Validar nova senha
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        """
        Validar confirmação da nova senha
        """
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'As senhas não coincidem'
            })
        return data


class APIKeySerializer(serializers.ModelSerializer):
    """
    Serializer para API Keys
    """
    plain_key = serializers.CharField(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'plain_key', 'user_email', 'is_active',
            'last_used', 'created_at', 'permissions'
        ]
        read_only_fields = ['id', 'plain_key', 'last_used', 'created_at']

    def validate_name(self, value):
        """
        Validar nome único por usuário
        """
        user = self.context['request'].user
        if APIKey.objects.filter(user=user, name=value, is_active=True).exists():
            raise serializers.ValidationError("Você já tem uma API Key com este nome")
        return value

    def to_representation(self, instance):
        """
        Customizar saída para mostrar chave apenas na criação
        """
        data = super().to_representation(instance)
        
        # Mostrar chave completa apenas se foi acabou de ser criada
        if hasattr(instance, 'plain_key'):
            data['key'] = instance.plain_key
        else:
            # Mostrar apenas parte da chave para segurança
            data['key_preview'] = f"{instance.key[:8]}...{instance.key[-4:]}"
            
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para perfil do usuário (dados editáveis)
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number'
        ]

    def update(self, instance, validated_data):
        """
        Atualizar apenas campos permitidos
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance