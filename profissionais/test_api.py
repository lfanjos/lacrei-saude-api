"""
Testes de API para Profissionais - Lacrei Saúde API
===================================================
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from profissionais.models import Endereco, Profissional

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.views
class TestProfissionalAPIAuthenticated(TestCase):
    """
    Testes para API de Profissionais com autenticação
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário administrador
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        # Criar usuário paciente
        self.paciente_user = User.objects.create_user(
            username='paciente@test.com',
            email='paciente@test.com',
            password='paciente123',
            user_type='PACIENTE'
        )
        
        # Cliente da API
        self.client = APIClient()
        
        # Criar endereço
        self.endereco = Endereco.objects.create(
            logradouro='Rua das Flores',
            numero='123',
            bairro='Centro',
            cidade='São Paulo',
            estado='SP',
            cep='01234567'
        )
        
        # Criar profissional existente
        self.profissional = Profissional.objects.create(
            nome_social='Dr. João Silva',
            profissao='MEDICO',
            email='joao@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
        
        # Dados para criar novo profissional
        self.profissional_data = {
            'nome_social': 'Dra. Maria Santos',
            'profissao': 'PSICOLOGO',
            'email': 'maria@test.com',
            'telefone': '11888777666',
            'endereco': {
                'logradouro': 'Avenida Paulista',
                'numero': '1000',
                'bairro': 'Bela Vista',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '98765432'
            },
            'valor_consulta': '120.00'
        }
    
    def get_jwt_token(self, user):
        """
        Gera token JWT para o usuário
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_admin(self):
        """
        Autentica como administrador
        """
        token = self.get_jwt_token(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def authenticate_paciente(self):
        """
        Autentica como paciente
        """
        token = self.get_jwt_token(self.paciente_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_list_profissionais_authenticated(self):
        """
        Testa listagem de profissionais com autenticação
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['nome_social'], 'Dr. João Silva')
    
    def test_retrieve_profissional_authenticated(self):
        """
        Testa buscar profissional específico
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-detail', kwargs={'pk': self.profissional.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome_social'], 'Dr. João Silva')
        self.assertEqual(response.data['email'], 'joao@test.com')
        self.assertIn('endereco', response.data)
    
    def test_create_profissional_admin(self):
        """
        Testa criação de profissional como admin
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-list')
        
        response = self.client.post(url, self.profissional_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nome_social'], 'Dra. Maria Santos')
        self.assertEqual(response.data['profissao'], 'PSICOLOGO')
        
        # Verificar se foi criado no banco
        self.assertTrue(
            Profissional.objects.filter(email='maria@test.com').exists()
        )
    
    def test_update_profissional_admin(self):
        """
        Testa atualização de profissional como admin
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-detail', kwargs={'pk': self.profissional.pk})
        
        update_data = {
            'nome_social': 'Dr. João Silva Atualizado',
            'especialidade': 'Cardiologia Avançada'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome_social'], 'Dr. João Silva Atualizado')
        
        # Verificar se foi atualizado no banco
        self.profissional.refresh_from_db()
        self.assertEqual(self.profissional.nome_social, 'Dr. João Silva Atualizado')
    
    def test_delete_profissional_admin(self):
        """
        Testa exclusão (soft delete) de profissional como admin
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-detail', kwargs={'pk': self.profissional.pk})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar soft delete
        self.profissional.refresh_from_db()
        self.assertFalse(self.profissional.is_active)
    
    def test_create_profissional_paciente_forbidden(self):
        """
        Testa que paciente não pode criar profissional
        """
        self.authenticate_paciente()
        url = reverse('profissionais:profissional-list')
        
        response = self.client.post(url, self.profissional_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_profissional_paciente_forbidden(self):
        """
        Testa que paciente não pode atualizar profissional
        """
        self.authenticate_paciente()
        url = reverse('profissionais:profissional-detail', kwargs={'pk': self.profissional.pk})
        
        update_data = {'nome_social': 'Tentativa de alteração'}
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_profissionais_paciente_read_only(self):
        """
        Testa que paciente pode listar profissionais (somente leitura)
        """
        self.authenticate_paciente()
        url = reverse('profissionais:profissional-list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_search_profissional_by_profissao(self):
        """
        Testa busca de profissional por profissão
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-list')
        
        # Buscar médicos
        response = self.client.get(url, {'profissao': 'MEDICO'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['profissao'], 'MEDICO')
        
        # Buscar psicólogos (não deve retornar nada)
        response = self.client.get(url, {'profissao': 'PSICOLOGO'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_search_profissional_by_cidade(self):
        """
        Testa busca de profissional por cidade
        """
        self.authenticate_admin()
        url = reverse('profissionais:profissional-list')
        
        response = self.client.get(url, {'cidade': 'São Paulo'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


@pytest.mark.django_db
@pytest.mark.views
class TestProfissionalAPIUnauthenticated(TestCase):
    """
    Testes para API de Profissionais sem autenticação
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.client = APIClient()
        
        # Criar endereço e profissional
        self.endereco = Endereco.objects.create(
            logradouro='Rua das Flores',
            numero='123',
            bairro='Centro',
            cidade='São Paulo',
            estado='SP',
            cep='01234567'
        )
        
        self.profissional = Profissional.objects.create(
            nome_social='Dr. João Silva',
            profissao='MEDICO',
            email='joao@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
    
    def test_list_profissionais_unauthenticated(self):
        """
        Testa que listagem requer autenticação
        """
        url = reverse('profissionais:profissional-list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_profissional_unauthenticated(self):
        """
        Testa que criação requer autenticação
        """
        url = reverse('profissionais:profissional-list')
        
        profissional_data = {
            'nome_social': 'Dr. Teste',
            'profissao': 'MEDICO',
            'email': 'teste@test.com',
            'telefone': '11999888777'
        }
        
        response = self.client.post(url, profissional_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_profissional_unauthenticated(self):
        """
        Testa que buscar detalhes requer autenticação
        """
        url = reverse('profissionais:profissional-detail', kwargs={'pk': self.profissional.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@pytest.mark.django_db
@pytest.mark.views
class TestProfissionalAPIValidation(TestCase):
    """
    Testes de validação para API de Profissionais
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.client = APIClient()
        
        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_create_profissional_invalid_email(self):
        """
        Testa criação com email inválido
        """
        url = reverse('profissionais:profissional-list')
        
        invalid_data = {
            'nome_social': 'Dr. Teste',
            'profissao': 'MEDICO',
            'email': 'email_invalido',
            'telefone': '11987654321',
            'endereco': {
                'logradouro': 'Rua Teste',
                'numero': '100',
                'bairro': 'Teste',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '12345678'
            }
        }
        
        response = self.client.post(url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_create_profissional_missing_required_fields(self):
        """
        Testa criação sem campos obrigatórios
        """
        url = reverse('profissionais:profissional-list')
        
        incomplete_data = {
            'nome_social': 'Dr. Teste',
            # Faltando profissao, email, telefone, endereco
        }
        
        response = self.client.post(url, incomplete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verificar se campos obrigatórios estão sendo validados
        required_fields = ['profissao', 'email', 'telefone', 'endereco']
        for field in required_fields:
            if field in response.data:
                self.assertIn(field, response.data)
    
    def test_create_profissional_invalid_profissao(self):
        """
        Testa criação com profissão inválida
        """
        url = reverse('profissionais:profissional-list')
        
        invalid_data = {
            'nome_social': 'Dr. Teste',
            'profissao': 'PROFISSAO_INEXISTENTE',
            'email': 'teste@test.com',
            'telefone': '11987654321',
            'endereco': {
                'logradouro': 'Rua Teste',
                'numero': '100',
                'bairro': 'Teste',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '12345678'
            }
        }
        
        response = self.client.post(url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('profissao', response.data)
    
    def test_create_profissional_duplicate_email(self):
        """
        Testa criação com email duplicado
        """
        # Criar primeiro profissional
        endereco = Endereco.objects.create(
            logradouro='Rua Teste',
            numero='100',
            bairro='Teste',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        Profissional.objects.create(
            nome_social='Dr. Primeiro',
            profissao='MEDICO',
            email='teste@test.com',
            telefone='11987654321',
            endereco=endereco
        )
        
        # Tentar criar segundo com mesmo email
        url = reverse('profissionais:profissional-list')
        
        duplicate_data = {
            'nome_social': 'Dr. Segundo',
            'profissao': 'MEDICO',
            'email': 'teste@test.com',  # Email duplicado
            'telefone': '11888777666',
            'endereco': {
                'logradouro': 'Outra Rua',
                'numero': '200',
                'bairro': 'Outro Bairro',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '87654321'
            }
        }
        
        response = self.client.post(url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_update_profissional_invalid_data(self):
        """
        Testa atualização com dados inválidos
        """
        # Criar profissional
        endereco = Endereco.objects.create(
            logradouro='Rua Teste',
            numero='100',
            bairro='Teste',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        profissional = Profissional.objects.create(
            nome_social='Dr. Teste',
            profissao='MEDICO',
            email='teste@test.com',
            telefone='11987654321',
            endereco=endereco
        )
        
        url = reverse('profissionais:profissional-detail', kwargs={'pk': profissional.pk})
        
        invalid_update = {
            'valor_consulta': '-50.00'  # Valor negativo
        }
        
        response = self.client.patch(url, invalid_update, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('valor_consulta', response.data)
    
    def test_retrieve_nonexistent_profissional(self):
        """
        Testa buscar profissional que não existe
        """
        url = reverse('profissionais:profissional-detail', kwargs={'pk': 99999})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
@pytest.mark.views
class TestProfissionalAPIEdgeCases(TestCase):
    """
    Testes de casos extremos para API de Profissionais
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário admin
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.client = APIClient()
        
        # Autenticar
        refresh = RefreshToken.for_user(self.admin_user)
        token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_pagination_profissionais(self):
        """
        Testa paginação de profissionais
        """
        # Criar múltiplos profissionais
        endereco = Endereco.objects.create(
            logradouro='Rua Teste',
            numero='100',
            bairro='Teste',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        for i in range(15):
            Profissional.objects.create(
                nome_social=f'Dr. Teste {i+1}',
                profissao='MEDICO',
                email=f'teste{i+1}@test.com',
                telefone=f'1199999999{i}',
                endereco=endereco
            )
        
        url = reverse('profissionais:profissional-list')
        
        # Primeira página
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('next', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 15)
    
    def test_filter_profissionais_multiple_criteria(self):
        """
        Testa filtros combinados
        """
        # Criar profissionais com diferentes características
        endereco_sp = Endereco.objects.create(
            logradouro='Rua SP',
            numero='100',
            bairro='Centro',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        endereco_rj = Endereco.objects.create(
            logradouro='Rua RJ',
            numero='200',
            bairro='Copacabana',
            cidade='Rio de Janeiro',
            estado='RJ',
            cep='87654321'
        )
        
        Profissional.objects.create(
            nome_social='Dr. Médico SP',
            profissao='MEDICO',
            email='medico.sp@test.com',
            telefone='11987654321',
            endereco=endereco_sp
        )
        
        Profissional.objects.create(
            nome_social='Dr. Psicólogo SP',
            profissao='PSICOLOGO',
            email='psi.sp@test.com',
            telefone='11888777666',
            endereco=endereco_sp
        )
        
        Profissional.objects.create(
            nome_social='Dr. Médico RJ',
            profissao='MEDICO',
            email='medico.rj@test.com',
            telefone='21987654321',
            endereco=endereco_rj
        )
        
        url = reverse('profissionais:profissional-list')
        
        # Filtrar médicos em São Paulo
        response = self.client.get(url, {
            'profissao': 'MEDICO',
            'cidade': 'São Paulo'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['nome_social'], 'Dr. Médico SP')
    
    def test_create_profissional_with_minimal_data(self):
        """
        Testa criação com dados mínimos obrigatórios
        """
        url = reverse('profissionais:profissional-list')
        
        minimal_data = {
            'nome_social': 'Dr. Mínimo',
            'profissao': 'MEDICO',
            'email': 'minimo@test.com',
            'telefone': '11987654321',
            'endereco': {
                'logradouro': 'Rua Mínima',
                'numero': '1',
                'bairro': 'Mínimo',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '12345678'
            }
        }
        
        response = self.client.post(url, minimal_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nome_social'], 'Dr. Mínimo')
    
    def test_large_payload_profissional(self):
        """
        Testa criação com payload grande (biografia longa)
        """
        url = reverse('profissionais:profissional-list')
        
        large_data = {
            'nome_social': 'Dr. Biografia Longa',
            'profissao': 'MEDICO',
            'email': 'longo@test.com',
            'telefone': '11987654321',
            'biografia': 'A' * 1900,  # Biografia próxima do limite
            'endereco': {
                'logradouro': 'Rua Longa',
                'numero': '999',
                'bairro': 'Longo',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '12345678'
            }
        }
        
        response = self.client.post(url, large_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['biografia']), 1900)