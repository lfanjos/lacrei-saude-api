"""
Views de Autenticação - Lacrei Saúde API
========================================
"""

import secrets
import hashlib
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from .models import User, APIKey, LoginAttempt
from .serializers import (
    UserSerializer, UserCreateSerializer, LoginSerializer,
    APIKeySerializer, ChangePasswordSerializer
)
from .permissions import IsOwnerOrAdmin


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View customizada para login com JWT
    """
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """
        Login com log de tentativas
        """
        email = request.data.get('email')
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Registrar tentativa de login
        login_attempt = LoginAttempt.objects.create(
            email=email or '',
            ip_address=ip_address,
            user_agent=user_agent,
            success=False
        )
        
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                # Login bem-sucedido
                login_attempt.success = True
                login_attempt.save()
                
                # Adicionar informações do usuário à resposta
                user = User.objects.get(email=email)
                response.data.update({
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'username': user.username,
                        'user_type': user.user_type,
                        'is_verified': user.is_verified
                    }
                })
            else:
                # Login falhou
                login_attempt.failure_reason = 'Invalid credentials'
                login_attempt.save()
            
            return response
            
        except Exception as e:
            login_attempt.failure_reason = str(e)
            login_attempt.save()
            raise

    def get_client_ip(self, request):
        """Obter IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    """
    Registro de novos usuários
    """
    serializer = UserCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            with transaction.atomic():
                user = serializer.save()
                
                # Gerar tokens JWT
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Usuário criado com sucesso',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({
                'error': 'Erro ao criar usuário',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Logout invalidando o refresh token
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'Logout realizado com sucesso'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Erro ao realizar logout',
            'details': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de usuários
    """
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filtrar usuários baseado em permissões
        """
        user = self.request.user
        
        if user.is_superuser or user.is_admin:
            return User.objects.filter(is_active=True)
        else:
            # Usuários comuns só veem a si mesmos
            return User.objects.filter(id=user.id, is_active=True)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Obter dados do usuário atual
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Alterar senha do usuário atual
        """
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Verificar senha atual
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    'error': 'Senha atual incorreta'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Definir nova senha
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                'message': 'Senha alterada com sucesso'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento de API Keys
    """
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Retornar apenas API Keys do usuário atual
        """
        return APIKey.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        """
        Criar nova API Key
        """
        # Gerar chave aleatória
        key = secrets.token_urlsafe(32)
        
        serializer.save(
            user=self.request.user,
            key=hashlib.sha256(key.encode()).hexdigest()
        )
        
        # Retornar a chave apenas uma vez
        instance = serializer.instance
        instance.plain_key = key  # Para mostrar apenas na criação

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revogar API Key
        """
        api_key = self.get_object()
        api_key.is_active = False
        api_key.save()
        
        return Response({
            'message': 'API Key revogada com sucesso'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def auth_status(request):
    """
    Verificar status de autenticação
    """
    return Response({
        'authenticated': True,
        'user': UserSerializer(request.user).data,
        'permissions': {
            'is_admin': request.user.is_admin,
            'is_profissional': request.user.is_profissional,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def security_stats(request):
    """
    Estatísticas de segurança (apenas para admins)
    """
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    stats = {
        'login_attempts_24h': LoginAttempt.objects.filter(
            created_at__gte=last_24h
        ).count(),
        'failed_logins_24h': LoginAttempt.objects.filter(
            created_at__gte=last_24h,
            success=False
        ).count(),
        'active_users': User.objects.filter(
            is_active=True,
            last_login__gte=last_7d
        ).count(),
        'total_api_keys': APIKey.objects.filter(is_active=True).count(),
    }
    
    return Response(stats)