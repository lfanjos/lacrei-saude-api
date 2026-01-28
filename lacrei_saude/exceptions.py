"""
Exception handlers customizados para Lacrei Saúde API
====================================================
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler que retorna respostas de erro formatadas
    """
    # Chama o handler padrão do DRF primeiro
    response = exception_handler(exc, context)
    
    # Se o DRF não tratou a exceção, tratamos aqui
    if response is None:
        
        # Django ValidationError
        if isinstance(exc, DjangoValidationError):
            response = Response(
                {
                    'error': 'Erro de validação',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else [str(exc)],
                    'code': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Http404
        elif isinstance(exc, Http404):
            response = Response(
                {
                    'error': 'Recurso não encontrado',
                    'details': str(exc),
                    'code': 'not_found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Outros erros não tratados
        else:
            logger.error(f"Erro não tratado: {str(exc)}", exc_info=True)
            response = Response(
                {
                    'error': 'Erro interno do servidor',
                    'details': 'Ocorreu um erro inesperado. Tente novamente mais tarde.',
                    'code': 'internal_error'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # Personalizar resposta se já foi tratada pelo DRF
    elif response is not None:
        custom_response_data = {
            'error': get_error_message(response.status_code),
            'details': response.data,
            'code': get_error_code(response.status_code)
        }
        
        # Se é um erro de validação, formatamos melhor
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            if isinstance(response.data, dict):
                custom_response_data['details'] = format_validation_errors(response.data)
        
        response.data = custom_response_data
    
    # Log de erros para debugging
    if response.status_code >= 400:
        logger.warning(
            f"Erro {response.status_code}: {exc} - "
            f"View: {context.get('view', 'unknown')} - "
            f"Request: {context.get('request', 'unknown')}"
        )
    
    return response


def get_error_message(status_code):
    """
    Retorna mensagem de erro amigável baseada no status code
    """
    messages = {
        400: 'Dados inválidos',
        401: 'Não autenticado',
        403: 'Sem permissão',
        404: 'Não encontrado',
        405: 'Método não permitido',
        406: 'Não aceito',
        409: 'Conflito',
        410: 'Recurso não disponível',
        422: 'Entidade não processável',
        429: 'Muitas requisições',
        500: 'Erro interno do servidor',
        501: 'Não implementado',
        502: 'Gateway inválido',
        503: 'Serviço indisponível',
    }
    return messages.get(status_code, 'Erro desconhecido')


def get_error_code(status_code):
    """
    Retorna código de erro baseado no status code
    """
    codes = {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        406: 'not_acceptable',
        409: 'conflict',
        410: 'gone',
        422: 'unprocessable_entity',
        429: 'too_many_requests',
        500: 'internal_server_error',
        501: 'not_implemented',
        502: 'bad_gateway',
        503: 'service_unavailable',
    }
    return codes.get(status_code, 'unknown_error')


def format_validation_errors(errors):
    """
    Formatar erros de validação de forma mais amigável
    """
    if isinstance(errors, dict):
        formatted = {}
        for field, field_errors in errors.items():
            if isinstance(field_errors, list):
                formatted[field] = field_errors
            else:
                formatted[field] = [str(field_errors)]
        return formatted
    elif isinstance(errors, list):
        return {'non_field_errors': errors}
    else:
        return {'error': str(errors)}