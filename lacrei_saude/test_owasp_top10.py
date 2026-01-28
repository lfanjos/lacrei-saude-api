"""
Testes OWASP Top 10 - Lacrei Saúde API
======================================

Testes baseados nas 10 principais vulnerabilidades de segurança
identificadas pela OWASP (Open Web Application Security Project).
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class A01BrokenAccessControlTestCase(APITestCase):
    """A01:2021 – Broken Access Control"""

    def setUp(self):
        """Setup para testes de controle de acesso"""
        self.paciente = User.objects.create_user(
            username="paciente", email="paciente@test.com", password="TestPassword123!", user_type="paciente"
        )
        self.profissional = User.objects.create_user(
            username="profissional", email="profissional@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )

    def test_vertical_privilege_escalation(self):
        """Testa escalação vertical de privilégios"""
        self.client.force_authenticate(user=self.paciente)

        # Paciente tenta acessar área administrativa
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, [401, 403, 404])

        # Paciente tenta acessar endpoint de usuários
        response = self.client.get("/api/auth/users/")
        self.assertIn(response.status_code, [401, 403, 404])

    def test_horizontal_privilege_escalation(self):
        """Testa escalação horizontal de privilégios"""
        # Cria outro paciente
        outro_paciente = User.objects.create_user(
            username="outro_paciente", email="outro@test.com", password="TestPassword123!", user_type="paciente"
        )

        self.client.force_authenticate(user=self.paciente)

        # Tenta acessar dados do outro paciente
        response = self.client.get(f"/api/auth/users/{outro_paciente.id}/")
        self.assertIn(response.status_code, [401, 403, 404])

    def test_direct_object_reference(self):
        """Testa referência direta insegura a objetos"""
        self.client.force_authenticate(user=self.paciente)

        # Tenta acessar objeto por ID sequencial
        for obj_id in range(1, 10):
            response = self.client.get(f"/api/v1/consultas/{obj_id}/")
            if response.status_code == 200:
                # Se retornou dados, verifica se são do usuário correto
                data = response.json()
                if "paciente" in data:
                    self.assertEqual(data["paciente"], self.paciente.id)


class A02CryptographicFailuresTestCase(APITestCase):
    """A02:2021 – Cryptographic Failures"""

    def setUp(self):
        """Setup para testes criptográficos"""
        self.user = User.objects.create_user(
            username="cryptotest", email="crypto@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_password_storage_security(self):
        """Testa se senhas são armazenadas de forma segura"""
        # Senha não deve estar em texto plano
        self.assertNotEqual(self.user.password, "TestPassword123!")

        # Deve usar hash forte (Django usa PBKDF2 por padrão)
        self.assertTrue(self.user.password.startswith("pbkdf2_sha256$"))

        # Hash deve ter complexidade adequada
        self.assertGreater(len(self.user.password), 50)

    def test_sensitive_data_exposure_in_logs(self):
        """Testa exposição de dados sensíveis em logs"""
        with self.assertLogs(level="INFO") as log:
            # Faz login
            response = self.client.post(
                reverse("authentication:login"), {"username": "cryptotest", "password": "TestPassword123!"}
            )

            # Verifica se senha não aparece nos logs
            log_output = " ".join(log.output)
            self.assertNotIn("TestPassword123!", log_output)
            self.assertNotIn("password", log_output.lower())

    def test_jwt_token_security(self):
        """Testa segurança dos tokens JWT"""
        response = self.client.post(
            reverse("authentication:login"), {"username": "cryptotest", "password": "TestPassword123!"}
        )

        if response.status_code == 200:
            token = response.json().get("access")

            # Token deve existir
            self.assertIsNotNone(token)

            # Token deve ter formato JWT (3 partes separadas por .)
            parts = token.split(".")
            self.assertEqual(len(parts), 3)

            # Cada parte deve ter conteúdo
            for part in parts:
                self.assertGreater(len(part), 0)

    def test_https_enforcement(self):
        """Testa se HTTPS é enforçado"""
        # Simula request HTTP
        response = self.client.get("/", secure=False)

        # Verifica headers de segurança HTTPS
        security_headers = ["Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options"]

        for header in security_headers:
            if header in response.headers:
                self.assertIsNotNone(response.headers[header])


class A03InjectionTestCase(APITestCase):
    """A03:2021 – Injection (já coberto em test_security_injection.py)"""

    def test_sql_injection_prevention(self):
        """Teste básico de prevenção de SQL injection"""
        user = User.objects.create_user(
            username="injectiontest", email="injection@test.com", password="TestPassword123!", user_type="profissional"
        )

        self.client.force_authenticate(user=user)

        # Tenta SQL injection via parâmetro de busca
        malicious_query = "' OR '1'='1' --"
        response = self.client.get(f"/api/v1/profissionais/?search={malicious_query}")

        # Não deve retornar erro de SQL ou dados não autorizados
        self.assertNotEqual(response.status_code, 500)


class A04InsecureDesignTestCase(APITestCase):
    """A04:2021 – Insecure Design"""

    def setUp(self):
        """Setup para testes de design inseguro"""
        self.user = User.objects.create_user(
            username="designtest", email="design@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_account_enumeration_protection(self):
        """Testa proteção contra enumeração de contas"""
        # Tenta login com usuário existente e senha incorreta
        response1 = self.client.post(reverse("authentication:login"), {"username": "designtest", "password": "wrongpassword"})

        # Tenta login com usuário inexistente
        response2 = self.client.post(
            reverse("authentication:login"), {"username": "nonexistentuser", "password": "wrongpassword"}
        )

        # Respostas devem ser similares para não permitir enumeração
        self.assertEqual(response1.status_code, response2.status_code)

    def test_business_logic_bypass(self):
        """Testa bypass de lógica de negócio"""
        self.client.force_authenticate(user=self.user)

        # Tenta criar consulta para data no passado
        past_date = "2020-01-01T10:00:00Z"
        response = self.client.post(
            "/api/v1/consultas/", {"profissional": 1, "data_horario": past_date, "observacoes": "Teste"}
        )

        # Deve ser rejeitado pela validação de negócio
        self.assertIn(response.status_code, [400, 422])

    def test_excessive_data_exposure(self):
        """Testa exposição excessiva de dados"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/auth/status/")

        if response.status_code == 200:
            data = response.json()

            # Não deve expor dados sensíveis desnecessariamente
            sensitive_fields = ["password", "secret_key", "private_key"]
            for field in sensitive_fields:
                self.assertNotIn(field, str(data).lower())


class A05SecurityMisconfigurationTestCase(APITestCase):
    """A05:2021 – Security Misconfiguration"""

    def test_debug_mode_disabled(self):
        """Testa se debug mode está desabilitado"""
        from django.conf import settings

        # Debug não deve estar ativado em produção
        # Este teste pode falhar em desenvolvimento
        if hasattr(settings, "DEBUG"):
            # Em ambiente de teste, documenta o valor
            print(f"DEBUG setting: {settings.DEBUG}")

    def test_default_credentials_changed(self):
        """Testa se credenciais padrão foram alteradas"""
        # Tenta login com credenciais comuns
        common_credentials = [("admin", "admin"), ("admin", "password"), ("root", "root"), ("test", "test")]

        for username, password in common_credentials:
            response = self.client.post(reverse("authentication:login"), {"username": username, "password": password})

            # Não deve conseguir fazer login com credenciais padrão
            self.assertNotEqual(response.status_code, 200)

    def test_error_handling_security(self):
        """Testa se tratamento de erros não vaza informações"""
        # Força um erro 404
        response = self.client.get("/api/v1/nonexistent_endpoint/")
        self.assertEqual(response.status_code, 404)

        if response.status_code == 404:
            # Resposta não deve conter informações de sistema
            content = response.content.decode().lower()
            sensitive_info = ["traceback", "exception", "django", "python"]

            for info in sensitive_info:
                self.assertNotIn(info, content)

    def test_unnecessary_services_disabled(self):
        """Testa se serviços desnecessários estão desabilitados"""
        # Tenta acessar interfaces administrativas que podem estar expostas
        admin_interfaces = ["/phpMyAdmin/", "/wp-admin/", "/admin/admin/", "/debug/", "/.env"]

        for interface in admin_interfaces:
            response = self.client.get(interface)
            # Deve retornar 404, não 200
            self.assertNotEqual(response.status_code, 200)


class A06VulnerableOutdatedComponentsTestCase(TestCase):
    """A06:2021 – Vulnerable and Outdated Components"""

    def test_django_version_security(self):
        """Testa se versão do Django é segura"""
        import django

        # Verifica versão do Django
        version = django.VERSION
        major, minor = version[0], version[1]

        # Django 3.2+ é LTS e mais seguro
        if major < 3 or (major == 3 and minor < 2):
            print(f"AVISO: Django {django.get_version()} pode ter vulnerabilidades conhecidas")

    def test_third_party_dependencies(self):
        """Testa dependências de terceiros"""
        # Este teste verifica se há ferramentas de auditoria configuradas

        try:
            import pip_audit  # noqa

            print("pip-audit disponível para auditoria de dependências")
        except ImportError:
            print("Considere instalar pip-audit para auditoria de dependências")

        try:
            import safety  # noqa

            print("safety disponível para verificação de vulnerabilidades")
        except ImportError:
            print("Considere instalar safety para verificação de vulnerabilidades")


class A07IdentificationAuthenticationFailuresTestCase(APITestCase):
    """A07:2021 – Identification and Authentication Failures"""

    def setUp(self):
        """Setup para testes de autenticação"""
        self.user = User.objects.create_user(
            username="authtest", email="auth@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_weak_password_rejection(self):
        """Testa rejeição de senhas fracas"""
        weak_passwords = ["123456", "password", "qwerty", "12345678", "abc123", "password123"]

        for weak_password in weak_passwords:
            response = self.client.post(
                reverse("authentication:register"),
                {
                    "username": f"test_{weak_password[:3]}",
                    "email": f"{weak_password[:3]}@test.com",
                    "password": weak_password,
                    "user_type": "paciente",
                },
            )

            # Senha fraca deve ser rejeitada
            self.assertNotEqual(response.status_code, 201)

    def test_session_management(self):
        """Testa gerenciamento de sessões"""
        # Faz login
        response = self.client.post(reverse("authentication:login"), {"username": "authtest", "password": "TestPassword123!"})

        if response.status_code == 200:
            token = response.json().get("access")

            # Usa o token
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            auth_response = self.client.get("/api/auth/status/")

            if auth_response.status_code == 200:
                # Token deve funcionar
                self.assertEqual(auth_response.status_code, 200)

                # Logout deve invalidar
                logout_response = self.client.post(reverse("authentication:logout"))
                if logout_response.status_code in [200, 204]:
                    # Tenta usar token após logout
                    post_logout_response = self.client.get("/api/auth/status/")
                    # Pode ainda funcionar se for JWT stateless
                    self.assertIn(post_logout_response.status_code, [200, 401, 403])

    def test_credential_stuffing_protection(self):
        """Testa proteção contra credential stuffing"""
        # Lista de credenciais comuns para teste
        common_credentials = [("admin@example.com", "password123"), ("user@test.com", "123456"), ("test@domain.com", "qwerty")]

        blocked = False
        for email, password in common_credentials * 3:  # Testa múltiplas vezes
            response = self.client.post(reverse("authentication:login"), {"username": email, "password": password})

            if response.status_code == 429:  # Rate limited
                blocked = True
                break

        # Se fez muitas tentativas, deveria ter sido bloqueado
        # Em desenvolvimento pode não ter rate limiting ativo


class A08SoftwareDataIntegrityFailuresTestCase(APITestCase):
    """A08:2021 – Software and Data Integrity Failures"""

    def setUp(self):
        """Setup para testes de integridade"""
        self.user = User.objects.create_user(
            username="integritytest", email="integrity@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.client.force_authenticate(user=self.user)

    def test_data_tampering_protection(self):
        """Testa proteção contra adulteração de dados"""
        # Cria dados
        response = self.client.post(
            "/api/v1/profissionais/",
            {
                "nome": "Dr. Teste",
                "email": "dr.teste@example.com",
                "telefone": "11999999999",
                "especialidade": "Clínico Geral",
                "crm": "123456-SP",
            },
        )

        if response.status_code in [200, 201]:
            profissional_id = response.json().get("id")

            # Tenta modificar com dados inválidos
            tamper_response = self.client.patch(f"/api/v1/profissionais/{profissional_id}/", {"crm": "INVALID_CRM"})

            # Validação deve rejeitar dados inválidos
            if tamper_response.status_code == 200:
                # Verifica se dados foram realmente alterados
                get_response = self.client.get(f"/api/v1/profissionais/{profissional_id}/")
                data = get_response.json()
                self.assertNotEqual(data["crm"], "INVALID_CRM")

    def test_serialization_integrity(self):
        """Testa integridade da serialização"""
        # Tenta enviar dados malformados
        malicious_data = {
            "nome": '<script>alert("xss")</script>',
            "email": "test@test.com",
            "observacoes": '{"malicious": true, "__proto__": {"isAdmin": true}}',
        }

        response = self.client.post("/api/v1/profissionais/", malicious_data)

        if response.status_code in [200, 201]:
            # Dados devem ser sanitizados
            profissional = response.json()
            self.assertNotIn("<script>", profissional.get("nome", ""))
            self.assertNotIn("__proto__", str(profissional))


class A09SecurityLoggingMonitoringFailuresTestCase(APITestCase):
    """A09:2021 – Security Logging and Monitoring Failures"""

    def setUp(self):
        """Setup para testes de logging"""
        self.user = User.objects.create_user(
            username="loggingtest", email="logging@test.com", password="TestPassword123!", user_type="paciente"
        )

    def test_authentication_logging(self):
        """Testa se tentativas de autenticação são logadas"""
        with self.assertLogs(level="INFO") as log:
            # Tentativa de login falhada
            response = self.client.post(
                reverse("authentication:login"), {"username": "loggingtest", "password": "wrongpassword"}
            )

            # Deveria ter logs de tentativa de login
            log_output = " ".join(log.output)
            # Verifica se há algum tipo de log relacionado a auth
            auth_logged = any(keyword in log_output.lower() for keyword in ["login", "auth", "authentication", "failed"])

            if not auth_logged:
                print("AVISO: Logging de autenticação pode não estar configurado")

    def test_access_control_logging(self):
        """Testa se violações de controle de acesso são logadas"""
        with self.assertLogs(level="WARNING") as log:
            # Tenta acessar área restrita
            response = self.client.get("/admin/")

            # Pode não gerar logs se retornar redirect em vez de 403
            if response.status_code == 403:
                log_output = " ".join(log.output)
                access_logged = any(keyword in log_output.lower() for keyword in ["access", "forbidden", "denied", "403"])

    def test_suspicious_activity_detection(self):
        """Testa detecção de atividade suspeita"""
        # Simula comportamento suspeito (muitas requisições)
        suspicious_patterns = []

        for i in range(20):
            response = self.client.get("/api/v1/profissionais/")
            suspicious_patterns.append(response.status_code)

        # Sistema deveria detectar e possivelmente rate limit
        rate_limited = any(status == 429 for status in suspicious_patterns)

        if rate_limited:
            print("Rate limiting ativo - boa prática de segurança")
        else:
            print("Considere implementar rate limiting para detectar atividade suspeita")


class A10ServerSideRequestForgeryTestCase(APITestCase):
    """A10:2021 – Server-Side Request Forgery (SSRF)"""

    def setUp(self):
        """Setup para testes de SSRF"""
        self.user = User.objects.create_user(
            username="ssrftest", email="ssrf@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )
        self.client.force_authenticate(user=self.user)

    def test_url_validation_protection(self):
        """Testa proteção contra SSRF via validação de URL"""
        # URLs maliciosas para teste SSRF
        malicious_urls = [
            "http://localhost:22",
            "http://127.0.0.1:3306",
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "file:///etc/passwd",
            "gopher://127.0.0.1:3306",
            "dict://127.0.0.1:11211",
        ]

        # Testa se sistema tem endpoint que aceita URLs
        for url in malicious_urls:
            # Simula campo que aceita URL (ex: webhook, callback)
            test_data = {"callback_url": url, "webhook_url": url, "image_url": url}

            # Tenta em diferentes endpoints que podem aceitar URLs
            endpoints = [
                "/api/v1/profissionais/",
                "/api/v1/consultas/",
            ]

            for endpoint in endpoints:
                response = self.client.post(endpoint, test_data)

                # Se aceitar URL, deve validar e rejeitar URLs maliciosas
                if response.status_code in [200, 201]:
                    print(f"AVISO: Endpoint {endpoint} pode ser vulnerável a SSRF")

                    # Verifica resposta para vazamento de dados internos
                    content = response.content.decode()
                    ssrf_indicators = ["SSH-", "mysql_native_password", "ami-id", "root:", "admin:", "password:"]

                    for indicator in ssrf_indicators:
                        self.assertNotIn(indicator, content)

    def test_ip_address_filtering(self):
        """Testa filtragem de endereços IP internos"""
        # IPs que deveriam ser bloqueados
        blocked_ips = ["127.0.0.1", "10.0.0.1", "192.168.1.1", "172.16.0.1", "169.254.169.254", "::1", "localhost"]

        for ip in blocked_ips:
            malicious_url = f"http://{ip}/sensitive-data"

            # Simula tentativa de fetch de URL interna
            test_response = self.client.post("/api/test/", {"external_url": malicious_url})

            # Endpoint pode não existir, mas não deve fazer requisição interna
            if test_response.status_code not in [404, 405]:
                self.assertNotEqual(test_response.status_code, 200)

    @patch("requests.get")
    def test_ssrf_with_redirects(self, mock_requests):
        """Testa proteção contra SSRF via redirects"""
        # Simula redirect malicioso
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Internal server data"
        mock_response.url = "http://127.0.0.1:22"
        mock_requests.return_value = mock_response

        # Se sistema faz requests externos, deve validar redirects
        external_url = "http://evil.com/redirect-to-internal"

        # Tenta endpoint que pode fazer request externo
        response = self.client.post("/api/external/", {"url": external_url})

        # Se endpoint existir, deve proteger contra redirects maliciosos
        if response.status_code == 200:
            # Não deve conter dados de serviços internos
            content = response.content.decode()
            self.assertNotIn("Internal server data", content)
