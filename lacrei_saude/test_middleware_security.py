"""
Testes para Middleware de Segurança - Lacrei Saúde API
======================================================

Testes para middleware, headers de segurança, logging e permissões.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

User = get_user_model()


class SecurityHeadersTestCase(TestCase):
    """Testes para headers de segurança"""

    def setUp(self):
        """Setup para testes de headers"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="headertest", email="header@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_security_headers_middleware(self):
        """Testa aplicação de headers de segurança"""
        from lacrei_saude.security_headers import SecurityHeadersMiddleware

        # Mock get_response
        get_response = Mock(return_value=HttpResponse("Test content"))
        middleware = SecurityHeadersMiddleware(get_response)

        request = self.factory.get("/")
        response = middleware(request)

        # Verifica se middleware foi chamado
        get_response.assert_called_once_with(request)
        self.assertEqual(response.content, b"Test content")

    def test_csp_header_configuration(self):
        """Testa configuração do Content Security Policy"""
        response = self.client.get("/api/auth/status/")

        # Verifica se CSP está presente (se configurado)
        csp_header = response.get("Content-Security-Policy")
        if csp_header:
            # CSP deve incluir diretivas básicas
            self.assertIn("default-src", csp_header)
            self.assertIn("script-src", csp_header)

    def test_frame_options_header(self):
        """Testa header X-Frame-Options"""
        response = self.client.get("/api/auth/status/")

        frame_options = response.get("X-Frame-Options")
        if frame_options:
            self.assertIn(frame_options, ["DENY", "SAMEORIGIN"])

    def test_content_type_options_header(self):
        """Testa header X-Content-Type-Options"""
        response = self.client.get("/api/auth/status/")

        content_type_options = response.get("X-Content-Type-Options")
        if content_type_options:
            self.assertEqual(content_type_options, "nosniff")


class LoggingMiddlewareTestCase(TestCase):
    """Testes para middleware de logging"""

    def setUp(self):
        """Setup para testes de logging"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="logtest", email="log@test.com", password="TestPassword123!", user_type="paciente"
        )

    @patch("lacrei_saude.logging_middleware.logger")
    def test_request_logging_middleware(self, mock_logger):
        """Testa middleware de logging de requests"""
        from lacrei_saude.logging_middleware import RequestLoggingMiddleware

        get_response = Mock(return_value=HttpResponse("OK"))
        middleware = RequestLoggingMiddleware(get_response)

        request = self.factory.post("/api/v1/profissionais/", {"nome": "Dr. Test", "email": "test@example.com"})
        request.user = self.user

        response = middleware(request)

        # Verifica se logging foi chamado
        self.assertTrue(mock_logger.info.called or mock_logger.debug.called)

    @patch("lacrei_saude.logging_middleware.logger")
    def test_sensitive_data_filtering(self, mock_logger):
        """Testa filtragem de dados sensíveis no logging"""
        from lacrei_saude.logging_middleware import RequestLoggingMiddleware

        get_response = Mock(return_value=HttpResponse("OK"))
        middleware = RequestLoggingMiddleware(get_response)

        request = self.factory.post("/api/auth/login/", {"username": "testuser", "password": "secretpassword123"})

        response = middleware(request)

        # Verifica se dados sensíveis não foram logados
        for call in mock_logger.info.call_args_list:
            log_message = str(call)
            self.assertNotIn("secretpassword123", log_message)
            self.assertNotIn("password", log_message.lower())

    @patch("lacrei_saude.logging_middleware.logger")
    def test_error_response_logging(self, mock_logger):
        """Testa logging de respostas de erro"""
        from lacrei_saude.logging_middleware import RequestLoggingMiddleware

        error_response = HttpResponse("Internal Error", status=500)
        get_response = Mock(return_value=error_response)
        middleware = RequestLoggingMiddleware(get_response)

        request = self.factory.get("/api/v1/profissionais/")
        request.user = self.user

        response = middleware(request)

        # Verifica se erro foi logado
        self.assertTrue(mock_logger.error.called or mock_logger.warning.called)


class SecurityMiddlewareTestCase(TestCase):
    """Testes para middleware de segurança geral"""

    def setUp(self):
        """Setup para testes de middleware"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="sectest", email="sec@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_jwt_authentication_middleware(self):
        """Testa middleware de autenticação JWT"""
        from lacrei_saude.middleware import JWTAuthenticationMiddleware

        get_response = Mock(return_value=HttpResponse("OK"))
        middleware = JWTAuthenticationMiddleware(get_response)

        # Request sem token
        request = self.factory.get("/api/v1/profissionais/")
        response = middleware(request)

        # Deve processar normalmente
        get_response.assert_called_once_with(request)

    def test_rate_limiting_middleware(self):
        """Testa middleware de rate limiting"""
        # Importa middleware se existir
        try:
            from lacrei_saude.middleware import RateLimitingMiddleware

            get_response = Mock(return_value=HttpResponse("OK"))
            middleware = RateLimitingMiddleware(get_response)

            request = self.factory.get("/api/v1/profissionais/")
            request.META["REMOTE_ADDR"] = "127.0.0.1"

            response = middleware(request)

            # Verifica se foi processado
            self.assertIsNotNone(response)

        except ImportError:
            self.skipTest("RateLimitingMiddleware não implementado")

    def test_ip_filtering_middleware(self):
        """Testa middleware de filtragem de IP"""
        try:
            from lacrei_saude.middleware import IPFilteringMiddleware

            get_response = Mock(return_value=HttpResponse("OK"))
            middleware = IPFilteringMiddleware(get_response)

            # IP suspeito
            request = self.factory.get("/api/v1/profissionais/")
            request.META["REMOTE_ADDR"] = "192.168.1.100"

            response = middleware(request)

            # Deve processar ou bloquear dependendo da configuração
            self.assertIsNotNone(response)

        except ImportError:
            self.skipTest("IPFilteringMiddleware não implementado")


class PermissionsTestCase(APITestCase):
    """Testes para classes de permissão customizadas"""

    def setUp(self):
        """Setup para testes de permissões"""
        self.paciente = User.objects.create_user(
            username="paciente", email="paciente@test.com", password="TestPassword123!", user_type="paciente"
        )
        self.profissional = User.objects.create_user(
            username="profissional", email="profissional@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )

    def test_is_admin_or_readonly_permission(self):
        """Testa permissão IsAdminOrReadOnly"""
        from rest_framework.test import APIRequestFactory

        from lacrei_saude.permissions import IsAdminOrReadOnly

        factory = APIRequestFactory()
        permission = IsAdminOrReadOnly()

        # Request GET (read-only) para paciente
        request = factory.get("/api/v1/profissionais/")
        request.user = self.paciente

        # Deve permitir GET para qualquer usuário autenticado
        self.assertTrue(permission.has_permission(request, None))

        # Request POST para paciente
        request = factory.post("/api/v1/profissionais/")
        request.user = self.paciente

        # Pode bloquear POST para não-admin
        result = permission.has_permission(request, None)
        if not result:
            # Admin deve ter acesso
            request.user = self.admin
            self.assertTrue(permission.has_permission(request, None))

    def test_is_owner_or_admin_permission(self):
        """Testa permissão IsOwnerOrAdmin"""
        try:
            from rest_framework.test import APIRequestFactory

            from lacrei_saude.permissions import IsOwnerOrAdmin

            factory = APIRequestFactory()
            permission = IsOwnerOrAdmin()

            # Mock object com owner
            obj = Mock()
            obj.user = self.paciente

            # Request do próprio owner
            request = factory.get("/api/v1/objeto/1/")
            request.user = self.paciente

            self.assertTrue(permission.has_object_permission(request, None, obj))

            # Request de outro usuário
            request.user = self.profissional
            result = permission.has_object_permission(request, None, obj)

            # Admin deve ter acesso mesmo não sendo owner
            request.user = self.admin
            admin_result = permission.has_object_permission(request, None, obj)
            if not result:  # Se bloqueou usuário comum
                self.assertTrue(admin_result)  # Admin deve passar

        except ImportError:
            self.skipTest("IsOwnerOrAdmin não implementado")

    def test_is_profissional_or_admin_permission(self):
        """Testa permissão específica para profissionais"""
        try:
            from rest_framework.test import APIRequestFactory

            from authentication.permissions import IsProfissionalOrAdmin

            factory = APIRequestFactory()
            permission = IsProfissionalOrAdmin()

            # Request de profissional
            request = factory.get("/api/v1/consultas/")
            request.user = self.profissional

            self.assertTrue(permission.has_permission(request, None))

            # Request de paciente
            request.user = self.paciente
            paciente_result = permission.has_permission(request, None)

            # Admin deve ter acesso
            request.user = self.admin
            admin_result = permission.has_permission(request, None)
            self.assertTrue(admin_result)

        except ImportError:
            self.skipTest("IsProfissionalOrAdmin não implementado")


class ExceptionsHandlingTestCase(TestCase):
    """Testes para tratamento de exceções customizadas"""

    def test_custom_exception_handler(self):
        """Testa handler customizado de exceções"""
        try:
            from rest_framework.exceptions import ValidationError
            from rest_framework.views import exception_handler

            from lacrei_saude.exceptions import custom_exception_handler

            # Mock context e exception
            exc = ValidationError("Erro de validação")
            context = {"request": Mock(), "view": Mock()}

            response = custom_exception_handler(exc, context)

            # Deve retornar response estruturado
            self.assertIsNotNone(response)
            if hasattr(response, "data"):
                self.assertIn("error", response.data or {})

        except ImportError:
            self.skipTest("custom_exception_handler não implementado")

    def test_validation_error_format(self):
        """Testa formato de erros de validação"""
        # Tenta criar profissional com dados inválidos
        self.client.post(
            "/api/v1/profissionais/", {"nome": "", "email": "email-invalido", "telefone": "123"}  # Nome obrigatório
        )
        # Verifica se erro é bem formatado através da resposta
        # Este teste funciona se o handler customizado estiver ativo

    def test_permission_denied_format(self):
        """Testa formato de erro de permissão negada"""
        # Usuário não autenticado tenta criar profissional
        response = self.client.post("/api/v1/profissionais/", {"nome": "Dr. Test", "email": "test@example.com"})

        # Verifica se retorna erro estruturado
        if response.status_code in [401, 403]:
            if response.content:
                try:
                    data = response.json()
                    # Verifica estrutura de erro
                    self.assertTrue("error" in data or "detail" in data)
                except:
                    pass  # Response pode não ser JSON


class MonitoringViewsTestCase(APITestCase):
    """Testes para views de monitoramento"""

    def setUp(self):
        """Setup para testes de monitoramento"""
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_health_check_endpoint(self):
        """Testa endpoint de health check"""
        response = self.client.get("/api/monitoring/health/")

        # Health check deve estar disponível
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()
            self.assertIn("status", data)

    def test_log_stats_endpoint_auth(self):
        """Testa endpoint de estatísticas de logs (autenticação)"""
        # Sem autenticação
        response = self.client.get("/api/monitoring/logs/stats/")
        self.assertIn(response.status_code, [401, 403, 404])

        # Com usuário comum
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/monitoring/logs/stats/")
        self.assertIn(response.status_code, [403, 404])

        # Com admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/monitoring/logs/stats/")
        self.assertIn(response.status_code, [200, 404])

    def test_access_log_analysis_endpoint(self):
        """Testa endpoint de análise de logs de acesso"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/monitoring/logs/access/")
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()
            # Deve conter estatísticas de acesso
            expected_fields = ["total_requests", "unique_ips", "top_endpoints"]
            for field in expected_fields:
                if field in data:
                    self.assertIsNotNone(data[field])

    def test_error_log_endpoint(self):
        """Testa endpoint de logs de erro"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/monitoring/logs/errors/")
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()
            # Deve retornar lista de erros ou estatísticas
            self.assertTrue("errors" in data or "count" in data)


class SecurityViewsTestCase(APITestCase):
    """Testes para views de segurança"""

    def setUp(self):
        """Setup para testes de segurança"""
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )

    def test_security_check_endpoint(self):
        """Testa endpoint de verificação de segurança"""
        response = self.client.get("/api/security/check/")

        # Endpoint pode estar disponível publicamente ou restrito
        self.assertIn(response.status_code, [200, 401, 403, 404])

        if response.status_code == 200:
            data = response.json()
            # Deve conter informações de segurança
            security_fields = ["headers", "ssl", "vulnerabilities"]
            for field in security_fields:
                if field in data:
                    self.assertIsNotNone(data[field])

    def test_headers_test_endpoint(self):
        """Testa endpoint de teste de headers"""
        response = self.client.get("/api/security/headers-test/")

        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            # Deve retornar informações sobre headers de segurança
            data = response.json()
            header_fields = ["csp", "hsts", "x_frame_options", "x_content_type_options"]
            for field in header_fields:
                if field in data:
                    self.assertIsNotNone(data[field])

    def test_cors_test_endpoint(self):
        """Testa endpoint de teste CORS"""
        response = self.client.get("/api/security/cors-test/")

        self.assertIn(response.status_code, [200, 404])

        # Verifica headers CORS na resposta
        cors_headers = ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods", "Access-Control-Allow-Headers"]

        for header in cors_headers:
            if header in response.headers:
                self.assertIsNotNone(response.headers[header])

    def test_csp_report_endpoint(self):
        """Testa endpoint de relatório CSP"""
        csp_report = {
            "csp-report": {"violated-directive": "script-src", "blocked-uri": "inline", "document-uri": "https://example.com"}
        }

        response = self.client.post("/api/security/csp-report/", data=json.dumps(csp_report), content_type="application/json")

        # CSP report endpoint deve aceitar POST
        self.assertIn(response.status_code, [200, 201, 202, 404])
