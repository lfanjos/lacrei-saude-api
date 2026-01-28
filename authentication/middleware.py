"""
Middleware de Autenticação - Lacrei Saúde API
=============================================
"""

import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from .models import APIKey, LoginAttempt

logger = logging.getLogger(__name__)


class APIKeyAuthentication:
    """
    Autenticação via API Key
    """

    def authenticate(self, request):
        """
        Autenticar usando API Key no header
        """
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            return None

        try:
            key_obj = APIKey.objects.select_related("user").get(key=api_key, is_active=True)

            # Atualizar último uso
            key_obj.last_used = timezone.now()
            key_obj.save(update_fields=["last_used"])

            return (key_obj.user, key_obj)

        except APIKey.DoesNotExist:
            return None

    def authenticate_header(self, request):
        return "X-API-Key"


class SecurityMiddleware:
    """
    Middleware para logs de segurança e controle de acesso
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log da requisição
        self.log_request(request)

        # Verificar tentativas de login suspeitas
        if request.path in ["/api/auth/login/", "/api/auth/token/"]:
            self.check_login_attempts(request)

        response = self.get_response(request)

        # Log da resposta
        self.log_response(request, response)

        return response

    def log_request(self, request):
        """
        Registrar informações da requisição para auditoria
        """
        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {self.get_client_ip(request)} "
            f"User: {getattr(request.user, 'email', 'Anonymous')}"
        )

    def log_response(self, request, response):
        """
        Registrar informações da resposta
        """
        if response.status_code >= 400:
            logger.warning(
                f"Error Response: {response.status_code} for "
                f"{request.method} {request.path} "
                f"from {self.get_client_ip(request)}"
            )

    def check_login_attempts(self, request):
        """
        Verificar tentativas de login suspeitas
        """
        ip_address = self.get_client_ip(request)

        # Verificar tentativas recentes falhas do IP
        recent_failures = LoginAttempt.objects.filter(
            ip_address=ip_address, success=False, created_at__gte=timezone.now() - timezone.timedelta(minutes=15)
        ).count()

        if recent_failures >= 5:
            logger.warning(f"Multiple failed login attempts from {ip_address} " f"({recent_failures} in last 15 minutes)")

    def get_client_ip(self, request):
        """
        Obter IP real do cliente considerando proxies
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class JWTAuthenticationMiddleware:
    """
    Middleware para autenticação JWT automática
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        # Tentar autenticar automaticamente via JWT
        if not hasattr(request, "user") or isinstance(request.user, AnonymousUser):
            auth_result = self.authenticate_jwt(request)
            if auth_result:
                user, token = auth_result
                request.user = user
                request.auth = token

        response = self.get_response(request)
        return response

    def authenticate_jwt(self, request):
        """
        Tentar autenticar via JWT
        """
        try:
            return self.jwt_auth.authenticate(request)
        except (InvalidToken, TokenError):
            return None
        except Exception as e:
            logger.error(f"JWT Authentication error: {e}")
            return None


class RateLimitMiddleware:
    """
    Middleware para rate limiting customizado
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            "/api/auth/login/": (5, 300),  # 5 tentativas por 5 minutos
            "/api/auth/register/": (3, 300),  # 3 tentativas por 5 minutos
            "/api/": (100, 60),  # 100 requests por minuto para API geral
        }

    def __call__(self, request):
        # Verificar rate limits
        if self.is_rate_limited(request):
            from django.http import JsonResponse

            return JsonResponse({"error": "Rate limit exceeded", "detail": "Too many requests. Try again later."}, status=429)

        response = self.get_response(request)
        return response

    def is_rate_limited(self, request):
        """
        Verificar se a requisição excede o rate limit
        """
        # Implementação básica - em produção usar Redis
        # Por agora, apenas log
        path = request.path
        for rate_path, (limit, window) in self.rate_limits.items():
            if path.startswith(rate_path):
                logger.info(f"Rate limit check for {path}: {limit}/{window}s")
                break

        return False  # Não bloquear por enquanto
