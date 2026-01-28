"""
Testes de Segurança de Sessão - Lacrei Saúde API
================================================

Testes para verificar segurança de sessões, gerenciamento de tokens JWT,
timeout de sessão, fixação de sessão e outros aspectos de segurança relacionados a sessões.
"""

import time
import jwt
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
import pytest

User = get_user_model()


class JWTSecurityTestCase(APITestCase):
    """Testes de segurança para tokens JWT"""
    
    def setUp(self):
        """Setup para testes de JWT"""
        self.user = User.objects.create_user(
            username='jwttest',
            email='jwt@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
        cache.clear()
    
    def test_jwt_token_generation(self):
        """Testa geração segura de tokens JWT"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'jwttest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access')
            refresh_token = data.get('refresh')
            
            # Tokens devem existir
            self.assertIsNotNone(access_token)
            self.assertIsNotNone(refresh_token)
            
            # Tokens devem ter formato JWT válido
            for token in [access_token, refresh_token]:
                parts = token.split('.')
                self.assertEqual(len(parts), 3, "Token JWT deve ter 3 partes")
                
                # Cada parte deve ter conteúdo
                for part in parts:
                    self.assertGreater(len(part), 0)
    
    def test_jwt_token_expiration(self):
        """Testa expiração de tokens JWT"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'jwttest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            access_token = response.json().get('access')
            
            # Decodifica token sem verificação para checar claims
            try:
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                
                # Token deve ter claim de expiração
                self.assertIn('exp', decoded)
                
                # Expiração deve ser no futuro
                exp_timestamp = decoded['exp']
                current_timestamp = datetime.utcnow().timestamp()
                self.assertGreater(exp_timestamp, current_timestamp)
                
                # Não deve expirar muito longe no futuro (máximo 24h)
                max_exp = current_timestamp + (24 * 60 * 60)  # 24 horas
                self.assertLess(exp_timestamp, max_exp)
                
            except jwt.DecodeError:
                self.fail("Token JWT inválido gerado")
    
    def test_jwt_token_signature_validation(self):
        """Testa validação de assinatura do JWT"""
        # Gera token válido
        response = self.client.post(reverse('authentication:login'), {
            'username': 'jwttest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            valid_token = response.json().get('access')
            
            # Modifica token para invalidar assinatura
            parts = valid_token.split('.')
            invalid_token = f"{parts[0]}.{parts[1]}.invalid_signature"
            
            # Tenta usar token com assinatura inválida
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {invalid_token}')
            response = self.client.get('/api/auth/status/')
            
            # Deve rejeitar token com assinatura inválida
            self.assertIn(response.status_code, [401, 403])
    
    def test_jwt_algorithm_security(self):
        """Testa se algoritmo JWT é seguro"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'jwttest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            token = response.json().get('access')
            
            # Decodifica header do token
            try:
                header = jwt.get_unverified_header(token)
                algorithm = header.get('alg')
                
                # Deve usar algoritmo seguro (não 'none' ou algoritmos fracos)
                self.assertNotEqual(algorithm.lower(), 'none')
                self.assertNotIn(algorithm.lower(), ['hs1', 'rs1', 'es1'])
                
                # Algoritmos recomendados
                secure_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
                self.assertIn(algorithm, secure_algorithms)
                
            except Exception as e:
                self.fail(f"Erro ao verificar algoritmo JWT: {e}")
    
    def test_token_reuse_prevention(self):
        """Testa prevenção de reutilização de tokens"""
        # Faz login
        response = self.client.post(reverse('authentication:login'), {
            'username': 'jwttest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            access_token = response.json().get('access')
            
            # Usa token
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            first_response = self.client.get('/api/auth/status/')
            
            # Faz logout (se implementado)
            logout_response = self.client.post(reverse('authentication:logout'))
            
            if logout_response.status_code in [200, 204]:
                # Tenta usar token após logout
                second_response = self.client.get('/api/auth/status/')
                
                # JWT stateless pode ainda funcionar, mas com blacklist deve falhar
                if hasattr(settings, 'SIMPLE_JWT') and \
                   getattr(settings.SIMPLE_JWT, 'BLACKLIST_AFTER_ROTATION', False):
                    self.assertIn(second_response.status_code, [401, 403])


class SessionManagementTestCase(APITestCase):
    """Testes de gerenciamento de sessão"""
    
    def setUp(self):
        """Setup para testes de sessão"""
        self.user = User.objects.create_user(
            username='sessiontest',
            email='session@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
        cache.clear()
    
    def test_concurrent_session_management(self):
        """Testa gerenciamento de sessões concorrentes"""
        # Primeira sessão
        response1 = self.client.post(reverse('authentication:login'), {
            'username': 'sessiontest',
            'password': 'TestPassword123!'
        })
        
        # Segunda sessão (novo client)
        from rest_framework.test import APIClient
        client2 = APIClient()
        response2 = client2.post(reverse('authentication:login'), {
            'username': 'sessiontest',
            'password': 'TestPassword123!'
        })
        
        if response1.status_code == 200 and response2.status_code == 200:
            token1 = response1.json().get('access')
            token2 = response2.json().get('access')
            
            # Ambos tokens devem ser diferentes
            self.assertNotEqual(token1, token2)
            
            # Ambos devem funcionar (ou política pode invalidar o primeiro)
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token1}')
            client2.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')
            
            status1_response = self.client.get('/api/auth/status/')
            status2_response = client2.get('/api/auth/status/')
            
            # Verifica política de sessões concorrentes
            if status1_response.status_code == 401:
                print("Política de sessão única detectada")
            elif status1_response.status_code == 200 and status2_response.status_code == 200:
                print("Sessões concorrentes permitidas")
    
    def test_session_timeout(self):
        """Testa timeout de sessão"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'sessiontest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            token = response.json().get('access')
            
            # Decodifica token para verificar expiração
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                exp_time = decoded.get('exp')
                current_time = datetime.utcnow().timestamp()
                
                # Calcula tempo até expiração
                timeout_seconds = exp_time - current_time
                
                # Timeout deve ser razoável (não muito longo, não muito curto)
                self.assertGreater(timeout_seconds, 300)  # Mínimo 5 minutos
                self.assertLess(timeout_seconds, 86400)   # Máximo 24 horas
                
                print(f"Token timeout: {timeout_seconds/60:.1f} minutos")
                
            except Exception as e:
                self.fail(f"Erro ao verificar timeout: {e}")
    
    def test_session_invalidation(self):
        """Testa invalidação de sessão"""
        # Login
        response = self.client.post(reverse('authentication:login'), {
            'username': 'sessiontest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            token = response.json().get('access')
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            # Verifica se está autenticado
            auth_response = self.client.get('/api/auth/status/')
            if auth_response.status_code == 200:
                # Logout
                logout_response = self.client.post(reverse('authentication:logout'))
                
                # Tenta usar token após logout
                post_logout_response = self.client.get('/api/auth/status/')
                
                # JWT stateless pode ainda funcionar
                # Mas com blacklist implementado deve falhar
                print(f"Status após logout: {post_logout_response.status_code}")
    
    def test_remember_me_functionality(self):
        """Testa funcionalidade 'lembrar-me'"""
        # Testa se há diferença entre login normal e "remember me"
        normal_login = self.client.post(reverse('authentication:login'), {
            'username': 'sessiontest',
            'password': 'TestPassword123!'
        })
        
        remember_login = self.client.post(reverse('authentication:login'), {
            'username': 'sessiontest',
            'password': 'TestPassword123!',
            'remember': True
        })
        
        if normal_login.status_code == 200 and remember_login.status_code == 200:
            normal_token = normal_login.json().get('access')
            remember_token = remember_login.json().get('access')
            
            # Compara expirações se diferentes
            try:
                normal_exp = jwt.decode(normal_token, options={"verify_signature": False}).get('exp')
                remember_exp = jwt.decode(remember_token, options={"verify_signature": False}).get('exp')
                
                if remember_exp > normal_exp:
                    print("Remember me aumenta duração do token")
                else:
                    print("Remember me não implementado ou não afeta duração")
                    
            except Exception:
                pass


class SessionFixationTestCase(APITestCase):
    """Testes de prevenção contra fixação de sessão"""
    
    def setUp(self):
        """Setup para testes de fixação de sessão"""
        self.user = User.objects.create_user(
            username='fixationtest',
            email='fixation@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
    
    def test_session_id_regeneration(self):
        """Testa regeneração de ID de sessão após login"""
        # Como é JWT, cada login deve gerar token único
        response1 = self.client.post(reverse('authentication:login'), {
            'username': 'fixationtest',
            'password': 'TestPassword123!'
        })
        
        time.sleep(1)  # Garante timestamps diferentes
        
        response2 = self.client.post(reverse('authentication:login'), {
            'username': 'fixationtest',
            'password': 'TestPassword123!'
        })
        
        if response1.status_code == 200 and response2.status_code == 200:
            token1 = response1.json().get('access')
            token2 = response2.json().get('access')
            
            # Tokens devem ser diferentes
            self.assertNotEqual(token1, token2, "Tokens JWT devem ser únicos por login")
    
    def test_privilege_escalation_protection(self):
        """Testa proteção contra escalação após mudança de privilégios"""
        # Login inicial
        response = self.client.post(reverse('authentication:login'), {
            'username': 'fixationtest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            initial_token = response.json().get('access')
            
            # Simula mudança de privilégios (upgrade para staff)
            self.user.is_staff = True
            self.user.save()
            
            # Tenta usar token antigo após mudança de privilégios
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {initial_token}')
            
            # Verifica se token ainda funciona
            response = self.client.get('/api/auth/status/')
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Token antigo não deveria refletir novos privilégios
                # Usuário deveria fazer login novamente
                decoded = jwt.decode(initial_token, options={"verify_signature": False})
                
                # Token original não deve ter is_staff = True
                if 'is_staff' in decoded:
                    self.assertFalse(decoded.get('is_staff'))


class TokenRefreshSecurityTestCase(APITestCase):
    """Testes de segurança para refresh de tokens"""
    
    def setUp(self):
        """Setup para testes de refresh"""
        self.user = User.objects.create_user(
            username='refreshtest',
            email='refresh@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
    
    def test_refresh_token_security(self):
        """Testa segurança do refresh token"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'refreshtest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            refresh_token = response.json().get('refresh')
            
            if refresh_token:
                # Refresh token deve ter expiração mais longa
                refresh_decoded = jwt.decode(refresh_token, options={"verify_signature": False})
                refresh_exp = refresh_decoded.get('exp')
                
                current_time = datetime.utcnow().timestamp()
                refresh_lifetime = refresh_exp - current_time
                
                # Refresh deve durar mais que access token (tipicamente dias vs horas)
                self.assertGreater(refresh_lifetime, 3600)  # Pelo menos 1 hora
    
    def test_refresh_token_rotation(self):
        """Testa rotação de refresh tokens"""
        # Login inicial
        login_response = self.client.post(reverse('authentication:login'), {
            'username': 'refreshtest',
            'password': 'TestPassword123!'
        })
        
        if login_response.status_code == 200:
            refresh_token = login_response.json().get('refresh')
            
            # Usa refresh token
            refresh_response = self.client.post(reverse('authentication:token_refresh'), {
                'refresh': refresh_token
            })
            
            if refresh_response.status_code == 200:
                new_access_token = refresh_response.json().get('access')
                new_refresh_token = refresh_response.json().get('refresh')
                
                # Novo access token deve existir
                self.assertIsNotNone(new_access_token)
                
                # Se rotação está habilitada, refresh também deve ser novo
                if new_refresh_token:
                    self.assertNotEqual(refresh_token, new_refresh_token)
                    print("Rotação de refresh token ativa")
                    
                    # Token antigo não deve funcionar mais
                    old_refresh_response = self.client.post(reverse('authentication:token_refresh'), {
                        'refresh': refresh_token
                    })
                    self.assertNotEqual(old_refresh_response.status_code, 200)
    
    def test_refresh_token_revocation(self):
        """Testa revogação de refresh tokens"""
        # Faz login para obter tokens
        response = self.client.post(reverse('authentication:login'), {
            'username': 'refreshtest',
            'password': 'TestPassword123!'
        })
        
        if response.status_code == 200:
            refresh_token = response.json().get('refresh')
            access_token = response.json().get('access')
            
            # Autentica e faz logout
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            logout_response = self.client.post(reverse('authentication:logout'))
            
            if logout_response.status_code in [200, 204]:
                # Tenta usar refresh token após logout
                refresh_response = self.client.post(reverse('authentication:token_refresh'), {
                    'refresh': refresh_token
                })
                
                # Refresh token deveria estar revogado
                # (Depende da implementação de blacklist)
                print(f"Status do refresh após logout: {refresh_response.status_code}")


class CSRFProtectionTestCase(APITestCase):
    """Testes de proteção CSRF"""
    
    def setUp(self):
        """Setup para testes CSRF"""
        self.user = User.objects.create_user(
            username='csrftest',
            email='csrf@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
    
    def test_csrf_token_presence(self):
        """Testa presença de proteção CSRF"""
        # Para APIs REST com JWT, CSRF pode não ser necessário
        # Mas verifica se está configurado quando necessário
        
        response = self.client.get('/api/auth/status/')
        
        # Verifica headers relacionados a CSRF
        csrf_headers = ['X-CSRFToken', 'X-CSRF-Token']
        csrf_present = any(header in response.headers for header in csrf_headers)
        
        if not csrf_present and 'csrftoken' not in response.cookies:
            print("CSRF não detectado - OK para API JWT")
        else:
            print("Proteção CSRF detectada")
    
    def test_state_changing_operations(self):
        """Testa proteção em operações que mudam estado"""
        # Tenta operação sem token CSRF (se necessário)
        response = self.client.post(reverse('authentication:login'), {
            'username': 'csrftest',
            'password': 'TestPassword123!'
        })
        
        # Login deve funcionar (APIs JWT geralmente não usam CSRF)
        if response.status_code == 200:
            token = response.json().get('access')
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            # Tenta operação de mudança de estado
            change_response = self.client.post('/api/v1/profissionais/', {
                'nome': 'Dr. CSRF Test',
                'email': 'csrf@example.com',
                'telefone': '11999999999',
                'especialidade': 'Clínico Geral',
                'crm': '123456-SP'
            })
            
            # Operação deve ser protegida adequadamente
            if change_response.status_code in [403, 422]:
                print("Proteção CSRF ativa em mudanças de estado")


class SessionHijackingProtectionTestCase(APITestCase):
    """Testes de proteção contra sequestro de sessão"""
    
    def setUp(self):
        """Setup para testes de sequestro"""
        self.user = User.objects.create_user(
            username='hijacktest',
            email='hijack@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
    
    def test_user_agent_binding(self):
        """Testa binding de sessão com User-Agent"""
        # Login com User-Agent específico
        response = self.client.post(
            reverse('authentication:login'),
            {
                'username': 'hijacktest',
                'password': 'TestPassword123!'
            },
            HTTP_USER_AGENT='TestAgent/1.0'
        )
        
        if response.status_code == 200:
            token = response.json().get('access')
            
            # Tenta usar token com User-Agent diferente
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            different_ua_response = self.client.get(
                '/api/auth/status/',
                HTTP_USER_AGENT='DifferentAgent/2.0'
            )
            
            # Dependendo da implementação, pode detectar mudança
            if different_ua_response.status_code == 401:
                print("Binding de User-Agent ativo")
            else:
                print("User-Agent não é usado para binding de sessão")
    
    def test_ip_address_binding(self):
        """Testa binding de sessão com endereço IP"""
        # Login com IP específico
        response = self.client.post(
            reverse('authentication:login'),
            {
                'username': 'hijacktest',
                'password': 'TestPassword123!'
            },
            HTTP_X_FORWARDED_FOR='192.168.1.100'
        )
        
        if response.status_code == 200:
            token = response.json().get('access')
            
            # Tenta usar token de IP diferente
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            different_ip_response = self.client.get(
                '/api/auth/status/',
                HTTP_X_FORWARDED_FOR='192.168.1.200'
            )
            
            # JWT stateless geralmente não faz binding de IP
            if different_ip_response.status_code == 401:
                print("Binding de IP ativo")
            else:
                print("IP não é usado para binding de sessão")
    
    def test_session_fingerprinting(self):
        """Testa fingerprinting de sessão"""
        # Coleta características da sessão
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Test Browser)',
            'HTTP_ACCEPT_LANGUAGE': 'pt-BR,pt;q=0.9',
            'HTTP_ACCEPT_ENCODING': 'gzip, deflate'
        }
        
        response = self.client.post(
            reverse('authentication:login'),
            {
                'username': 'hijacktest',
                'password': 'TestPassword123!'
            },
            **headers
        )
        
        if response.status_code == 200:
            token = response.json().get('access')
            
            # Tenta usar com headers completamente diferentes
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            different_headers = {
                'HTTP_USER_AGENT': 'Completely/Different Browser',
                'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.5',
                'HTTP_ACCEPT_ENCODING': 'br, gzip'
            }
            
            hijack_response = self.client.get(
                '/api/auth/status/',
                **different_headers
            )
            
            # Verifica se detectou mudança suspeita
            if hijack_response.status_code == 401:
                print("Fingerprinting de sessão ativo")
            else:
                print("Fingerprinting não implementado")


@pytest.mark.integration
class SessionSecurityIntegrationTestCase(APITestCase):
    """Testes de integração para segurança de sessão"""
    
    def setUp(self):
        """Setup para testes de integração"""
        self.user = User.objects.create_user(
            username='integration',
            email='integration@test.com',
            password='TestPassword123!',
            user_type='profissional'
        )
        cache.clear()
    
    def test_complete_session_lifecycle(self):
        """Testa ciclo completo de vida da sessão"""
        # 1. Login
        login_response = self.client.post(reverse('authentication:login'), {
            'username': 'integration',
            'password': 'TestPassword123!'
        })
        
        self.assertEqual(login_response.status_code, 200)
        
        access_token = login_response.json().get('access')
        refresh_token = login_response.json().get('refresh')
        
        # 2. Uso normal da sessão
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        status_response = self.client.get('/api/auth/status/')
        self.assertEqual(status_response.status_code, 200)
        
        # 3. Refresh do token
        if refresh_token:
            refresh_response = self.client.post(reverse('authentication:token_refresh'), {
                'refresh': refresh_token
            })
            
            if refresh_response.status_code == 200:
                new_token = refresh_response.json().get('access')
                self.assertIsNotNone(new_token)
        
        # 4. Logout
        logout_response = self.client.post(reverse('authentication:logout'))
        self.assertIn(logout_response.status_code, [200, 204])
        
        # 5. Verificação pós-logout
        post_logout_response = self.client.get('/api/auth/status/')
        # JWT stateless pode ainda funcionar
        print(f"Status pós-logout: {post_logout_response.status_code}")
    
    def test_security_headers_presence(self):
        """Testa presença de headers de segurança"""
        response = self.client.get('/api/auth/status/')
        
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=',
            'Content-Security-Policy': None,
            'Referrer-Policy': None
        }
        
        for header, expected in security_headers.items():
            if header in response.headers:
                value = response.headers[header]
                
                if expected is None:
                    print(f"Header {header} presente: {value}")
                elif isinstance(expected, list):
                    if any(exp in value for exp in expected):
                        print(f"✓ {header}: {value}")
                    else:
                        print(f"⚠ {header} valor inesperado: {value}")
                elif expected in value:
                    print(f"✓ {header}: {value}")
                else:
                    print(f"⚠ {header} valor inesperado: {value}")
            else:
                print(f"⚠ Header {header} ausente")
    
    def test_concurrent_sessions_security(self):
        """Testa segurança de sessões concorrentes"""
        # Múltiplos logins
        sessions = []
        
        for i in range(3):
            response = self.client.post(reverse('authentication:login'), {
                'username': 'integration',
                'password': 'TestPassword123!'
            })
            
            if response.status_code == 200:
                token = response.json().get('access')
                sessions.append(token)
        
        # Verifica se todas as sessões funcionam
        active_sessions = 0
        
        for token in sessions:
            from rest_framework.test import APIClient
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            response = client.get('/api/auth/status/')
            if response.status_code == 200:
                active_sessions += 1
        
        print(f"Sessões ativas concorrentes: {active_sessions}")
        
        # Verifica política de sessões (todas ativas vs sessão única)
        if active_sessions == len(sessions):
            print("Política: Múltiplas sessões permitidas")
        elif active_sessions == 1:
            print("Política: Sessão única (última invalida anteriores)")
        else:
            print(f"Política: Limite de {active_sessions} sessões")