"""
Configurações globais para testes - Lacrei Saúde API
===================================================
"""

import pytest
import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta

# Configuração do Django ANTES de qualquer importação Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lacrei_saude.settings_test')

import django
django.setup()

# Agora podemos importar componentes Django
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Importar modelos
from profissionais.models import Endereco, Profissional
from consultas.models import Consulta

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Fixture que fornece um cliente de API para testes
    """
    return APIClient()


@pytest.fixture
def admin_user(db):
    """
    Fixture que cria um usuário administrador
    """
    return User.objects.create_user(
        username='admin@test.com',
        email='admin@test.com',
        password='admin123',
        first_name='Admin',
        last_name='Sistema',
        tipo_usuario='ADMIN',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def paciente_user(db):
    """
    Fixture que cria um usuário paciente
    """
    return User.objects.create_user(
        username='paciente@test.com',
        email='paciente@test.com',
        password='paciente123',
        first_name='João',
        last_name='Paciente',
        tipo_usuario='PACIENTE'
    )


@pytest.fixture
def endereco_sample(db):
    """
    Fixture que cria um endereço de exemplo
    """
    return Endereco.objects.create(
        logradouro='Rua das Flores',
        numero='123',
        bairro='Centro',
        cidade='São Paulo',
        estado='SP',
        cep='01234567'
    )


@pytest.fixture
def profissional_medico(db, endereco_sample):
    """
    Fixture que cria um profissional médico
    """
    return Profissional.objects.create(
        nome_social='Dr. João Silva',
        nome_registro='João Silva Santos',
        profissao='MEDICO',
        registro_profissional='CRM123456',
        especialidade='Cardiologia',
        email='medico@test.com',
        telefone='11987654321',
        endereco=endereco_sample,
        biografia='Médico cardiologista experiente',
        aceita_convenio=True,
        valor_consulta=Decimal('150.00')
    )


@pytest.fixture
def profissional_psicologo(db, endereco_sample):
    """
    Fixture que cria um profissional psicólogo
    """
    endereco_psi = Endereco.objects.create(
        logradouro='Avenida Paulista',
        numero='1000',
        bairro='Bela Vista',
        cidade='São Paulo',
        estado='SP',
        cep='98765432'
    )
    
    return Profissional.objects.create(
        nome_social='Dra. Maria Santos',
        nome_registro='Maria Santos Lima',
        profissao='PSICOLOGO',
        registro_profissional='CRP789123',
        especialidade='Psicologia Clínica',
        email='psicologa@test.com',
        telefone='11888777666',
        endereco=endereco_psi,
        biografia='Psicóloga especializada em TCC',
        aceita_convenio=False,
        valor_consulta=Decimal('120.00')
    )


@pytest.fixture
def consulta_agendada(db, paciente_user, profissional_medico):
    """
    Fixture que cria uma consulta agendada
    """
    data_futura = timezone.now() + timedelta(days=7)
    
    return Consulta.objects.create(
        paciente=paciente_user,
        profissional=profissional_medico,
        data_consulta=data_futura,
        observacoes='Consulta de rotina',
        valor=profissional_medico.valor_consulta,
        status='AGENDADA'
    )


@pytest.fixture
def consulta_confirmada(db, paciente_user, profissional_psicologo):
    """
    Fixture que cria uma consulta confirmada
    """
    data_futura = timezone.now() + timedelta(days=3)
    
    return Consulta.objects.create(
        paciente=paciente_user,
        profissional=profissional_psicologo,
        data_consulta=data_futura,
        observacoes='Primeira sessão de terapia',
        valor=profissional_psicologo.valor_consulta,
        status='CONFIRMADA'
    )


@pytest.fixture
def jwt_token_admin(admin_user):
    """
    Fixture que gera token JWT para usuário admin
    """
    refresh = RefreshToken.for_user(admin_user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': admin_user
    }


@pytest.fixture
def jwt_token_paciente(paciente_user):
    """
    Fixture que gera token JWT para usuário paciente
    """
    refresh = RefreshToken.for_user(paciente_user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': paciente_user
    }


@pytest.fixture
def authenticated_admin_client(api_client, jwt_token_admin):
    """
    Fixture que fornece cliente autenticado como admin
    """
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {jwt_token_admin["access"]}')
    return api_client


@pytest.fixture
def authenticated_paciente_client(api_client, jwt_token_paciente):
    """
    Fixture que fornece cliente autenticado como paciente
    """
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {jwt_token_paciente["access"]}')
    return api_client


@pytest.fixture
def sample_endereco_data():
    """
    Fixture com dados de exemplo para endereço
    """
    return {
        'logradouro': 'Rua Teste',
        'numero': '100',
        'bairro': 'Bairro Teste',
        'cidade': 'São Paulo',
        'estado': 'SP',
        'cep': '12345678'
    }


@pytest.fixture
def sample_profissional_data(sample_endereco_data):
    """
    Fixture com dados de exemplo para profissional
    """
    return {
        'nome_social': 'Dr. Teste',
        'profissao': 'MEDICO',
        'email': 'teste@profissional.com',
        'telefone': '11999888777',
        'endereco': sample_endereco_data,
        'valor_consulta': '150.00'
    }


@pytest.fixture
def sample_consulta_data(paciente_user, profissional_medico):
    """
    Fixture com dados de exemplo para consulta
    """
    return {
        'paciente': paciente_user.id,
        'profissional': profissional_medico.id,
        'data_consulta': (timezone.now() + timedelta(days=5)).isoformat(),
        'observacoes': 'Consulta de teste'
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Permite acesso ao banco para todos os testes
    """
    pass


@pytest.fixture
def transactional_db(db):
    """
    Fixture para testes que precisam de transações de banco
    """
    pass


# Fixtures para dados em massa (para testes de performance)
@pytest.fixture
def multiple_profissionais(db, endereco_sample):
    """
    Fixture que cria múltiplos profissionais para testes
    """
    profissionais = []
    profissoes = ['MEDICO', 'PSICOLOGO', 'NUTRICIONISTA', 'FISIOTERAPEUTA', 'ENFERMEIRO']
    
    for i in range(10):
        profissional = Profissional.objects.create(
            nome_social=f'Dr. Teste {i+1}',
            profissao=profissoes[i % len(profissoes)],
            email=f'teste{i+1}@profissional.com',
            telefone=f'1199988877{i}',
            endereco=endereco_sample,
            valor_consulta=Decimal(f'{100 + (i * 10)}.00')
        )
        profissionais.append(profissional)
    
    return profissionais


@pytest.fixture  
def multiple_consultas(db, paciente_user, profissional_medico):
    """
    Fixture que cria múltiplas consultas para testes
    """
    consultas = []
    
    for i in range(5):
        data_consulta = timezone.now() + timedelta(days=i+1)
        consulta = Consulta.objects.create(
            paciente=paciente_user,
            profissional=profissional_medico,
            data_consulta=data_consulta,
            observacoes=f'Consulta {i+1}',
            valor=profissional_medico.valor_consulta,
            status='AGENDADA'
        )
        consultas.append(consulta)
    
    return consultas


# Marks customizados para pytest
def pytest_configure(config):
    """Configura marks customizados"""
    config.addinivalue_line(
        "markers", "slow: marca testes lentos"
    )
    config.addinivalue_line(
        "markers", "integration: marca testes de integração"
    )
    config.addinivalue_line(
        "markers", "unit: marca testes unitários"
    )
    config.addinivalue_line(
        "markers", "models: marca testes de modelos"
    )
    config.addinivalue_line(
        "markers", "serializers: marca testes de serializers"
    )
    config.addinivalue_line(
        "markers", "views: marca testes de views"
    )
    config.addinivalue_line(
        "markers", "validators: marca testes de validadores"
    )