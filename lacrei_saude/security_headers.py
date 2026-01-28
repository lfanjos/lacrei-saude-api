"""
Middleware para Headers de Segurança - Lacrei Saúde API
======================================================
"""

import hashlib
import secrets
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para adicionar headers de segurança avançados
    """
    
    def process_response(self, request, response):
        """
        Adiciona headers de segurança à resposta
        """
        # Content Security Policy (CSP)
        csp_directives = self._get_csp_directives(request)
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Headers de segurança básicos
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'cross-origin'
        
        # Permissions Policy (Feature Policy)
        permissions_policy = self._get_permissions_policy()
        response['Permissions-Policy'] = permissions_policy
        
        # Cache Control para endpoints da API
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Headers específicos para produção
        if not settings.DEBUG:
            # HSTS (HTTP Strict Transport Security)
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            
            # Expect-CT
            response['Expect-CT'] = 'max-age=86400, enforce'
        
        # Headers personalizados da API
        response['X-API-Version'] = '1.0'
        response['X-Powered-By'] = 'Lacrei Saúde API'
        
        return response
    
    def _get_csp_directives(self, request):
        """
        Gera as diretivas do Content Security Policy
        """
        # Nonce para scripts inline (se necessário)
        nonce = self._generate_nonce()
        request.csp_nonce = nonce
        
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-eval'",  # unsafe-eval para Django Debug Toolbar
            "style-src 'self' 'unsafe-inline'",  # Necessário para estilos inline do DRF
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests",
        ]
        
        # Ajustes para desenvolvimento
        if settings.DEBUG:
            # Permitir WebSocket para live reload
            directives.append("connect-src 'self' ws: wss:")
            # Permitir localhost para desenvolvimento
            directives = [d.replace("'self'", "'self' localhost:* 127.0.0.1:*") for d in directives]
        else:
            # CSP mais restritivo para produção
            directives.extend([
                "report-uri /api/security/csp-report/",
                "report-to csp-endpoint"
            ])
        
        return directives
    
    def _get_permissions_policy(self):
        """
        Gera a Permissions Policy
        """
        policies = [
            'geolocation=()',
            'microphone=()',
            'camera=()', 
            'midi=()',
            'encrypted-media=()',
            'fullscreen=()',
            'payment=()',
            'usb=()',
            'serial=()',
            'bluetooth=()',
            'magnetometer=()',
            'gyroscope=()',
            'accelerometer=()',
            'ambient-light-sensor=()',
        ]
        
        return ', '.join(policies)
    
    def _generate_nonce(self):
        """
        Gera um nonce para CSP
        """
        return secrets.token_urlsafe(16)


class CORSSecurityMiddleware(MiddlewareMixin):
    """
    Middleware para CORS com validações de segurança adicionais
    """
    
    def process_request(self, request):
        """
        Valida requisições CORS
        """
        origin = request.META.get('HTTP_ORIGIN')
        
        if origin:
            # Log de origens para monitoramento
            if not self._is_allowed_origin(origin):
                import logging
                logger = logging.getLogger('security')
                logger.warning(f"Blocked CORS request from origin: {origin}")
        
        return None
    
    def process_response(self, request, response):
        """
        Adiciona headers CORS com validações de segurança
        """
        origin = request.META.get('HTTP_ORIGIN')
        
        if origin and self._is_allowed_origin(origin):
            # Headers CORS seguros
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
            
            # Expor headers customizados para o frontend
            response['Access-Control-Expose-Headers'] = 'X-API-Version, X-RateLimit-Remaining'
        
        return response
    
    def _is_allowed_origin(self, origin):
        """
        Verifica se a origem é permitida
        """
        import re
        
        # Verificar origins exatas
        if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
            if origin in settings.CORS_ALLOWED_ORIGINS:
                return True
        
        # Verificar regex patterns
        if hasattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES'):
            for pattern in settings.CORS_ALLOWED_ORIGIN_REGEXES:
                if re.match(pattern, origin):
                    return True
        
        return False


class APISecurityMiddleware(MiddlewareMixin):
    """
    Middleware específico para segurança da API
    """
    
    def process_request(self, request):
        """
        Validações específicas para endpoints da API
        """
        if request.path.startswith('/api/'):
            # Validar Content-Type para métodos POST/PUT/PATCH
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.META.get('CONTENT_TYPE', '')
                if not content_type.startswith('application/json'):
                    import logging
                    logger = logging.getLogger('security')
                    logger.warning(f"Invalid Content-Type for API request: {content_type}")
            
            # Validar User-Agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            if self._is_suspicious_user_agent(user_agent):
                import logging
                logger = logging.getLogger('security')
                logger.warning(f"Suspicious User-Agent: {user_agent}")
        
        return None
    
    def process_response(self, request, response):
        """
        Headers específicos para API
        """
        if request.path.startswith('/api/'):
            # Prevenir caching de respostas da API
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            
            # Informações da API
            response['X-API-Version'] = '1.0'
            response['X-Framework'] = 'Django REST Framework'
            
            # Rate limiting info (se disponível)
            if hasattr(request, 'rate_limit_remaining'):
                response['X-RateLimit-Remaining'] = str(request.rate_limit_remaining)
        
        return response
    
    def _is_suspicious_user_agent(self, user_agent):
        """
        Detecta User-Agents suspeitos
        """
        suspicious_patterns = [
            'sqlmap',
            'nmap',
            'burp',
            'nikto',
            'wget',
            'curl',  # Pode ser removido se curl for usado legitimamente
            'python-requests',
            'bot',
            'crawler',
            'spider',
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)