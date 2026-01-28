"""
Views de Segurança - Lacrei Saúde API
====================================
"""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger("security")


@csrf_exempt
@require_http_methods(["POST"])
def csp_report_view(request):
    """
    Endpoint para receber relatórios de violações de CSP
    """
    try:
        if request.content_type == "application/csp-report":
            # Formato padrão de relatório CSP
            report_data = json.loads(request.body.decode("utf-8"))
        elif request.content_type == "application/json":
            # Alguns browsers enviam como JSON
            report_data = json.loads(request.body.decode("utf-8"))
        else:
            return JsonResponse({"error": "Invalid content type"}, status=400)

        # Log da violação
        csp_report = report_data.get("csp-report", report_data)

        log_data = {
            "type": "csp_violation",
            "document_uri": csp_report.get("document-uri"),
            "blocked_uri": csp_report.get("blocked-uri"),
            "violated_directive": csp_report.get("violated-directive"),
            "original_policy": csp_report.get("original-policy"),
            "user_agent": request.META.get("HTTP_USER_AGENT"),
            "ip_address": request.META.get("REMOTE_ADDR"),
            "timestamp": csp_report.get("timestamp"),
        }

        logger.warning(f"CSP Violation: {json.dumps(log_data)}")

        return HttpResponse(status=204)  # No Content

    except Exception as e:
        logger.error(f"Error processing CSP report: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)


class SecurityCheckView(View):
    """
    View para verificação de segurança da aplicação
    """

    def get(self, request):
        """
        Retorna status de segurança da aplicação
        """
        from django.conf import settings

        security_status = {
            "https_enabled": not settings.DEBUG,
            "hsts_enabled": hasattr(settings, "SECURE_HSTS_SECONDS"),
            "csp_enabled": True,
            "cors_configured": hasattr(settings, "CORS_ALLOWED_ORIGINS"),
            "security_middleware_enabled": True,
            "api_version": "1.0",
            "security_features": [
                "Input Sanitization",
                "SQL Injection Protection",
                "XSS Protection",
                "CSRF Protection",
                "Rate Limiting",
                "Content Security Policy",
                "CORS Configuration",
                "Security Headers",
            ],
        }

        return JsonResponse(security_status)


class SecurityHeadersTestView(View):
    """
    View para testar headers de segurança
    """

    def get(self, request):
        """
        Endpoint para verificar se headers de segurança estão sendo aplicados
        """
        # Filtrar apenas headers serializáveis
        filtered_headers = {}
        for key, value in request.META.items():
            if isinstance(value, (str, int, float, bool)) and key.startswith(("HTTP_", "REMOTE_", "SERVER_")):
                if key not in ["HTTP_AUTHORIZATION", "HTTP_X_API_KEY"]:
                    filtered_headers[key] = value
                else:
                    filtered_headers[key] = "[REDACTED]"

        headers_info = {
            "request_headers": filtered_headers,
            "security_note": "Check response headers for security configurations",
            "cors_origin": request.META.get("HTTP_ORIGIN"),
            "user_agent": request.META.get("HTTP_USER_AGENT"),
            "ip_address": request.META.get("REMOTE_ADDR"),
            "method": request.method,
            "path": request.path,
        }

        return JsonResponse(headers_info)


@method_decorator(csrf_exempt, name="dispatch")
class CORSTestView(View):
    """
    View para testar configurações CORS
    """

    def options(self, request):
        """
        Handle preflight CORS requests
        """
        response = HttpResponse()
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Max-Age"] = "86400"
        return response

    def get(self, request):
        """
        Test CORS GET request
        """
        return JsonResponse(
            {
                "message": "CORS test successful",
                "origin": request.META.get("HTTP_ORIGIN"),
                "method": request.method,
                "path": request.path,
            }
        )

    def post(self, request):
        """
        Test CORS POST request
        """
        return JsonResponse(
            {
                "message": "CORS POST test successful",
                "origin": request.META.get("HTTP_ORIGIN"),
                "method": request.method,
                "content_type": request.META.get("CONTENT_TYPE"),
            }
        )


def security_txt_view(request):
    """
    Security.txt endpoint conforme RFC 9116
    """
    security_txt = """Contact: mailto:security@lacreisaude.com.br
Contact: https://lacreisaude.com.br/security
Expires: 2025-12-31T23:59:59.000Z
Acknowledgments: https://lacreisaude.com.br/security/acknowledgments
Preferred-Languages: pt-BR, en
Canonical: https://lacreisaude.com.br/.well-known/security.txt
Policy: https://lacreisaude.com.br/security/policy"""

    return HttpResponse(security_txt, content_type="text/plain")
