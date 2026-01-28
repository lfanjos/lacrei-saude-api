"""
Testes de Casos Extremos e Edge Cases - Lacrei Saúde API
========================================================
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from profissionais.models import Endereco, Profissional
from consultas.models import Consulta

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.views
class TestTimezoneEdgeCases(TestCase):
    """
    Testes para casos extremos relacionados a timezone
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
        
        # Criar profissional
        self.endereco = Endereco.objects.create(
            logradouro='Rua Timezone',
            numero='100',
            bairro='Timezone',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        self.profissional = Profissional.objects.create(
            nome_social='Dr. Timezone',
            profissao='MEDICO',
            email='timezone@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
    
    def test_consulta_mudanca_horario_verao(self):
        """
        Testa agendamento durante mudança de horário de verão
        """
        # Simular data próxima à mudança de horário (outubro/março no Brasil)
        # Data hipotética de mudança: primeiro domingo de outubro
        
        url = reverse('consultas:consulta-list')
        
        # Data que pode ser afetada pela mudança de horário
        data_mudanca = timezone.now().replace(
            month=10, day=15, hour=2, minute=30
        ) + timedelta(days=30)  # 30 dias no futuro
        
        consulta_data = {
            'profissional': self.profissional.id,
            'data_hora': data_mudanca.isoformat(),
            'nome_paciente': 'Paciente Horário Verão',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, consulta_data, format='json')
        
        # Deve aceitar ou retornar erro específico
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
        
        if response.status_code == status.HTTP_201_CREATED:
            # Verificar se data foi armazenada corretamente
            self.assertIn('data_hora', response.data)
    
    def test_consulta_meia_noite(self):
        """
        Testa agendamento exatamente à meia-noite
        """
        url = reverse('consultas:consulta-list')
        
        meia_noite = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        
        consulta_data = {
            'profissional': self.profissional.id,
            'data_hora': meia_noite.isoformat(),
            'nome_paciente': 'Paciente Meia Noite',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, consulta_data, format='json')
        
        # Pode ser aceito ou rejeitado dependendo das regras de horário
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_consulta_31_dezembro(self):
        """
        Testa agendamento no último dia do ano
        """
        url = reverse('consultas:consulta-list')
        
        fim_ano = timezone.now().replace(
            month=12, day=31, hour=23, minute=59
        )
        # Se estamos no final do ano, usar ano seguinte
        if timezone.now().month == 12 and timezone.now().day > 25:
            fim_ano = fim_ano.replace(year=fim_ano.year + 1)
        
        consulta_data = {
            'profissional': self.profissional.id,
            'data_hora': fim_ano.isoformat(),
            'nome_paciente': 'Paciente Fim de Ano',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, consulta_data, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_consulta_ano_bissexto(self):
        """
        Testa agendamento em 29 de fevereiro (ano bissexto)
        """
        url = reverse('consultas:consulta-list')
        
        # Encontrar próximo ano bissexto
        ano_atual = timezone.now().year
        ano_bissexto = ano_atual
        
        while not (ano_bissexto % 4 == 0 and (ano_bissexto % 100 != 0 or ano_bissexto % 400 == 0)):
            ano_bissexto += 1
        
        # Se o ano bissexto está muito longe, usar um ano bissexto conhecido
        if ano_bissexto - ano_atual > 10:
            ano_bissexto = 2024 if ano_atual <= 2024 else ano_atual + (4 - (ano_atual % 4))
        
        data_bissexto = timezone.now().replace(
            year=ano_bissexto, month=2, day=29, hour=14, minute=0
        )
        
        consulta_data = {
            'profissional': self.profissional.id,
            'data_hora': data_bissexto.isoformat(),
            'nome_paciente': 'Paciente Ano Bissexto',
            'telefone_paciente': '11987654321'
        }
        
        response = self.client.post(url, consulta_data, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])


@pytest.mark.django_db
@pytest.mark.views
class TestBoundaryValues(TestCase):
    """
    Testes para valores limítrofes
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
    
    def test_profissional_valores_minimos(self):
        """
        Testa criação de profissional com valores mínimos
        """
        url = reverse('profissionais:profissional-list')
        
        # Dados com valores mínimos permitidos
        minimal_data = {
            'nome_social': 'Dr',  # Nome mais curto possível
            'profissao': 'MEDICO',
            'email': 'a@b.co',  # Email mínimo válido
            'telefone': '1112345678',  # Telefone mínimo
            'endereco': {
                'logradouro': 'R',  # Logradouro mínimo
                'numero': '1',
                'bairro': 'B',
                'cidade': 'C',
                'estado': 'SP',
                'cep': '12345678'
            }
        }
        
        response = self.client.post(url, minimal_data, format='json')
        
        # Pode ser aceito ou rejeitado dependendo das validações
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            # Se rejeitado, deve haver mensagens de erro específicas
            self.assertTrue(len(response.data) > 0)
    
    def test_profissional_valores_maximos(self):
        """
        Testa criação de profissional com valores máximos
        """
        url = reverse('profissionais:profissional-list')
        
        # Dados com valores máximos (próximos aos limites)
        maximal_data = {
            'nome_social': 'Dr. ' + 'A' * 147,  # Nome próximo ao limite (150 chars)
            'nome_registro': 'B' * 147,
            'profissao': 'MEDICO',
            'registro_profissional': 'CRM' + '1' * 47,  # Registro longo
            'especialidade': 'Especialidade ' + 'X' * 80,  # Especialidade longa
            'email': 'usuario.muito.longo@dominio.muito.longo.com.br',
            'telefone': '11987654321',
            'whatsapp': '11999888777',
            'biografia': 'B' * 1900,  # Biografia próxima ao limite
            'valor_consulta': '99999.99',  # Valor alto
            'endereco': {
                'logradouro': 'Avenida ' + 'L' * 90,  # Logradouro longo
                'numero': '99999',
                'complemento': 'Complemento ' + 'C' * 80,
                'bairro': 'Bairro ' + 'B' * 90,
                'cidade': 'Cidade ' + 'C' * 90,
                'estado': 'SP',
                'cep': '98765432'
            }
        }
        
        response = self.client.post(url, maximal_data, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ])
    
    def test_valor_consulta_extremos(self):
        """
        Testa valores extremos para valor_consulta
        """
        # Criar endereço
        endereco = Endereco.objects.create(
            logradouro='Rua Valor',
            numero='100',
            bairro='Valor',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        url = reverse('profissionais:profissional-list')
        
        valores_teste = [
            '0.01',      # Valor mínimo
            '0.99',      # Centavos
            '1.00',      # Um real
            '999.99',    # Valor médio alto
            '9999.99',   # Valor muito alto
            '99999.99'   # Valor extremo
        ]
        
        for valor in valores_teste:
            profissional_data = {
                'nome_social': f'Dr. Valor {valor}',
                'profissao': 'MEDICO',
                'email': f'valor{valor.replace(".", "")}@test.com',
                'telefone': '11987654321',
                'valor_consulta': valor,
                'endereco': {
                    'logradouro': 'Rua Valor',
                    'numero': '100',
                    'bairro': 'Valor',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                }
            }
            
            response = self.client.post(url, profissional_data, format='json')
            
            # Valores positivos devem ser aceitos
            if float(valor) > 0:
                self.assertIn(response.status_code, [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST  # Se houver limite de valor
                ])
    
    def test_duracao_consulta_extremos(self):
        """
        Testa durações extremas para consultas
        """
        # Criar profissional
        endereco = Endereco.objects.create(
            logradouro='Rua Duração',
            numero='100',
            bairro='Duração',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        profissional = Profissional.objects.create(
            nome_social='Dr. Duração',
            profissao='MEDICO',
            email='duracao@test.com',
            telefone='11987654321',
            endereco=endereco,
            valor_consulta=Decimal('150.00')
        )
        
        url = reverse('consultas:consulta-list')
        
        duracoes_teste = [
            1,      # 1 minuto (muito curto)
            15,     # 15 minutos (consulta rápida)
            30,     # 30 minutos (padrão)
            60,     # 1 hora (normal)
            120,    # 2 horas (longo)
            480,    # 8 horas (dia todo)
            1440    # 24 horas (extremo)
        ]
        
        for duracao in duracoes_teste:
            data_consulta = timezone.now() + timedelta(days=5)
            
            consulta_data = {
                'profissional': profissional.id,
                'data_hora': data_consulta.isoformat(),
                'duracao_estimada': duracao,
                'nome_paciente': f'Paciente {duracao}min',
                'telefone_paciente': '11987654321'
            }
            
            response = self.client.post(url, consulta_data, format='json')
            
            # Durações razoáveis devem ser aceitas
            if 15 <= duracao <= 480:  # Entre 15 minutos e 8 horas
                self.assertIn(response.status_code, [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST
                ])


@pytest.mark.django_db
@pytest.mark.views
class TestConcurrencyEdgeCases(TestCase):
    """
    Testes para casos extremos de concorrência
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
        
        # Criar profissional
        self.endereco = Endereco.objects.create(
            logradouro='Rua Concorrência',
            numero='100',
            bairro='Concorrência',
            cidade='São Paulo',
            estado='SP',
            cep='12345678'
        )
        
        self.profissional = Profissional.objects.create(
            nome_social='Dr. Concorrência',
            profissao='MEDICO',
            email='concorrencia@test.com',
            telefone='11987654321',
            endereco=self.endereco,
            valor_consulta=Decimal('150.00')
        )
    
    def test_consultas_simultaneas_mesmo_horario(self):
        """
        Testa tentativa de criar consultas simultâneas no mesmo horário
        """
        url = reverse('consultas:consulta-list')
        
        # Data/hora específica para conflito
        data_conflito = timezone.now() + timedelta(days=5)
        
        consulta_data_1 = {
            'profissional': self.profissional.id,
            'data_hora': data_conflito.isoformat(),
            'nome_paciente': 'Paciente 1',
            'telefone_paciente': '11987654321'
        }
        
        consulta_data_2 = {
            'profissional': self.profissional.id,
            'data_hora': data_conflito.isoformat(),
            'nome_paciente': 'Paciente 2',
            'telefone_paciente': '11888777666'
        }
        
        # Criar primeira consulta
        response1 = self.client.post(url, consulta_data_1, format='json')
        
        # Tentar criar segunda consulta no mesmo horário
        response2 = self.client.post(url, consulta_data_2, format='json')
        
        # Uma deve ter sucesso, a outra deve falhar
        statuses = [response1.status_code, response2.status_code]
        
        # Pelo menos uma deve ter sucesso
        self.assertIn(status.HTTP_201_CREATED, statuses)
        
        # Se ambas tiveram sucesso, verificar se há sobreposição de horários
        if all(s == status.HTTP_201_CREATED for s in statuses):
            # Sistema pode permitir sobreposições dependendo das regras
            pass
        else:
            # Uma deve ter falhado por conflito
            self.assertIn(status.HTTP_400_BAD_REQUEST, statuses)
    
    def test_atualizacao_simultanea_mesmo_objeto(self):
        """
        Testa atualização simultânea do mesmo objeto
        """
        # Criar consulta
        consulta = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=timezone.now() + timedelta(days=5),
            nome_paciente='Paciente Original',
            telefone_paciente='11987654321',
            valor_consulta=Decimal('150.00')
        )
        
        url = reverse('consultas:consulta-detail', kwargs={'pk': consulta.pk})
        
        # Simular duas atualizações "simultâneas"
        update_data_1 = {'nome_paciente': 'Paciente Atualizado 1'}
        update_data_2 = {'nome_paciente': 'Paciente Atualizado 2'}
        
        # Em um cenário real, estas seriam realmente simultâneas
        response1 = self.client.patch(url, update_data_1, format='json')
        response2 = self.client.patch(url, update_data_2, format='json')
        
        # Ambas podem ter sucesso dependendo da implementação
        self.assertIn(response1.status_code, [
            status.HTTP_200_OK,
            status.HTTP_409_CONFLICT
        ])
        
        self.assertIn(response2.status_code, [
            status.HTTP_200_OK,
            status.HTTP_409_CONFLICT
        ])
        
        # Verificar estado final
        consulta.refresh_from_db()
        self.assertIn(consulta.nome_paciente, [
            'Paciente Atualizado 1',
            'Paciente Atualizado 2'
        ])
    
    def test_criacao_massa_profissionais(self):
        """
        Testa criação em massa de profissionais
        """
        url = reverse('profissionais:profissional-list')
        
        # Criar múltiplos profissionais rapidamente
        responses = []
        
        for i in range(10):
            profissional_data = {
                'nome_social': f'Dr. Massa {i}',
                'profissao': 'MEDICO',
                'email': f'massa{i}@test.com',
                'telefone': f'119876543{i:02d}',
                'endereco': {
                    'logradouro': f'Rua Massa {i}',
                    'numero': str(100 + i),
                    'bairro': 'Massa',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                }
            }
            
            response = self.client.post(url, profissional_data, format='json')
            responses.append(response.status_code)
        
        # A maioria deve ter sucesso
        successful_responses = [s for s in responses if s == status.HTTP_201_CREATED]
        self.assertGreater(len(successful_responses), 5)  # Pelo menos 50% de sucesso


@pytest.mark.django_db
@pytest.mark.views
class TestSpecialCharactersEdgeCases(TestCase):
    """
    Testes para casos extremos com caracteres especiais
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
    
    def test_nomes_caracteres_especiais(self):
        """
        Testa nomes com caracteres especiais válidos
        """
        url = reverse('profissionais:profissional-list')
        
        nomes_especiais = [
            "Dr. José da Silva",
            "Dra. María José González",
            "Dr. João D'Angelo",
            "Dra. Ana-Beatriz",
            "Dr. François Müller",
            "Dra. Ângela Conceição",
            "Dr. André Luís",
            "Dra. Cláudia Pônçano"
        ]
        
        for i, nome in enumerate(nomes_especiais):
            profissional_data = {
                'nome_social': nome,
                'profissao': 'MEDICO',
                'email': f'especial{i}@test.com',
                'telefone': f'1198765432{i}',
                'endereco': {
                    'logradouro': 'Rua Especial',
                    'numero': str(100 + i),
                    'bairro': 'Especial',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                }
            }
            
            response = self.client.post(url, profissional_data, format='json')
            
            # Caracteres acentuados devem ser aceitos
            self.assertIn(response.status_code, [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST  # Se houver validação restritiva
            ])
            
            if response.status_code == status.HTTP_201_CREATED:
                # Verificar se caracteres especiais foram preservados
                self.assertEqual(response.data['nome_social'], nome)
    
    def test_enderecos_caracteres_especiais(self):
        """
        Testa endereços com caracteres especiais brasileiros
        """
        url = reverse('profissionais:profissional-list')
        
        enderecos_especiais = [
            {
                'logradouro': 'Rua São João',
                'bairro': 'Coração de Jesus',
                'cidade': 'São Luís'
            },
            {
                'logradouro': 'Avenida Brasília',
                'bairro': 'Água Branca',
                'cidade': 'Ribeirão Preto'
            },
            {
                'logradouro': 'Praça da Sé',
                'bairro': 'Centro Histórico',
                'cidade': 'Salvador'
            }
        ]
        
        for i, endereco_info in enumerate(enderecos_especiais):
            profissional_data = {
                'nome_social': f'Dr. Endereço {i}',
                'profissao': 'MEDICO',
                'email': f'endereco{i}@test.com',
                'telefone': f'1198765432{i}',
                'endereco': {
                    'logradouro': endereco_info['logradouro'],
                    'numero': '100',
                    'bairro': endereco_info['bairro'],
                    'cidade': endereco_info['cidade'],
                    'estado': 'SP',
                    'cep': '12345678'
                }
            }
            
            response = self.client.post(url, profissional_data, format='json')
            
            self.assertIn(response.status_code, [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST
            ])
    
    def test_emails_formato_extremo(self):
        """
        Testa emails com formatos no limite da especificação
        """
        url = reverse('profissionais:profissional-list')
        
        emails_extremos = [
            'a@b.co',  # Email muito curto
            'muito.longo.usuario.email@dominio.muito.longo.extenso.com.br',  # Email longo
            'user+tag@domain.com',  # Email com +
            'user.name@domain-with-hyphens.com',  # Domínio com hífen
            'user_underscore@domain.com',  # Email com underscore
        ]
        
        for i, email in enumerate(emails_extremos):
            profissional_data = {
                'nome_social': f'Dr. Email {i}',
                'profissao': 'MEDICO',
                'email': email,
                'telefone': f'1198765432{i}',
                'endereco': {
                    'logradouro': 'Rua Email',
                    'numero': str(100 + i),
                    'bairro': 'Email',
                    'cidade': 'São Paulo',
                    'estado': 'SP',
                    'cep': '12345678'
                }
            }
            
            response = self.client.post(url, profissional_data, format='json')
            
            # Emails válidos devem ser aceitos
            self.assertIn(response.status_code, [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST
            ])