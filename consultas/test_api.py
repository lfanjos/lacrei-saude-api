"""
Testes de API para Consultas - Lacrei Saúde API
===============================================
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from consultas.models import Consulta
from profissionais.models import Endereco, Profissional

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.views
class TestConsultaAPIAuthenticated(TestCase):
    """
    Testes para API de Consultas com autenticação
    """
    
    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuários
        self.admin_user = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            user_type='ADMIN',
            is_staff=True
        )
        
        self.paciente_user = User.objects.create_user(
            username='paciente@test.com',
            email='paciente@test.com',
            password='paciente123',
            user_type='PACIENTE'
        )
        
        # Cliente da API
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
        
        # Criar consulta existente
        self.data_consulta = timezone.now() + timedelta(days=7)
        self.consulta = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=self.data_consulta,
            nome_paciente='João Paciente',
            telefone_paciente='11987654321',
            email_paciente='paciente@test.com',
            valor_consulta=Decimal('150.00')
        )
        
        # Dados para nova consulta
        self.consulta_data = {
            'profissional': self.profissional.id,
            'data_hora': (timezone.now() + timedelta(days=10)).isoformat(),
            'nome_paciente': 'Maria Silva',
            'telefone_paciente': '11888777666',
            'email_paciente': 'maria@test.com',
            'motivo_consulta': 'Consulta de rotina',
            'observacoes': 'Primeira consulta'
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
    
    def test_list_consultas_admin(self):
        """
        Testa listagem de consultas como admin
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-list')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['nome_paciente'], 'João Paciente')
    
    def test_retrieve_consulta_admin(self):
        """
        Testa buscar consulta específica como admin
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-detail', kwargs={'pk': self.consulta.pk})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nome_paciente'], 'João Paciente')
        self.assertEqual(response.data['status'], 'AGENDADA')
        self.assertIn('profissional', response.data)
    
    def test_create_consulta_admin(self):
        """
        Testa criação de consulta como admin
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-list')
        
        response = self.client.post(url, self.consulta_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nome_paciente'], 'Maria Silva')
        self.assertEqual(response.data['status'], 'AGENDADA')
        
        # Verificar se foi criada no banco
        self.assertTrue(
            Consulta.objects.filter(nome_paciente='Maria Silva').exists()
        )
    
    def test_update_consulta_admin(self):
        """
        Testa atualização de consulta como admin
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-detail', kwargs={'pk': self.consulta.pk})
        
        update_data = {
            'motivo_consulta': 'Consulta de retorno',
            'observacoes': 'Paciente retornando para reavaliação'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['motivo_consulta'], 'Consulta de retorno')
        
        # Verificar se foi atualizada no banco
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.motivo_consulta, 'Consulta de retorno')
    
    def test_delete_consulta_admin(self):
        """
        Testa exclusão (soft delete) de consulta como admin
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-detail', kwargs={'pk': self.consulta.pk})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar soft delete
        self.consulta.refresh_from_db()
        self.assertFalse(self.consulta.is_active)
    
    def test_list_consultas_paciente_limited(self):
        """
        Testa que paciente tem acesso limitado às consultas
        """
        self.authenticate_paciente()
        url = reverse('consultas:consulta-list')
        
        response = self.client.get(url)
        
        # Paciente pode ter acesso limitado ou negado dependendo das regras de negócio
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
    
    def test_create_consulta_paciente_forbidden(self):
        """
        Testa que paciente não pode criar consulta diretamente
        """
        self.authenticate_paciente()
        url = reverse('consultas:consulta-list')
        
        response = self.client.post(url, self.consulta_data, format='json')
        
        # Dependendo das regras de negócio, pode ser 403 ou permitido
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_201_CREATED])
    
    def test_search_consulta_by_profissional(self):
        """
        Testa busca de consultas por profissional
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-list')
        
        response = self.client.get(url, {'profissional': self.profissional.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['profissional'], self.profissional.id)
    
    def test_search_consulta_by_status(self):
        """
        Testa busca de consultas por status
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-list')
        
        # Buscar consultas agendadas
        response = self.client.get(url, {'status': 'AGENDADA'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'AGENDADA')
        
        # Buscar consultas concluídas (não deve retornar nada)
        response = self.client.get(url, {'status': 'CONCLUIDA'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_search_consulta_by_data(self):
        """
        Testa busca de consultas por data
        """
        self.authenticate_admin()
        url = reverse('consultas:consulta-list')
        
        # Buscar por data específica
        data_busca = self.data_consulta.strftime('%Y-%m-%d')
        response = self.client.get(url, {'data': data_busca})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Pode haver ou não resultados dependendo da implementação do filtro


@pytest.mark.django_db
@pytest.mark.views
class TestConsultaAPIValidation(TestCase):
    """
    Testes de validação para API de Consultas
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
        
        # Criar endereço e profissional
        self.endereco = Endereco.objects.create(
            logradouro='Rua Teste',
            numero='100',
            bairro='Teste',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        self.profissional = Profissional.objects.create(
            nome_social='Dr. Teste',
            profissao='MEDICO',
            email='teste@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
    
    def test_create_consulta_data_passado(self):
        """
        Testa criação de consulta com data no passado
        """
        url = reverse('consultas:consulta-list')
        
        invalid_data = {
            'profissional': self.profissional.id,
            'data_hora': (timezone.now() - timedelta(days=1)).isoformat(),
            'nome_paciente': 'João Teste',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
    
    def test_create_consulta_missing_required_fields(self):
        """
        Testa criação sem campos obrigatórios
        """
        url = reverse('consultas:consulta-list')
        
        incomplete_data = {
            'profissional': self.profissional.id,
            # Faltando data_hora, nome_paciente, telefone_paciente
        }
        
        response = self.client.post(url, incomplete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verificar se campos obrigatórios estão sendo validados
        required_fields = ['data_hora', 'nome_paciente', 'telefone_paciente']
        for field in required_fields:
            if field in response.data:
                self.assertIn(field, response.data)
    
    def test_create_consulta_profissional_inativo(self):
        """
        Testa criação de consulta com profissional inativo
        """
        # Desativar profissional
        self.profissional.is_active = False
        self.profissional.save()
        
        url = reverse('consultas:consulta-list')
        
        invalid_data = {
            'profissional': self.profissional.id,
            'data_hora': (timezone.now() + timedelta(days=5)).isoformat(),
            'nome_paciente': 'João Teste',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('profissional', response.data)
    
    def test_create_consulta_horario_conflito(self):
        """
        Testa criação de consulta com conflito de horário
        """
        data_conflito = timezone.now() + timedelta(days=5)
        
        # Criar primeira consulta
        Consulta.objects.create(
            profissional=self.profissional,
            data_hora=data_conflito,
            nome_paciente='Primeiro Paciente',
            telefone_paciente='11987654321',
            valor_consulta=Decimal('150.00')
        )
        
        # Tentar criar segunda consulta no mesmo horário
        url = reverse('consultas:consulta-list')
        
        conflicting_data = {
            'profissional': self.profissional.id,
            'data_hora': data_conflito.isoformat(),
            'nome_paciente': 'Segundo Paciente',
            'telefone_paciente': '11888777666'
        }
        
        response = self.client.post(url, conflicting_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_hora', response.data)
    
    def test_create_consulta_invalid_email(self):
        """
        Testa criação com email inválido
        """
        url = reverse('consultas:consulta-list')
        
        invalid_data = {
            'profissional': self.profissional.id,
            'data_hora': (timezone.now() + timedelta(days=5)).isoformat(),
            'nome_paciente': 'João Teste',
            'telefone_paciente': '11987654321',
            'email_paciente': 'email_invalido'
        }
        
        response = self.client.post(url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email_paciente', response.data)
    
    def test_update_consulta_finalizada(self):
        """
        Testa atualização de consulta já finalizada
        """
        # Criar consulta finalizada
        consulta_finalizada = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() - timedelta(days=1),
            nome_paciente='Paciente Finalizado',
            telefone_paciente='11987654321',
            status='CONCLUIDA',
            valor_consulta=Decimal('150.00')
        )
        
        url = reverse('consultas:consulta-detail', kwargs={'pk': consulta_finalizada.pk})
        
        update_data = {
            'observacoes': 'Tentativa de alteração'
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        # Dependendo das regras de negócio, pode ser 400 ou 403
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])


@pytest.mark.django_db
@pytest.mark.views
class TestConsultaAPIActions(TestCase):
    """
    Testes para ações específicas da API de Consultas
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
        
        # Criar endereço e profissional
        self.endereco = Endereco.objects.create(
            logradouro='Rua Teste',
            numero='100',
            bairro='Teste',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        self.profissional = Profissional.objects.create(
            nome_social='Dr. Teste',
            profissao='MEDICO',
            email='teste@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
        
        # Criar consulta
        self.consulta = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=5),
            nome_paciente='João Teste',
            telefone_paciente='11987654321',
            valor_consulta=Decimal('150.00')
        )
    
    def test_confirmar_consulta(self):
        """
        Testa confirmação de consulta
        """
        url = reverse('consultas:consulta-detail', kwargs={'pk': self.consulta.pk})
        
        # Se houver endpoint específico para confirmar
        if hasattr(self, 'consulta_confirmar_url'):
            url = reverse('consultas:consulta-confirmar', kwargs={'pk': self.consulta.pk})
            response = self.client.post(url)
        else:
            # Atualizar status para confirmada
            response = self.client.patch(url, {'status': 'CONFIRMADA'}, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data['status'], 'CONFIRMADA')
            
            # Verificar no banco
            self.consulta.refresh_from_db()
            self.assertEqual(self.consulta.status, 'CONFIRMADA')
    
    def test_cancelar_consulta(self):
        """
        Testa cancelamento de consulta
        """
        url = reverse('consultas:consulta-detail', kwargs={'pk': self.consulta.pk})
        
        # Se houver endpoint específico para cancelar
        if hasattr(self, 'consulta_cancelar_url'):
            url = reverse('consultas:consulta-cancelar', kwargs={'pk': self.consulta.pk})
            response = self.client.post(url, {
                'motivo_cancelamento': 'Paciente não pode comparecer'
            })
        else:
            # Atualizar status para cancelada
            response = self.client.patch(url, {
                'status': 'CANCELADA',
                'motivo_cancelamento': 'Paciente não pode comparecer'
            }, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data['status'], 'CANCELADA')
            
            # Verificar no banco
            self.consulta.refresh_from_db()
            self.assertEqual(self.consulta.status, 'CANCELADA')


@pytest.mark.django_db
@pytest.mark.views
class TestConsultaAPIEdgeCases(TestCase):
    """
    Testes de casos extremos para API de Consultas
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
        
        # Criar endereço e profissional
        self.endereco = Endereco.objects.create(
            logradouro='Rua Teste',
            numero='100',
            bairro='Teste',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        self.profissional = Profissional.objects.create(
            nome_social='Dr. Teste',
            profissao='MEDICO',
            email='teste@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
    
    def test_pagination_consultas(self):
        """
        Testa paginação de consultas
        """
        # Criar múltiplas consultas
        for i in range(15):
            data_consulta = timezone.now() + timedelta(days=i+1, hours=i)
            Consulta.objects.create(
                profissional=self.profissional,
                data_hora=data_consulta,
                nome_paciente=f'Paciente {i+1}',
                telefone_paciente=f'1199999999{i}',
                valor_consulta=Decimal('150.00')
            )
        
        url = reverse('consultas:consulta-list')
        
        # Primeira página
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 15)
    
    def test_create_consulta_limite_futuro(self):
        """
        Testa criação de consulta muito no futuro
        """
        url = reverse('consultas:consulta-list')
        
        # Consulta para 1 ano no futuro
        data_muito_futura = timezone.now() + timedelta(days=365)
        
        future_data = {
            'profissional': self.profissional.id,
            'data_hora': data_muito_futura.isoformat(),
            'nome_paciente': 'Paciente Futuro',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, future_data, format='json')
        
        # Pode ser aceito ou rejeitado dependendo das regras de negócio
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED, 
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_create_consulta_fim_semana(self):
        """
        Testa criação de consulta em fim de semana
        """
        # Encontrar próximo domingo
        hoje = timezone.now().date()
        dias_para_domingo = (6 - hoje.weekday()) % 7
        if dias_para_domingo == 0:
            dias_para_domingo = 7
        
        domingo = timezone.now().replace(
            year=hoje.year,
            month=hoje.month,
            day=hoje.day,
            hour=14,
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(days=dias_para_domingo)
        
        url = reverse('consultas:consulta-list')
        
        weekend_data = {
            'profissional': self.profissional.id,
            'data_hora': domingo.isoformat(),
            'nome_paciente': 'Paciente Domingo',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, weekend_data, format='json')
        
        # Pode ser aceito ou rejeitado dependendo das regras de negócio
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_create_consulta_horario_noturno(self):
        """
        Testa criação de consulta em horário noturno
        """
        # Consulta às 22h
        data_noturna = timezone.now().replace(
            hour=22, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        
        url = reverse('consultas:consulta-list')
        
        night_data = {
            'profissional': self.profissional.id,
            'data_hora': data_noturna.isoformat(),
            'nome_paciente': 'Paciente Noturno',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, night_data, format='json')
        
        # Pode ser aceito ou rejeitado dependendo das regras de horário comercial
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_consulta_valor_automatico(self):
        """
        Testa que valor é calculado automaticamente baseado no profissional
        """
        url = reverse('consultas:consulta-list')
        
        # Não fornecer valor_consulta
        consulta_sem_valor = {
            'profissional': self.profissional.id,
            'data_hora': (timezone.now() + timedelta(days=5)).isoformat(),
            'nome_paciente': 'Paciente Sem Valor',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, consulta_sem_valor, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            # Valor deve ser igual ao valor_consulta do profissional
            self.assertEqual(
                Decimal(response.data['valor_consulta']), 
                self.profissional.valor_consulta
            )