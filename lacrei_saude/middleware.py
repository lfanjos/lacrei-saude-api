"""
Middleware personalizado - Lacrei Saúde API
==========================================
"""

import json
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .validators import sanitize_string, sanitize_html_content

logger = logging.getLogger(__name__)


class InputSanitizationMiddleware(MiddlewareMixin):
    """
    Middleware para sanitização automática de dados de entrada
    """
    
    def process_request(self, request):
        """
        Sanitiza dados de entrada em requisições POST, PUT, PATCH
        """
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Sanitizar dados JSON
                if request.content_type == 'application/json' and hasattr(request, 'body'):
                    try:
                        data = json.loads(request.body.decode('utf-8'))
                        sanitized_data = self._sanitize_dict(data)
                        
                        # Substitui o body da requisição
                        request._body = json.dumps(sanitized_data).encode('utf-8')
                        
                        logger.info(f"Input sanitized for {request.path}")
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
                
                # Sanitizar dados de formulário
                if hasattr(request, 'POST'):
                    for key, value in request.POST.items():
                        if isinstance(value, str):
                            request.POST._mutable = True
                            request.POST[key] = sanitize_string(value)
                            request.POST._mutable = False
                
            except Exception as e:
                logger.error(f"Error in input sanitization: {str(e)}")
        
        return None
    
    def _sanitize_dict(self, data):
        """
        Recursivamente sanitiza um dicionário
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                sanitized_key = sanitize_string(str(key)) if isinstance(key, str) else key
                sanitized[sanitized_key] = self._sanitize_value(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_value(item) for item in data]
        else:
            return self._sanitize_value(data)
    
    def _sanitize_value(self, value):
        """
        Sanitiza um valor individual
        """
        if isinstance(value, str):
            # Campos que podem conter HTML (observações, etc)
            if len(value) > 200:  # Assume que textos longos podem ter HTML
                return sanitize_html_content(value)
            else:
                return sanitize_string(value)
        elif isinstance(value, dict):
            return self._sanitize_dict(value)
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        else:
            return value


class SecurityValidationMiddleware(MiddlewareMixin):
    """
    Middleware para validações de segurança
    """
    
    # Patterns de SQL injection
    SQL_INJECTION_PATTERNS = [
        r"('|(\\')|(;)|(\\;))",  # Aspas e ponto e vírgula
        r"(\\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\\b)",
        r"(\\b(or|and)\\s+\\d+\\s*=\\s*\\d+)",  # OR 1=1, AND 1=1
        r"(\\-\\-)|(/\\*.*\\*/)",  # Comentários SQL
    ]
    
    def process_request(self, request):
        """
        Valida requisições contra padrões de ataque
        """
        # Verificar SQL injection em parâmetros GET
        for key, value in request.GET.items():
            if self._check_sql_injection(value):
                logger.warning(f"SQL injection attempt detected in GET parameter: {key} = {value}")
                return JsonResponse({
                    'error': 'Invalid input detected'
                }, status=400)
        
        # Verificar SQL injection no body para POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            if hasattr(request, 'body') and request.body:
                try:
                    body_str = request.body.decode('utf-8')
                    if self._check_sql_injection(body_str):
                        logger.warning(f"SQL injection attempt detected in request body")
                        return JsonResponse({
                            'error': 'Invalid input detected'
                        }, status=400)
                except UnicodeDecodeError:
                    pass
        
        return None
    
    def _check_sql_injection(self, value):
        """
        Verifica padrões de SQL injection
        """
        if not isinstance(value, str):
            return False
        
        import re
        value_lower = value.lower()
        
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower):
                return True
        
        return False


class DataTypeValidationMiddleware(MiddlewareMixin):
    """
    Middleware para validação de tipos de dados
    """
    
    def process_request(self, request):
        """
        Valida tipos de dados em requisições JSON
        """
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.content_type == 'application/json' and hasattr(request, 'body'):
                try:
                    data = json.loads(request.body.decode('utf-8'))
                    
                    # Validações específicas por endpoint
                    validation_errors = self._validate_data_types(request.path, data)
                    
                    if validation_errors:
                        logger.warning(f"Data type validation failed for {request.path}: {validation_errors}")
                        return JsonResponse({
                            'error': 'Invalid data types',
                            'details': validation_errors
                        }, status=400)
                        
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        
        return None
    
    def _validate_data_types(self, path, data):
        """
        Valida tipos de dados baseado no endpoint
        """
        errors = []
        
        # Validações comuns para todos os endpoints
        if isinstance(data, dict):
            # Validar IDs como números ou UUIDs
            if 'id' in data and data['id'] is not None:
                if not (isinstance(data['id'], (int, str))):
                    errors.append("Field 'id' must be a number or string")
            
            # Validar emails
            if 'email' in data and data['email'] is not None:
                if not isinstance(data['email'], str):
                    errors.append("Field 'email' must be a string")
                elif '@' not in data['email']:
                    errors.append("Field 'email' must be a valid email address")
            
            # Validar telefones
            for field in ['telefone', 'telefone_paciente', 'telefone_contato']:
                if field in data and data[field] is not None:
                    if not isinstance(data[field], str):
                        errors.append(f"Field '{field}' must be a string")
            
            # Validar valores monetários
            for field in ['valor_consulta', 'valor']:
                if field in data and data[field] is not None:
                    if not isinstance(data[field], (int, float)):
                        errors.append(f"Field '{field}' must be a number")
                    elif data[field] < 0:
                        errors.append(f"Field '{field}' cannot be negative")
            
            # Validar datas
            for field in ['data_hora', 'data_nascimento', 'created_at', 'updated_at']:
                if field in data and data[field] is not None:
                    if not isinstance(data[field], str):
                        errors.append(f"Field '{field}' must be a string (ISO format)")
            
            # Validar booleanos
            for field in ['is_active', 'aceita_convenio', 'pago']:
                if field in data and data[field] is not None:
                    if not isinstance(data[field], bool):
                        errors.append(f"Field '{field}' must be a boolean")
        
        return errors