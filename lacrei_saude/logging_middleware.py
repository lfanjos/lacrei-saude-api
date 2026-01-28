"""
Middleware para Logs - Lacrei Saúde API
======================================
"""

import json
import logging
import time
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

# Loggers específicos
access_logger = logging.getLogger('access')
security_logger = logging.getLogger('security')
audit_logger = logging.getLogger('audit')
error_logger = logging.getLogger('django.request')


class AccessLogMiddleware(MiddlewareMixin):
    """
    Middleware para logs detalhados de acesso
    """
    
    def process_request(self, request):
        """
        Registra informações da requisição
        """
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
        Registra logs de acesso detalhados
        """
        duration = time.time() - getattr(request, '_start_time', time.time())
        
        # Informações básicas do acesso
        log_data = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'referer': request.META.get('HTTP_REFERER', ''),
            'content_length': response.get('Content-Length', 0),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Informações do usuário
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            log_data['user_id'] = str(request.user.id)
            log_data['user_email'] = request.user.email
            log_data['user_type'] = getattr(request.user, 'user_type', 'unknown')
        else:
            log_data['user_id'] = 'anonymous'
        
        # Informações de autenticação
        if 'HTTP_AUTHORIZATION' in request.META:
            log_data['auth_type'] = 'jwt'
        elif 'HTTP_X_API_KEY' in request.META:
            log_data['auth_type'] = 'api_key'
        else:
            log_data['auth_type'] = 'none'
        
        # Query parameters (sem dados sensíveis)
        if request.GET:
            filtered_params = {}
            for key, value in request.GET.items():
                if key.lower() not in ['password', 'token', 'key', 'secret']:
                    filtered_params[key] = value
            log_data['query_params'] = filtered_params
        
        # Logs por tipo de endpoint
        if request.path.startswith('/api/'):
            self._log_api_access(log_data)
        elif request.path.startswith('/admin/'):
            self._log_admin_access(log_data)
        else:
            self._log_general_access(log_data)
        
        return response
    
    def _log_api_access(self, log_data):
        """
        Log específico para endpoints da API
        """
        message = (
            f"API {log_data['method']} {log_data['path']} "
            f"| Status: {log_data['status_code']} "
            f"| Duration: {log_data['duration_ms']}ms "
            f"| User: {log_data['user_id']} "
            f"| IP: {log_data['ip_address']} "
            f"| Auth: {log_data['auth_type']}"
        )
        access_logger.info(message)
    
    def _log_admin_access(self, log_data):
        """
        Log específico para acesso ao admin
        """
        message = (
            f"ADMIN {log_data['method']} {log_data['path']} "
            f"| Status: {log_data['status_code']} "
            f"| User: {log_data['user_id']} "
            f"| IP: {log_data['ip_address']}"
        )
        access_logger.info(message)
        
        # Auditoria para admin
        audit_logger.info(json.dumps({
            'event': 'admin_access',
            'data': log_data
        }))
    
    def _log_general_access(self, log_data):
        """
        Log geral para outros endpoints
        """
        message = (
            f"{log_data['method']} {log_data['path']} "
            f"| Status: {log_data['status_code']} "
            f"| Duration: {log_data['duration_ms']}ms "
            f"| IP: {log_data['ip_address']}"
        )
        access_logger.info(message)
    
    def _get_client_ip(self, request):
        """
        Obtém o IP real do cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ErrorLogMiddleware(MiddlewareMixin):
    """
    Middleware para capturar e logar erros detalhados
    """
    
    def process_exception(self, request, exception):
        """
        Registra erros detalhados
        """
        import traceback
        
        error_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'request_path': request.path,
            'request_method': request.method,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Log do erro
        error_message = (
            f"EXCEPTION {error_data['exception_type']}: {error_data['exception_message']} "
            f"| Path: {error_data['request_path']} "
            f"| Method: {error_data['request_method']} "
            f"| User: {error_data['user_id']} "
            f"| IP: {error_data['ip_address']}"
        )
        
        error_logger.error(error_message)
        
        # Auditoria do erro
        audit_logger.error(json.dumps({
            'event': 'application_error',
            'data': error_data
        }))
        
        return None
    
    def _get_client_ip(self, request):
        """
        Obtém o IP real do cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware para auditoria de operações críticas
    """
    
    # Operações que devem ser auditadas
    AUDIT_PATHS = [
        '/api/v1/profissionais/',
        '/api/v1/consultas/',
        '/api/auth/',
        '/admin/',
    ]
    
    AUDIT_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_request(self, request):
        """
        Registra início de operações críticas
        """
        if self._should_audit(request):
            audit_data = {
                'event': 'operation_start',
                'method': request.method,
                'path': request.path,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                'ip_address': self._get_client_ip(request),
                'timestamp': timezone.now().isoformat(),
                'request_data': self._get_request_data(request),
            }
            
            audit_logger.info(json.dumps(audit_data))
        
        return None
    
    def process_response(self, request, response):
        """
        Registra resultado de operações críticas
        """
        if self._should_audit(request) and request.method in self.AUDIT_METHODS:
            audit_data = {
                'event': 'operation_complete',
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                'ip_address': self._get_client_ip(request),
                'timestamp': timezone.now().isoformat(),
                'success': 200 <= response.status_code < 400,
            }
            
            # Para criações, tentar capturar ID do objeto criado
            if request.method == 'POST' and response.status_code == 201:
                try:
                    response_data = json.loads(response.content.decode('utf-8'))
                    if 'id' in response_data:
                        audit_data['created_object_id'] = response_data['id']
                except:
                    pass
            
            audit_logger.info(json.dumps(audit_data))
        
        return response
    
    def _should_audit(self, request):
        """
        Verifica se a requisição deve ser auditada
        """
        return any(request.path.startswith(path) for path in self.AUDIT_PATHS)
    
    def _get_request_data(self, request):
        """
        Captura dados da requisição (sem informações sensíveis)
        """
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                data = json.loads(request.body.decode('utf-8'))
                # Filtrar campos sensíveis
                sensitive_fields = ['password', 'token', 'secret', 'key']
                filtered_data = {}
                for key, value in data.items():
                    if key.lower() not in sensitive_fields:
                        if isinstance(value, dict):
                            # Filtrar recursivamente
                            filtered_value = {}
                            for k, v in value.items():
                                if k.lower() not in sensitive_fields:
                                    filtered_value[k] = v
                            filtered_data[key] = filtered_value
                        else:
                            filtered_data[key] = value
                return filtered_data
            except:
                return {}
        return {}
    
    def _get_client_ip(self, request):
        """
        Obtém o IP real do cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PerformanceLogMiddleware(MiddlewareMixin):
    """
    Middleware para monitoramento de performance
    """
    
    def process_request(self, request):
        """
        Marca início da requisição
        """
        request._perf_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
        Registra métricas de performance
        """
        duration = time.time() - getattr(request, '_perf_start_time', time.time())
        
        # Log de performance para requisições lentas (>2 segundos)
        if duration > 2.0:
            slow_query_data = {
                'event': 'slow_request',
                'path': request.path,
                'method': request.method,
                'duration_seconds': round(duration, 3),
                'status_code': response.status_code,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                'timestamp': timezone.now().isoformat(),
            }
            
            audit_logger.warning(json.dumps(slow_query_data))
        
        # Adicionar header de performance
        response['X-Response-Time'] = f"{round(duration * 1000, 2)}ms"
        
        return response