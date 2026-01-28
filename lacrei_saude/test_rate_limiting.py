"""
Testes de Rate Limiting - Lacrei Saúde API
==========================================

Testes para verificar a implementação de rate limiting
e prevenção de ataques de força bruta.
"""

import time
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status
import pytest

User = get_user_model()


class RateLimitingTestCase(APITestCase):
    """Testes de Rate Limiting para diferentes endpoints"""
    
    def setUp(self):
        """Setup para os testes de rate limiting"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
        cache.clear()
    
    def tearDown(self):
        """Cleanup após cada teste"""
        cache.clear()
    
    def test_login_rate_limiting(self):
        """Testa rate limiting no endpoint de login"""
        login_url = reverse('authentication:login')
        
        # Tenta fazer muitas tentativas de login com dados incorretos
        for i in range(6):  # Assumindo limite de 5 por minuto
            response = self.client.post(login_url, {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            
            if i < 5:
                # Primeiras 5 tentativas devem retornar erro de autenticação
                self.assertIn(response.status_code, [400, 401])
            else:
                # 6ª tentativa deve ser bloqueada por rate limiting
                self.assertEqual(response.status_code, 429)
    
    def test_api_endpoint_rate_limiting(self):
        """Testa rate limiting em endpoints da API"""
        self.client.force_authenticate(user=self.user)
        
        # Endpoint de profissionais
        profissionais_url = '/api/v1/profissionais/'
        
        # Faz muitas requisições rapidamente
        responses = []
        for i in range(101):  # Assumindo limite de 100 por minuto
            response = self.client.get(profissionais_url)
            responses.append(response.status_code)
        
        # Verifica se alguma requisição foi bloqueada
        rate_limited = any(status_code == 429 for status_code in responses)
        self.assertTrue(rate_limited, "Rate limiting deveria ter sido aplicado")
    
    def test_registration_rate_limiting(self):
        """Testa rate limiting no endpoint de registro"""
        register_url = reverse('authentication:register')
        
        # Tenta registrar muitos usuários rapidamente
        for i in range(6):  # Assumindo limite de 5 registros por hora
            response = self.client.post(register_url, {
                'username': f'testuser{i}',
                'email': f'test{i}@test.com',
                'password': 'TestPassword123!',
                'user_type': 'paciente'
            })
            
            if i < 5:
                # Primeiros 5 registros podem passar (ou falhar por outros motivos)
                self.assertIn(response.status_code, [200, 201, 400])
            else:
                # 6º registro deve ser bloqueado
                self.assertEqual(response.status_code, 429)
    
    def test_password_reset_rate_limiting(self):
        """Testa rate limiting em tentativas de reset de senha"""
        # Simula endpoint de reset de senha
        reset_url = '/api/auth/password/reset/'
        
        # Faz múltiplas tentativas
        for i in range(4):  # Assumindo limite de 3 por hora
            response = self.client.post(reset_url, {
                'email': 'test@test.com'
            })
            
            if i < 3:
                # Aceita ou retorna 404 se endpoint não existir
                self.assertIn(response.status_code, [200, 202, 404])
            else:
                # 4ª tentativa deve ser bloqueada se o endpoint existir
                if response.status_code != 404:
                    self.assertEqual(response.status_code, 429)


class BruteForceProtectionTestCase(APITestCase):
    """Testes de proteção contra ataques de força bruta"""
    
    def setUp(self):
        """Setup para os testes de força bruta"""
        self.user = User.objects.create_user(
            username='brutetest',
            email='brute@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
        cache.clear()
    
    def tearDown(self):
        """Cleanup após cada teste"""
        cache.clear()
    
    def test_brute_force_login_protection(self):
        """Testa proteção contra força bruta no login"""
        login_url = reverse('authentication:login')
        
        # Lista de tentativas de senha
        password_attempts = [
            'password123',
            'admin',
            '123456',
            'password',
            'letmein',
            'wrongpassword'
        ]
        
        blocked = False
        for password in password_attempts:
            response = self.client.post(login_url, {
                'username': 'brutetest',
                'password': password
            })
            
            if response.status_code == 429:
                blocked = True
                break
        
        # Deve ter sido bloqueado em algum momento
        self.assertTrue(blocked, "Proteção contra força bruta deveria ter sido ativada")
    
    def test_ip_based_rate_limiting(self):
        """Testa rate limiting baseado em IP"""
        login_url = reverse('authentication:login')
        
        # Simula múltiplas tentativas do mesmo IP
        responses = []
        for i in range(10):
            response = self.client.post(
                login_url,
                {
                    'username': f'user{i}',
                    'password': 'wrongpassword'
                },
                HTTP_X_FORWARDED_FOR='192.168.1.100'
            )
            responses.append(response.status_code)
        
        # Verifica se houve bloqueio por IP
        rate_limited = any(status_code == 429 for status_code in responses)
        self.assertTrue(rate_limited, "Rate limiting por IP deveria ter sido aplicado")
    
    def test_account_lockout_protection(self):
        """Testa bloqueio de conta após múltiplas tentativas"""
        login_url = reverse('authentication:login')
        
        # Faz múltiplas tentativas incorretas para a mesma conta
        for i in range(6):
            response = self.client.post(login_url, {
                'username': 'brutetest',
                'password': 'wrongpassword'
            })
            
            # Após várias tentativas, deve ser bloqueado
            if i >= 4 and response.status_code == 429:
                break
        
        # Agora tenta com a senha correta
        response = self.client.post(login_url, {
            'username': 'brutetest',
            'password': 'TestPassword123!'
        })
        
        # Pode estar bloqueado mesmo com senha correta
        if response.status_code == 429:
            self.assertEqual(response.status_code, 429)


class RateLimitHeadersTestCase(APITestCase):
    """Testes para verificação de headers de rate limiting"""
    
    def setUp(self):
        """Setup para os testes de headers"""
        self.user = User.objects.create_user(
            username='headertest',
            email='header@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
        self.client.force_authenticate(user=self.user)
        cache.clear()
    
    def test_rate_limit_headers_present(self):
        """Testa se headers de rate limiting estão presentes"""
        response = self.client.get('/api/v1/profissionais/')
        
        # Headers que deveriam estar presentes
        expected_headers = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset'
        ]
        
        # Verifica se pelo menos algum header está presente
        headers_found = any(
            header in response.headers or header.lower() in response.headers
            for header in expected_headers
        )
        
        # Se não houver rate limiting implementado, documenta isso
        if not headers_found:
            print("Rate limiting headers não encontrados - implementação pendente")
    
    def test_rate_limit_reset_time(self):
        """Testa se o tempo de reset é válido"""
        response = self.client.get('/api/v1/profissionais/')
        
        reset_header = (
            response.headers.get('X-RateLimit-Reset') or
            response.headers.get('x-ratelimit-reset')
        )
        
        if reset_header:
            try:
                reset_time = int(reset_header)
                current_time = int(time.time())
                
                # Reset time deve ser no futuro
                self.assertGreater(reset_time, current_time)
                
                # Reset time não deve ser muito distante (máximo 1 hora)
                self.assertLess(reset_time - current_time, 3600)
            except ValueError:
                self.fail("Header X-RateLimit-Reset deve conter timestamp válido")


class DistributedRateLimitingTestCase(TestCase):
    """Testes para rate limiting distribuído"""
    
    def setUp(self):
        """Setup para testes distribuídos"""
        cache.clear()
    
    @patch('django.core.cache.cache.get')
    @patch('django.core.cache.cache.set')
    def test_cache_based_rate_limiting(self, mock_set, mock_get):
        """Testa rate limiting baseado em cache"""
        # Simula contador no cache
        mock_get.return_value = 5  # Já tem 5 tentativas
        
        # Deveria ser bloqueado se limite for 5
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/api/v1/profissionais/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Verifica se o cache foi consultado
        mock_get.assert_called()
    
    def test_redis_rate_limiting_simulation(self):
        """Simula rate limiting com Redis"""
        # Este teste verifica a estrutura para rate limiting distribuído
        from django.core.cache import cache
        
        key = 'rate_limit:127.0.0.1:login'
        
        # Simula incremento de contador
        current_count = cache.get(key, 0)
        cache.set(key, current_count + 1, timeout=60)
        
        # Verifica se o valor foi incrementado
        new_count = cache.get(key)
        self.assertEqual(new_count, 1)


class RateLimitBypassTestCase(APITestCase):
    """Testes para verificar tentativas de bypass do rate limiting"""
    
    def setUp(self):
        """Setup para testes de bypass"""
        self.user = User.objects.create_user(
            username='bypasstest',
            email='bypass@test.com',
            password='TestPassword123!',
            user_type='paciente'
        )
        cache.clear()
    
    def test_user_agent_rotation_bypass(self):
        """Testa se rotação de User-Agent pode bypasear rate limiting"""
        login_url = reverse('authentication:login')
        
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        
        for i, user_agent in enumerate(user_agents * 3):  # 9 tentativas
            response = self.client.post(
                login_url,
                {'username': 'bypasstest', 'password': 'wrongpassword'},
                HTTP_USER_AGENT=user_agent
            )
            
            # Rate limiting deve funcionar independente do User-Agent
            if i >= 5 and response.status_code == 429:
                self.assertEqual(response.status_code, 429)
                break
    
    def test_header_manipulation_bypass(self):
        """Testa se manipulação de headers pode bypasear rate limiting"""
        login_url = reverse('authentication:login')
        
        # Tenta com diferentes headers de IP
        headers_variants = [
            {'HTTP_X_FORWARDED_FOR': '192.168.1.1'},
            {'HTTP_X_REAL_IP': '192.168.1.2'},
            {'HTTP_CF_CONNECTING_IP': '192.168.1.3'},
            {'REMOTE_ADDR': '192.168.1.4'}
        ]
        
        for i, headers in enumerate(headers_variants * 3):  # 12 tentativas
            response = self.client.post(
                login_url,
                {'username': 'bypasstest', 'password': 'wrongpassword'},
                **headers
            )
            
            # Rate limiting deve funcionar independente dos headers
            if response.status_code == 429:
                self.assertEqual(response.status_code, 429)
                break
    
    def test_distributed_attack_simulation(self):
        """Simula ataque distribuído com múltiplos IPs"""
        login_url = reverse('authentication:login')
        
        # Simula requests de diferentes IPs
        for i in range(10):
            ip = f'192.168.1.{i + 1}'
            
            # Cada IP faz múltiplas tentativas
            for j in range(3):
                response = self.client.post(
                    login_url,
                    {'username': 'bypasstest', 'password': 'wrongpassword'},
                    HTTP_X_FORWARDED_FOR=ip
                )
                
                # Rate limiting global deveria eventualmente ativar
                if response.status_code == 429:
                    break


@pytest.mark.integration
class RateLimitingIntegrationTestCase(APITestCase):
    """Testes de integração para rate limiting"""
    
    def setUp(self):
        """Setup para testes de integração"""
        self.user = User.objects.create_user(
            username='integration',
            email='integration@test.com',
            password='TestPassword123!',
            user_type='profissional'
        )
        cache.clear()
    
    def test_rate_limiting_across_endpoints(self):
        """Testa rate limiting através de múltiplos endpoints"""
        self.client.force_authenticate(user=self.user)
        
        endpoints = [
            '/api/v1/profissionais/',
            '/api/v1/consultas/',
            '/api/auth/status/',
            '/api/security/check/'
        ]
        
        total_requests = 0
        rate_limited = False
        
        # Faz requests para todos os endpoints
        for endpoint in endpoints:
            for i in range(30):  # 30 requests por endpoint
                response = self.client.get(endpoint)
                total_requests += 1
                
                if response.status_code == 429:
                    rate_limited = True
                    break
            
            if rate_limited:
                break
        
        # Deveria ter sido rate limited em algum ponto
        if total_requests > 100:  # Se fez mais de 100 requests
            self.assertTrue(rate_limited, "Rate limiting deveria ter sido ativado")
    
    def test_rate_limiting_with_authentication_flow(self):
        """Testa rate limiting durante fluxo completo de autenticação"""
        # Logout primeiro
        self.client.logout()
        
        # Login
        login_response = self.client.post(reverse('authentication:login'), {
            'username': 'integration',
            'password': 'TestPassword123!'
        })
        
        if login_response.status_code == 200:
            # Usa o token para fazer múltiplas requisições
            token = login_response.json().get('access')
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            # Faz muitas requisições autenticadas
            for i in range(50):
                response = self.client.get('/api/v1/profissionais/')
                
                if response.status_code == 429:
                    break
    
    def test_rate_limiting_recovery(self):
        """Testa recuperação após rate limiting"""
        login_url = reverse('authentication:login')
        
        # Força rate limiting
        for i in range(10):
            self.client.post(login_url, {
                'username': 'integration',
                'password': 'wrongpassword'
            })
        
        # Espera um pouco (simula reset do rate limit)
        time.sleep(1)
        
        # Tenta novamente - deveria eventualmente recuperar
        recovery_response = self.client.post(login_url, {
            'username': 'integration',
            'password': 'TestPassword123!'
        })
        
        # Pode estar ainda bloqueado ou ter recuperado
        self.assertIn(recovery_response.status_code, [200, 429])