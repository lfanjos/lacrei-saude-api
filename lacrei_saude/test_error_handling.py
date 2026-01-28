"""
Testes de Tratamento de Erros e Casos Extremos - Lacrei Saúde API
================================================================
"""

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from consultas.models import Consulta
from profissionais.models import Endereco, Profissional

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.views
class TestAPIErrorHandling(TestCase):
    """
    Testes para tratamento de erros da API
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username="admin@test.com", email="admin@test.com", password="admin123", user_type="ADMIN", is_staff=True
        )

        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_malformed_json_request(self):
        """
        Testa requisição com JSON malformado
        """
        url = reverse("profissionais:profissional-list")

        # JSON inválido
        malformed_json = '{"nome_social": "Dr. Teste", "profissao":'

        response = self.client.post(url, malformed_json, content_type="application/json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_missing_content_type(self):
        """
        Testa requisição sem Content-Type correto
        """
        url = reverse("profissionais:profissional-list")

        data = {"nome_social": "Dr. Teste", "profissao": "MEDICO"}

        # Enviar como form data em vez de JSON
        response = self.client.post(url, data)

        # Pode retornar erro dependendo da configuração do parser
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE])

    def test_oversized_request_payload(self):
        """
        Testa requisição com payload muito grande
        """
        url = reverse("profissionais:profissional-list")

        # Dados com campo muito grande
        large_data = {
            "nome_social": "Dr. Teste",
            "profissao": "MEDICO",
            "email": "teste@test.com",
            "telefone": "11987654321",
            "biografia": "A" * 10000,  # Biografia muito longa
            "endereco": {
                "logradouro": "Rua Teste",
                "numero": "100",
                "bairro": "Teste",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
        }

        response = self.client.post(url, large_data, format="json")

        # Deve retornar erro de validação
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sql_injection_attempts(self):
        """
        Testa tentativas de SQL injection
        """
        url = reverse("profissionais:profissional-list")

        sql_injection_attempts = [
            "'; DROP TABLE profissionais_profissional; --",
            "1' OR '1'='1",
            "'; UPDATE profissionais_profissional SET email='hacked@test.com'; --",
            "<script>alert('xss')</script>",
            "admin@test.com'; DELETE FROM auth_user WHERE '1'='1",
        ]

        for injection in sql_injection_attempts:
            # Tentar injeção no campo email
            data = {
                "nome_social": "Dr. Injection",
                "profissao": "MEDICO",
                "email": injection,
                "telefone": "11987654321",
                "endereco": {
                    "logradouro": "Rua Injection",
                    "numero": "100",
                    "bairro": "Injection",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "cep": "12345678",
                },
            }

            response = self.client.post(url, data, format="json")

            # Deve retornar erro de validação, não executar SQL
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_xss_attempts(self):
        """
        Testa tentativas de Cross-Site Scripting (XSS)
        """
        url = reverse("profissionais:profissional-list")

        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
        ]

        for xss in xss_attempts:
            data = {
                "nome_social": xss,
                "profissao": "MEDICO",
                "email": "teste@test.com",
                "telefone": "11987654321",
                "endereco": {
                    "logradouro": "Rua Teste",
                    "numero": "100",
                    "bairro": "Teste",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "cep": "12345678",
                },
            }

            response = self.client.post(url, data, format="json")

            # Se criado com sucesso, verificar se XSS foi sanitizado
            if response.status_code == status.HTTP_201_CREATED:
                self.assertNotIn("<script>", response.data["nome_social"])
                self.assertNotIn("javascript:", response.data["nome_social"])

    def test_unicode_and_special_characters(self):
        """
        Testa caracteres especiais e Unicode
        """
        url = reverse("profissionais:profissional-list")

        special_chars_data = {
            "nome_social": "Dr. João José María ñ ç â ü 中文 🏥",
            "profissao": "MEDICO",
            "email": "unicode@test.com",
            "telefone": "11987654321",
            "endereco": {
                "logradouro": "Rua São José nº 100 ñ ç",
                "numero": "100",
                "bairro": "São João",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
        }

        response = self.client.post(url, special_chars_data, format="json")

        # Deve aceitar caracteres especiais válidos
        if response.status_code == status.HTTP_201_CREATED:
            self.assertIn("João", response.data["nome_social"])
        else:
            # Se retornar erro, deve ser erro de validação específico
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_null_byte_injection(self):
        """
        Testa injeção de null bytes
        """
        url = reverse("profissionais:profissional-list")

        null_byte_data = {
            "nome_social": "Dr. Teste\x00Injection",
            "profissao": "MEDICO",
            "email": "teste\x00@test.com",
            "telefone": "11987654321",
            "endereco": {
                "logradouro": "Rua\x00Teste",
                "numero": "100",
                "bairro": "Teste",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
        }

        response = self.client.post(url, null_byte_data, format="json")

        # Deve retornar erro ou sanitizar null bytes
        if response.status_code == status.HTTP_201_CREATED:
            self.assertNotIn("\x00", response.data["nome_social"])
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concurrent_requests(self):
        """
        Testa requisições concorrentes que podem causar condições de corrida
        """
        # Criar profissional
        endereco = Endereco.objects.create(
            logradouro="Rua Teste", numero="100", bairro="Teste", cidade="São Paulo", estado="SP", cep="12345678"
        )

        profissional = Profissional.objects.create(
            nome_social="Dr. Concorrencia",
            profissao="MEDICO",
            email="concorrencia@test.com",
            telefone="11987654321",
            endereco=endereco,
        )

        # Simular múltiplas atualizações simultâneas
        url = reverse("profissionais:profissional-detail", kwargs={"pk": profissional.pk})

        update_data = {"nome_social": "Dr. Atualizado"}

        # Em um cenário real, estas requisições seriam realmente simultâneas
        responses = []
        for i in range(5):
            response = self.client.patch(url, update_data, format="json")
            responses.append(response.status_code)

        # Pelo menos uma deve ter sucesso
        self.assertIn(status.HTTP_200_OK, responses)


@pytest.mark.django_db
@pytest.mark.views
class TestRateLimitingAndSecurity(TestCase):
    """
    Testes de rate limiting e segurança
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar usuário
        self.user = User.objects.create_user(
            username="ratelimit@test.com", email="ratelimit@test.com", password="ratelimit123", user_type="ADMIN"
        )

        # Autenticar
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_rapid_requests(self):
        """
        Testa muitas requisições rápidas (rate limiting)
        """
        url = reverse("profissionais:profissional-list")

        # Fazer muitas requisições rapidamente
        responses = []
        for i in range(100):  # 100 requisições
            response = self.client.get(url)
            responses.append(response.status_code)

            # Se rate limiting estiver ativo, deve retornar 429
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break

        # Verificar se rate limiting foi acionado ou todas passaram
        self.assertTrue(
            all(status_code == status.HTTP_200_OK for status_code in responses)
            or status.HTTP_429_TOO_MANY_REQUESTS in responses
        )

    def test_brute_force_login_attempts(self):
        """
        Testa tentativas de força bruta no login
        """
        token_url = reverse("token_obtain_pair")

        # Tentar múltiplas senhas incorretas
        responses = []
        for i in range(20):
            credentials = {"username": "ratelimit@test.com", "password": f"senha_errada_{i}"}

            response = self.client.post(token_url, credentials, format="json")
            responses.append(response.status_code)

            # Se rate limiting estiver ativo para login, deve retornar 429
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break

        # Todas as tentativas devem falhar com 401 ou rate limiting deve ser acionado
        self.assertTrue(
            all(status_code == status.HTTP_401_UNAUTHORIZED for status_code in responses)
            or status.HTTP_429_TOO_MANY_REQUESTS in responses
        )

    def test_large_file_upload_simulation(self):
        """
        Testa simulação de upload de arquivo grande
        """
        url = reverse("profissionais:profissional-list")

        # Simular upload com dados muito grandes
        large_data = {
            "nome_social": "Dr. Upload",
            "profissao": "MEDICO",
            "email": "upload@test.com",
            "telefone": "11987654321",
            "biografia": "B" * 50000,  # 50KB de texto
            "endereco": {
                "logradouro": "Rua Upload" + ("X" * 1000),
                "numero": "100",
                "bairro": "Upload",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
        }

        response = self.client.post(url, large_data, format="json")

        # Deve retornar erro por excesso de tamanho
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE])


@pytest.mark.django_db
@pytest.mark.views
class TestDataIntegrity(TestCase):
    """
    Testes de integridade de dados
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username="admin@test.com", email="admin@test.com", password="admin123", user_type="ADMIN", is_staff=True
        )

        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_foreign_key_integrity(self):
        """
        Testa integridade de chaves estrangeiras
        """
        # Tentar criar consulta com profissional inexistente
        url = reverse("consultas:consulta-list")

        invalid_data = {
            "profissional": 99999,  # ID inexistente
            "data_hora": (timezone.now() + timedelta(days=5)).isoformat(),
            "nome_paciente": "Paciente Teste",
            "telefone_paciente": "11987654321",
        }

        response = self.client.post(url, invalid_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("profissional", response.data)

    def test_unique_constraint_violation(self):
        """
        Testa violação de restrição de unicidade
        """
        # Criar primeiro profissional
        endereco = Endereco.objects.create(
            logradouro="Rua Teste", numero="100", bairro="Teste", cidade="São Paulo", estado="SP", cep="12345678"
        )

        Profissional.objects.create(
            nome_social="Dr. Primeiro", profissao="MEDICO", email="unico@test.com", telefone="11987654321", endereco=endereco
        )

        # Tentar criar segundo com mesmo email
        url = reverse("profissionais:profissional-list")

        duplicate_data = {
            "nome_social": "Dr. Segundo",
            "profissao": "MEDICO",
            "email": "unico@test.com",  # Email já existe
            "telefone": "11888777666",
            "endereco": {
                "logradouro": "Outra Rua",
                "numero": "200",
                "bairro": "Outro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "87654321",
            },
        }

        response = self.client.post(url, duplicate_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_cascade_delete_protection(self):
        """
        Testa proteção contra deleção em cascata
        """
        # Criar profissional e consulta
        endereco = Endereco.objects.create(
            logradouro="Rua Cascade", numero="100", bairro="Cascade", cidade="São Paulo", estado="SP", cep="12345678"
        )

        profissional = Profissional.objects.create(
            nome_social="Dr. Cascade", profissao="MEDICO", email="cascade@test.com", telefone="11987654321", endereco=endereco
        )

        # Criar consulta para o profissional
        consulta = Consulta.objects.create(
            profissional=profissional,
            data_hora=timezone.now() + timedelta(days=5),
            nome_paciente="Paciente Cascade",
            telefone_paciente="11987654321",
            valor_consulta=Decimal("150.00"),
        )

        # Tentar deletar profissional que tem consultas
        url = reverse("profissionais:profissional-detail", kwargs={"pk": profissional.pk})

        response = self.client.delete(url)

        # Dependendo da implementação, pode retornar erro de proteção
        # ou fazer soft delete
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            # Proteção ativa - não pode deletar profissional com consultas
            self.assertIn("profissional", str(response.data).lower())
        elif response.status_code == status.HTTP_204_NO_CONTENT:
            # Soft delete - profissional foi desativado
            profissional.refresh_from_db()
            self.assertFalse(profissional.is_active)

    def test_transaction_rollback(self):
        """
        Testa rollback de transações em caso de erro
        """
        url = reverse("profissionais:profissional-list")

        # Dados que podem passar na validação inicial mas falhar depois
        problematic_data = {
            "nome_social": "Dr. Rollback",
            "profissao": "MEDICO",
            "email": "rollback@test.com",
            "telefone": "11987654321",
            "endereco": {
                "logradouro": "Rua Rollback",
                "numero": "100",
                "bairro": "Rollback",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
            "valor_consulta": "valor_invalido",  # Tipo inválido para Decimal
        }

        # Contar profissionais antes
        count_before = Profissional.objects.count()

        response = self.client.post(url, problematic_data, format="json")

        # Deve retornar erro
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Contar profissionais depois - não deve ter criado nada
        count_after = Profissional.objects.count()
        self.assertEqual(count_before, count_after)
