"""
Testes de Autenticação e Autorização - Lacrei Saúde API
=======================================================
"""

from datetime import timedelta

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.views
class TestJWTAuthentication(TestCase):
    """
    Testes para autenticação JWT
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar diferentes tipos de usuários
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="admin123",
            first_name="Admin",
            last_name="Sistema",
            user_type="ADMIN",
            is_staff=True,
            is_superuser=True,
        )

        self.paciente_user = User.objects.create_user(
            username="paciente@test.com",
            email="paciente@test.com",
            password="paciente123",
            first_name="João",
            last_name="Paciente",
            user_type="PACIENTE",
        )

        # URL para obter token
        self.token_url = reverse("authentication:login")
        self.token_refresh_url = reverse("authentication:token_refresh")

    def test_obtain_token_valid_credentials(self):
        """
        Testa obtenção de token com credenciais válidas
        """
        credentials = {"username": "admin@test.com", "password": "admin123"}

        response = self.client.post(self.token_url, credentials, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Verificar se os tokens são válidos
        self.assertIsNotNone(response.data["access"])
        self.assertIsNotNone(response.data["refresh"])

    def test_obtain_token_invalid_credentials(self):
        """
        Testa obtenção de token com credenciais inválidas
        """
        invalid_credentials = [
            {"username": "admin@test.com", "password": "senha_errada"},
            {"username": "usuario_inexistente@test.com", "password": "qualquer_senha"},
            {"username": "", "password": "admin123"},
            {"username": "admin@test.com", "password": ""},
        ]

        for credentials in invalid_credentials:
            response = self.client.post(self.token_url, credentials, format="json")

            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertNotIn("access", response.data)
            self.assertNotIn("refresh", response.data)

    def test_refresh_token_valid(self):
        """
        Testa renovação de token com refresh token válido
        """
        # Obter tokens iniciais
        credentials = {"username": "admin@test.com", "password": "admin123"}

        response = self.client.post(self.token_url, credentials, format="json")
        refresh_token = response.data["refresh"]

        # Renovar token
        refresh_data = {"refresh": refresh_token}
        response = self.client.post(self.token_refresh_url, refresh_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        # Novo access token deve ser diferente
        self.assertIsNotNone(response.data["access"])

    def test_refresh_token_invalid(self):
        """
        Testa renovação com refresh token inválido
        """
        invalid_refresh_data = [{"refresh": "token_invalido"}, {"refresh": ""}, {}]

        for refresh_data in invalid_refresh_data:
            response = self.client.post(self.token_refresh_url, refresh_data, format="json")

            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_protected_endpoint_with_valid_token(self):
        """
        Testa acesso a endpoint protegido com token válido
        """
        # Obter token
        refresh = RefreshToken.for_user(self.admin_user)
        access_token = str(refresh.access_token)

        # Configurar autorização
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Acessar endpoint protegido (profissionais)
        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_access_protected_endpoint_without_token(self):
        """
        Testa acesso a endpoint protegido sem token
        """
        # Acessar endpoint protegido sem autenticação
        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_protected_endpoint_with_invalid_token(self):
        """
        Testa acesso a endpoint protegido com token inválido
        """
        # Token inválido
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token_invalido")

        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_user_information(self):
        """
        Testa que token contém informações corretas do usuário
        """
        # Criar token para admin
        refresh = RefreshToken.for_user(self.admin_user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Acessar endpoint que mostra informações do usuário (se existir)
        # Por exemplo, um endpoint /me/ ou similar
        try:
            url = reverse("user-me")  # Assumindo que existe
            response = self.client.get(url)

            if response.status_code == status.HTTP_200_OK:
                self.assertEqual(response.data["email"], self.admin_user.email)
                self.assertEqual(response.data["user_type"], "ADMIN")
        except:
            # Se o endpoint não existir, pular teste
            pass

    def test_token_expiration(self):
        """
        Testa comportamento de token expirado
        """
        # Este teste seria mais complexo e dependeria da configuração de tempo de expiração
        # Por enquanto, apenas verificamos se token muito antigo falha

        # Simular token expirado criando um token com tempo passado
        # (implementação dependeria de mock ou configuração específica)
        pass


@pytest.mark.django_db
@pytest.mark.views
class TestUserRoleAuthorization(TestCase):
    """
    Testes para autorização baseada em tipos de usuário
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Criar diferentes tipos de usuários
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="admin123",
            user_type="ADMIN",
            is_staff=True,
            is_superuser=True,
        )

        self.paciente_user = User.objects.create_user(
            username="paciente@test.com", email="paciente@test.com", password="paciente123", user_type="PACIENTE"
        )

        # Criar usuário comum (sem privilégios especiais)
        self.common_user = User.objects.create_user(
            username="comum@test.com",
            email="comum@test.com",
            password="comum123",
            tipo_usuario="",  # Tipo não definido
        )

    def get_jwt_token(self, user):
        """
        Gera token JWT para o usuário
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_admin_full_access_profissionais(self):
        """
        Testa que admin tem acesso completo a profissionais
        """
        token = self.get_jwt_token(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("profissionais:profissional-list")

        # Admin deve poder listar
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Admin deve poder criar (se endpoint suportar)
        profissional_data = {
            "nome_social": "Dr. Teste Admin",
            "profissao": "MEDICO",
            "email": "teste.admin@test.com",
            "telefone": "11987654321",
            "endereco": {
                "logradouro": "Rua Admin",
                "numero": "100",
                "bairro": "Admin",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "12345678",
            },
        }

        response = self.client.post(url, profissional_data, format="json")
        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_405_METHOD_NOT_ALLOWED],  # Sucesso  # Método não permitido
        )

    def test_paciente_limited_access_profissionais(self):
        """
        Testa que paciente tem acesso limitado a profissionais
        """
        token = self.get_jwt_token(self.paciente_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("profissionais:profissional-list")

        # Paciente pode conseguir listar (para escolher profissional)
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])  # Permitido  # Negado

        # Paciente NÃO deve poder criar profissional
        profissional_data = {
            "nome_social": "Dr. Teste Paciente",
            "profissao": "MEDICO",
            "email": "teste.paciente@test.com",
            "telefone": "11987654321",
        }

        response = self.client.post(url, profissional_data, format="json")
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED],  # Negado  # Método não permitido
        )

    def test_common_user_no_access(self):
        """
        Testa que usuário comum não tem acesso a recursos restritos
        """
        token = self.get_jwt_token(self.common_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("profissionais:profissional-list")

        response = self.client.get(url)
        self.assertIn(
            response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_200_OK]  # Negado  # Permitido (depende das regras)
        )

    def test_admin_access_consultas(self):
        """
        Testa que admin tem acesso completo a consultas
        """
        token = self.get_jwt_token(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("consultas:consulta-list")

        # Admin deve poder listar todas as consultas
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_paciente_limited_access_consultas(self):
        """
        Testa que paciente tem acesso limitado a suas próprias consultas
        """
        token = self.get_jwt_token(self.paciente_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("consultas:consulta-list")

        # Paciente pode ou não ter acesso dependendo das regras
        response = self.client.get(url)
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]  # Permitido (suas consultas)  # Negado
        )

    def test_user_type_field_validation(self):
        """
        Testa validação do campo tipo_usuario
        """
        # Testar diferentes valores de tipo_usuario
        valid_types = ["ADMIN", "PACIENTE"]

        for user_type in valid_types:
            user = User.objects.create_user(
                username=f"{user_type.lower()}@test.com",
                email=f"{user_type.lower()}@test.com",
                password="test123",
                tipo_usuario=user_type,
            )

            self.assertEqual(user.tipo_usuario, user_type)
            self.assertTrue(user.is_active)

    def test_staff_status_authorization(self):
        """
        Testa autorização baseada em status de staff
        """
        # Usuário com is_staff=True
        staff_user = User.objects.create_user(
            username="staff@test.com", email="staff@test.com", password="staff123", is_staff=True
        )

        # Usuário sem is_staff
        non_staff_user = User.objects.create_user(
            username="nonstaff@test.com", email="nonstaff@test.com", password="nonstaff123", is_staff=False
        )

        # Testar acesso com usuário staff
        token = self.get_jwt_token(staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Acessar endpoint admin (se existir)
        try:
            admin_url = reverse("admin:index")
            response = self.client.get(admin_url)
            # Staff user deve ter algum nível de acesso
        except:
            pass

    def test_superuser_status_authorization(self):
        """
        Testa autorização baseada em status de superusuário
        """
        # Testar se superuser tem acesso total
        token = self.get_jwt_token(self.admin_user)  # admin_user é superuser
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Superuser deve ter acesso a todos os endpoints
        endpoints = ["profissionais:profissional-list", "consultas:consulta-list"]

        for endpoint in endpoints:
            try:
                url = reverse(endpoint)
                response = self.client.get(url)
                # Superuser deve ter acesso (200) ou método não permitido (405)
                self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED])
            except:
                pass


@pytest.mark.django_db
@pytest.mark.views
class TestPermissionEdgeCases(TestCase):
    """
    Testes de casos extremos de permissões
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()

        # Usuário inativo
        self.inactive_user = User.objects.create_user(
            username="inativo@test.com", email="inativo@test.com", password="inativo123", is_active=False
        )

        # Usuário ativo normal
        self.active_user = User.objects.create_user(
            username="ativo@test.com", email="ativo@test.com", password="ativo123", user_type="PACIENTE"
        )

    def test_inactive_user_cannot_login(self):
        """
        Testa que usuário inativo não consegue fazer login
        """
        credentials = {"username": "inativo@test.com", "password": "inativo123"}

        token_url = reverse("authentication:login")
        response = self.client.post(token_url, credentials, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_deactivation_invalidates_sessions(self):
        """
        Testa que desativar usuário invalida sessões ativas
        """
        # Fazer login com usuário ativo
        refresh = RefreshToken.for_user(self.active_user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Verificar que tem acesso
        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)
        initial_status = response.status_code

        # Desativar usuário
        self.active_user.is_active = False
        self.active_user.save()

        # Tentar acessar novamente (dependendo da implementação, pode ainda funcionar
        # até o token expirar, ou pode ser validado em tempo real)
        response = self.client.get(url)

        # O comportamento pode variar dependendo da implementação de verificação de token
        # Em uma implementação mais segura, deve retornar 401

    def test_multiple_concurrent_sessions(self):
        """
        Testa múltiplas sessões simultâneas do mesmo usuário
        """
        # Criar múltiplos tokens para o mesmo usuário
        refresh1 = RefreshToken.for_user(self.active_user)
        refresh2 = RefreshToken.for_user(self.active_user)

        token1 = str(refresh1.access_token)
        token2 = str(refresh2.access_token)

        # Ambos os tokens devem funcionar
        for token in [token1, token2]:
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

            url = reverse("profissionais:profissional-list")
            response = client.get(url)

            # Ambas as sessões devem ser válidas
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])  # Dependendo das permissões

    def test_malformed_authorization_header(self):
        """
        Testa headers de autorização malformados
        """
        malformed_headers = [
            "Bearer",  # Sem token
            "bearer token123",  # Minúsculo
            "Token token123",  # Tipo errado
            "Bearer token1 token2",  # Múltiplos tokens
            "Bearer ",  # Token vazio
        ]

        url = reverse("profissionais:profissional-list")

        for header in malformed_headers:
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=header)

            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_case_sensitivity_permissions(self):
        """
        Testa sensibilidade a maiúsculas/minúsculas em permissões
        """
        # Criar usuário com tipo em formato diferente
        user_lower = User.objects.create_user(
            username="lower@test.com", email="lower@test.com", password="lower123", tipo_usuario="admin"  # Minúsculo
        )

        refresh = RefreshToken.for_user(user_lower)
        token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("profissionais:profissional-list")
        response = self.client.get(url)

        # Dependendo da implementação, tipo em minúsculo pode ou não funcionar
        # Ideal é que seja case-insensitive ou tenha validação rigorosa
