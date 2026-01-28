"""
Utilitários de Segurança - Lacrei Saúde API
==========================================
"""

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)


class QuerySecurityManager:
    """
    Gerenciador de segurança para consultas ao banco de dados
    """

    # Palavras-chave perigosas para SQL injection
    DANGEROUS_KEYWORDS = [
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "ALTER",
        "CREATE",
        "EXEC",
        "EXECUTE",
        "UNION",
        "SELECT",
        "SCRIPT",
        "JAVASCRIPT",
        "VBSCRIPT",
        "ONLOAD",
        "ONERROR",
    ]

    # Padrões de SQL injection
    INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|;|\/\*|\*\/|xp_|sp_)",
        r"('|(\\')|(;)|(\\;))",
        r"(\b(or|and)\s+\d+\s*=\s*\d+)",
        r"(\b(or|and)\s+.+\s*=\s*.+)",
        r"(\\b(char|ascii|substring|length|version|database|user|@@)\s*\()",
        r"(\+.*\+|\|\|.*\|\|)",
    ]

    @classmethod
    def validate_input_safety(cls, input_value):
        """
        Valida se a entrada é segura contra SQL injection
        """
        if not input_value or not isinstance(input_value, str):
            return True

        input_upper = input_value.upper()

        # Verificar palavras-chave perigosas
        for keyword in cls.DANGEROUS_KEYWORDS:
            if keyword in input_upper:
                logger.warning(f"Dangerous keyword detected: {keyword} in input: {input_value[:50]}...")
                raise ValidationError(f"Input contains forbidden content")

        # Verificar padrões de injection
        import re

        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected in input: {input_value[:50]}...")
                raise ValidationError(f"Invalid input pattern detected")

        return True

    @classmethod
    def safe_like_query(cls, field_name, search_term):
        """
        Cria uma consulta LIKE segura usando parâmetros
        """
        if not search_term:
            return None

        # Validar entrada
        cls.validate_input_safety(search_term)

        # Escapar caracteres especiais do LIKE
        escaped_term = search_term.replace("%", r"\%").replace("_", r"\_")

        return {f"{field_name}__icontains": escaped_term}

    @classmethod
    def monitor_database_queries(cls):
        """
        Monitora consultas suspeitas ao banco de dados
        """
        if settings.DEBUG:
            queries = connection.queries

            for query in queries[-5:]:  # Verificar últimas 5 consultas
                sql = query.get("sql", "").upper()

                # Verificar padrões suspeitos
                if any(keyword in sql for keyword in cls.DANGEROUS_KEYWORDS):
                    logger.warning(f"Suspicious database query detected: {query['sql'][:100]}...")


def validate_uuid_field(value):
    """
    Valida campos UUID de forma segura
    """
    import uuid

    if not value:
        return value

    try:
        # Converter para string e validar formato UUID
        uuid_str = str(value).strip()
        uuid.UUID(uuid_str)
        return uuid_str
    except (ValueError, AttributeError):
        raise ValidationError("Invalid UUID format")


def validate_integer_field(value, min_value=None, max_value=None):
    """
    Valida campos inteiros de forma segura
    """
    if value is None:
        return value

    try:
        int_value = int(value)

        if min_value is not None and int_value < min_value:
            raise ValidationError(f"Value must be at least {min_value}")

        if max_value is not None and int_value > max_value:
            raise ValidationError(f"Value must be at most {max_value}")

        return int_value
    except (ValueError, TypeError):
        raise ValidationError("Invalid integer value")


def sanitize_search_query(query):
    """
    Sanitiza consultas de busca
    """
    if not query:
        return ""

    # Remover caracteres perigosos
    dangerous_chars = ["<", ">", '"', "'", "&", ";", "(", ")", "{", "}", "[", "]"]
    sanitized = str(query)

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    # Limitar tamanho
    sanitized = sanitized[:200]

    # Validar segurança
    QuerySecurityManager.validate_input_safety(sanitized)

    return sanitized.strip()


class SecurePagination:
    """
    Paginação segura com validação de parâmetros
    """

    @staticmethod
    def validate_pagination_params(page, page_size):
        """
        Valida parâmetros de paginação
        """
        try:
            page = int(page) if page else 1
            page_size = int(page_size) if page_size else 20
        except (ValueError, TypeError):
            raise ValidationError("Invalid pagination parameters")

        # Limites de segurança
        if page < 1:
            page = 1
        if page > 10000:  # Limite máximo de páginas
            raise ValidationError("Page number too high")

        if page_size < 1:
            page_size = 20
        if page_size > 100:  # Limite máximo de itens por página
            page_size = 100

        return page, page_size


def log_security_event(event_type, message, request=None, extra_data=None):
    """
    Registra eventos de segurança
    """
    log_data = {
        "event_type": event_type,
        "message": message,
        "timestamp": timezone.now().isoformat(),
    }

    if request:
        log_data.update(
            {
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "path": request.path,
                "method": request.method,
                "user": str(request.user) if hasattr(request, "user") else "Anonymous",
            }
        )

    if extra_data:
        log_data.update(extra_data)

    logger.warning(f"SECURITY EVENT: {log_data}")
