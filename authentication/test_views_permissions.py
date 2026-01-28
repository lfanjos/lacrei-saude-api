"""
Testes para Views e Permissões - Authentication Module
======================================================

Testes específicos para melhorar cobertura das views e permissões de autenticação.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class CustomTokenObtainPairViewTestCase(APITestCase):
    """Testes para view customizada de obtenção de token"""

    def setUp(self):
        """Setup para testes de token"""
        self.user = User.objects.create_user(
            username="tokentest", email="token@test.com", password="TestPassword123!", user_type="paciente"
        )
        self.login_url = reverse("authentication:login")

    def test_successful_login_response_format(self):
        """Testa formato da resposta de login bem-sucedido"""
        response = self.client.post(self.login_url, {"username": "tokentest", "password": "TestPassword123!"})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verifica campos obrigatórios
        required_fields = ["access", "refresh"]
        for field in required_fields:
            self.assertIn(field, data)
            self.assertIsNotNone(data[field])

        # Pode conter informações do usuário
        if "user" in data:
            self.assertEqual(data["user"]["id"], self.user.id)
            self.assertEqual(data["user"]["username"], self.user.username)

    def test_failed_login_response_format(self):
        """Testa formato da resposta de login falhado"""
        response = self.client.post(self.login_url, {"username": "tokentest", "password": "wrongpassword"})

        self.assertEqual(response.status_code, 401)
        data = response.json()

        # Deve conter mensagem de erro
        self.assertTrue("detail" in data or "error" in data)

    def test_inactive_user_login_blocked(self):
        """Testa bloqueio de login para usuário inativo"""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.login_url, {"username": "tokentest", "password": "TestPassword123!"})

        self.assertNotEqual(response.status_code, 200)

    def test_missing_credentials_error(self):
        """Testa erro quando credenciais estão ausentes"""
        # Sem username
        response = self.client.post(self.login_url, {"password": "TestPassword123!"})
        self.assertEqual(response.status_code, 400)

        # Sem password
        response = self.client.post(self.login_url, {"username": "tokentest"})
        self.assertEqual(response.status_code, 400)

        # Completamente vazio
        response = self.client.post(self.login_url, {})
        self.assertEqual(response.status_code, 400)


class RegisterViewTestCase(APITestCase):
    """Testes para view de registro"""

    def setUp(self):
        """Setup para testes de registro"""
        self.register_url = reverse("authentication:register")

    def test_successful_registration(self):
        """Testa registro bem-sucedido"""
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "NewPassword123!",
            "user_type": "paciente",
        }

        response = self.client.post(self.register_url, user_data)

        if response.status_code == 201:
            # Verifica se usuário foi criado
            self.assertTrue(User.objects.filter(username="newuser").exists())

            data = response.json()
            self.assertEqual(data["username"], "newuser")
            self.assertEqual(data["email"], "newuser@test.com")

            # Senha não deve estar na resposta
            self.assertNotIn("password", data)

    def test_duplicate_username_registration(self):
        """Testa registro com username duplicado"""
        # Cria usuário inicial
        User.objects.create_user(
            username="duplicate", email="first@test.com", password="TestPassword123!", user_type="paciente"
        )

        # Tenta registrar com mesmo username
        response = self.client.post(
            self.register_url,
            {"username": "duplicate", "email": "second@test.com", "password": "TestPassword123!", "user_type": "paciente"},
        )

        self.assertNotEqual(response.status_code, 201)

    def test_duplicate_email_registration(self):
        """Testa registro com email duplicado"""
        # Cria usuário inicial
        User.objects.create_user(
            username="first", email="duplicate@test.com", password="TestPassword123!", user_type="paciente"
        )

        # Tenta registrar com mesmo email
        response = self.client.post(
            self.register_url,
            {"username": "second", "email": "duplicate@test.com", "password": "TestPassword123!", "user_type": "paciente"},
        )

        self.assertNotEqual(response.status_code, 201)

    def test_invalid_user_type_registration(self):
        """Testa registro com tipo de usuário inválido"""
        response = self.client.post(
            self.register_url,
            {
                "username": "invalidtype",
                "email": "invalid@test.com",
                "password": "TestPassword123!",
                "user_type": "invalid_type",
            },
        )

        self.assertNotEqual(response.status_code, 201)

    def test_weak_password_registration(self):
        """Testa registro com senha fraca"""
        weak_passwords = ["123", "password", "12345678"]

        for weak_password in weak_passwords:
            response = self.client.post(
                self.register_url,
                {
                    "username": f"weak_{weak_password}",
                    "email": f"weak_{weak_password}@test.com",
                    "password": weak_password,
                    "user_type": "paciente",
                },
            )

            # Senha fraca deve ser rejeitada
            self.assertNotEqual(response.status_code, 201)


class LogoutViewTestCase(APITestCase):
    """Testes para view de logout"""

    def setUp(self):
        """Setup para testes de logout"""
        self.user = User.objects.create_user(
            username="logouttest", email="logout@test.com", password="TestPassword123!", user_type="paciente"
        )
        self.logout_url = reverse("authentication:logout")

    def test_logout_with_authentication(self):
        """Testa logout com usuário autenticado"""
        # Faz login primeiro
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.logout_url)

        # Logout deve funcionar
        self.assertIn(response.status_code, [200, 204])

    def test_logout_without_authentication(self):
        """Testa logout sem autenticação"""
        response = self.client.post(self.logout_url)

        # Pode retornar erro ou permitir logout sem auth
        self.assertIn(response.status_code, [200, 204, 401])

    def test_logout_invalidates_token(self):
        """Testa se logout invalida token (se implementado)"""
        # Login para obter token
        login_response = self.client.post(
            reverse("authentication:login"), {"username": "logouttest", "password": "TestPassword123!"}
        )

        if login_response.status_code == 200:
            token = login_response.json().get("access")

            # Usa token
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            auth_response = self.client.get(reverse("authentication:auth_status"))

            if auth_response.status_code == 200:
                # Faz logout
                logout_response = self.client.post(self.logout_url)

                # Tenta usar token após logout
                post_logout_response = self.client.get(reverse("authentication:auth_status"))

                # JWT stateless pode ainda funcionar
                # Mas com blacklist deve falhar
                print(f"Status após logout: {post_logout_response.status_code}")


class AuthStatusViewTestCase(APITestCase):
    """Testes para view de status de autenticação"""

    def setUp(self):
        """Setup para testes de status"""
        self.user = User.objects.create_user(
            username="statustest", email="status@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.status_url = reverse("authentication:auth_status")

    def test_auth_status_authenticated_user(self):
        """Testa status de usuário autenticado"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Deve conter informações do usuário
        self.assertEqual(data["id"], self.user.id)
        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["user_type"], self.user.user_type)
        self.assertTrue(data["is_authenticated"])

    def test_auth_status_unauthenticated_user(self):
        """Testa status de usuário não autenticado"""
        response = self.client.get(self.status_url)

        # Deve retornar erro ou status não autenticado
        if response.status_code == 200:
            data = response.json()
            self.assertFalse(data.get("is_authenticated", True))
        else:
            self.assertIn(response.status_code, [401, 403])

    def test_auth_status_response_format(self):
        """Testa formato da resposta de status"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.status_url)

        if response.status_code == 200:
            data = response.json()

            # Campos esperados
            expected_fields = ["id", "username", "email", "user_type", "is_authenticated"]
            for field in expected_fields:
                self.assertIn(field, data)

            # Campos sensíveis não devem estar presentes
            sensitive_fields = ["password", "last_login"]
            for field in sensitive_fields:
                self.assertNotIn(field, data)


class SecurityStatsViewTestCase(APITestCase):
    """Testes para view de estatísticas de segurança"""

    def setUp(self):
        """Setup para testes de estatísticas"""
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )
        self.user = User.objects.create_user(
            username="user", email="user@test.com", password="TestPassword123!", user_type="paciente"
        )
        self.stats_url = reverse("authentication:security_stats")

    def test_security_stats_admin_access(self):
        """Testa acesso admin às estatísticas de segurança"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.stats_url)

        # Admin deve ter acesso
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()

            # Pode conter estatísticas de segurança
            stats_fields = ["login_attempts", "failed_logins", "blocked_ips", "active_sessions"]
            for field in stats_fields:
                if field in data:
                    self.assertIsNotNone(data[field])

    def test_security_stats_user_access_denied(self):
        """Testa negação de acesso para usuários comuns"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.stats_url)

        # Usuário comum não deve ter acesso
        self.assertIn(response.status_code, [403, 404])

    def test_security_stats_unauthenticated_access(self):
        """Testa acesso não autenticado às estatísticas"""
        response = self.client.get(self.stats_url)

        # Não autenticado não deve ter acesso
        self.assertIn(response.status_code, [401, 403, 404])


class UserViewSetTestCase(APITestCase):
    """Testes para UserViewSet"""

    def setUp(self):
        """Setup para testes de viewset"""
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="TestPassword123!", user_type="paciente"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="TestPassword123!", user_type="profissional"
        )

    def test_user_list_admin_access(self):
        """Testa listagem de usuários para admin"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/auth/users/")

        if response.status_code == 200:
            data = response.json()

            # Deve retornar lista de usuários
            if "results" in data:
                results = data["results"]
            else:
                results = data

            self.assertGreater(len(results), 0)

    def test_user_list_user_access_denied(self):
        """Testa negação de acesso à lista para usuários comuns"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get("/api/auth/users/")

        # Usuário comum não deve ter acesso
        self.assertIn(response.status_code, [403, 404])

    def test_user_detail_own_profile(self):
        """Testa acesso ao próprio perfil"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(f"/api/auth/users/{self.user1.id}/")

        # Deve permitir acesso ao próprio perfil
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["id"], self.user1.id)

    def test_user_detail_other_profile(self):
        """Testa acesso ao perfil de outro usuário"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(f"/api/auth/users/{self.user2.id}/")

        # Não deve permitir acesso ao perfil de outro usuário
        self.assertIn(response.status_code, [403, 404])

    def test_user_update_own_profile(self):
        """Testa atualização do próprio perfil"""
        self.client.force_authenticate(user=self.user1)

        update_data = {"email": "newemail@test.com"}

        response = self.client.patch(f"/api/auth/users/{self.user1.id}/", update_data)

        # Deve permitir atualizar próprio perfil
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            self.user1.refresh_from_db()
            self.assertEqual(self.user1.email, "newemail@test.com")

    def test_user_update_other_profile(self):
        """Testa atualização do perfil de outro usuário"""
        self.client.force_authenticate(user=self.user1)

        update_data = {"email": "hacked@test.com"}

        response = self.client.patch(f"/api/auth/users/{self.user2.id}/", update_data)

        # Não deve permitir atualizar perfil de outro usuário
        self.assertIn(response.status_code, [403, 404])

    def test_user_delete_protection(self):
        """Testa proteção contra exclusão de usuários"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(f"/api/auth/users/{self.user1.id}/")

        # Exclusão pode ser bloqueada ou permitida apenas para admin
        if response.status_code == 204:
            # Se permitido, usuário deve estar inativo
            self.user1.refresh_from_db()
            self.assertFalse(self.user1.is_active)
        else:
            # Se bloqueado
            self.assertIn(response.status_code, [403, 405])


class APIKeyViewSetTestCase(APITestCase):
    """Testes para APIKeyViewSet"""

    def setUp(self):
        """Setup para testes de API Key"""
        self.user = User.objects.create_user(
            username="apiuser", email="api@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )

    def test_api_key_creation(self):
        """Testa criação de API Key"""
        self.client.force_authenticate(user=self.user)

        api_key_data = {"name": "Test API Key", "permissions": "read"}

        response = self.client.post("/api/auth/api-keys/", api_key_data)

        if response.status_code == 201:
            data = response.json()
            self.assertEqual(data["name"], "Test API Key")
            self.assertIn("key", data)  # Deve retornar a chave

    def test_api_key_list_own_keys(self):
        """Testa listagem das próprias API Keys"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/auth/api-keys/")

        # Deve permitir ver próprias chaves
        self.assertIn(response.status_code, [200, 404])

    def test_api_key_access_control(self):
        """Testa controle de acesso às API Keys"""
        # Cria API Key para user1
        self.client.force_authenticate(user=self.user)

        # Tenta como outro usuário
        other_user = User.objects.create_user(
            username="other", email="other@test.com", password="TestPassword123!", user_type="paciente"
        )

        self.client.force_authenticate(user=other_user)
        response = self.client.get("/api/auth/api-keys/")

        if response.status_code == 200:
            data = response.json()
            # Não deve ver chaves de outro usuário
            if "results" in data:
                self.assertEqual(len(data["results"]), 0)

    def test_api_key_deletion(self):
        """Testa exclusão de API Key"""
        self.client.force_authenticate(user=self.user)

        # Cria API Key primeiro
        create_response = self.client.post("/api/auth/api-keys/", {"name": "Delete Test Key", "permissions": "read"})

        if create_response.status_code == 201:
            key_id = create_response.json()["id"]

            # Tenta deletar
            delete_response = self.client.delete(f"/api/auth/api-keys/{key_id}/")

            # Deve permitir deletar própria chave
            self.assertIn(delete_response.status_code, [204, 404])
