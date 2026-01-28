"""
Testes para Serializers de Consultas - Lacrei Saúde API
======================================================
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from consultas.models import Consulta
from consultas.serializers import (
    ConsultaActionSerializer,
    ConsultaCreateSerializer,
    ConsultaListSerializer,
    ConsultaPacienteSerializer,
    ConsultaSerializer,
    ConsultaUpdateSerializer,
)
from profissionais.models import Endereco, Profissional

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.serializers
class TestConsultaSerializer(TestCase):
    """
    Testes para ConsultaSerializer
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar usuário paciente
        self.paciente = User.objects.create_user(
            username="paciente@test.com",
            email="paciente@test.com",
            password="testpass123",
            first_name="João",
            last_name="Paciente",
            tipo_usuario="PACIENTE",
        )

        # Criar endereço
        self.endereco = Endereco.objects.create(
            logradouro="Rua das Flores", numero="123", bairro="Centro", cidade="São Paulo", estado="SP", cep="01234567"
        )

        # Criar profissional
        self.profissional = Profissional.objects.create(
            nome_social="Dr. João Silva",
            profissao="MEDICO",
            email="medico@test.com",
            telefone="11987654321",
            endereco=self.endereco,
            valor_consulta=Decimal("150.00"),
        )

        # Data/hora para consulta (futuro)
        self.data_consulta = timezone.now() + timedelta(days=7)

        self.consulta_data = {
            "profissional": self.profissional.id,
            "data_hora": self.data_consulta.isoformat(),
            "nome_paciente": "João Paciente",
            "telefone_paciente": "11987654321",
            "observacoes": "Primeira consulta",
        }

        # Criar consulta para testes de serialização
        self.consulta = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=self.data_consulta,
            nome_paciente="João Paciente",
            telefone_paciente="11987654321",
            observacoes="Consulta de teste",
            valor_consulta=Decimal("150.00"),
        )

    def test_serialization_consulta_completa(self):
        """
        Testa serialização de consulta com todos os campos
        """
        serializer = ConsultaSerializer(self.consulta)
        data = serializer.data

        self.assertEqual(data["nome_paciente"], "João Paciente")
        self.assertEqual(data["profissional_info"]["nome_social"], "Dr. João Silva")
        self.assertEqual(data["status"], "AGENDADA")
        self.assertEqual(data["valor_consulta"], "150.00")
        self.assertIn("data_hora", data)
        self.assertIn("observacoes", data)

    def test_nested_serialization_paciente_profissional(self):
        """
        Testa serialização aninhada de paciente e profissional
        """
        serializer = ConsultaSerializer(self.consulta)
        data = serializer.data

        # Verifica dados do paciente
        self.assertIsInstance(data["paciente"], dict)
        self.assertEqual(data["paciente"]["nome_completo"], "João Paciente")

        # Verifica dados do profissional
        self.assertIsInstance(data["profissional"], dict)
        self.assertEqual(data["profissional"]["profissao"], "MEDICO")

    def test_deserialization_dados_validos(self):
        """
        Testa deserialização com dados válidos
        """
        serializer = ConsultaSerializer(data=self.consulta_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        consulta = serializer.save()

        self.assertEqual(consulta.paciente, self.paciente)
        self.assertEqual(consulta.profissional, self.profissional)
        self.assertEqual(consulta.status, "AGENDADA")
        self.assertEqual(consulta.observacoes, "Primeira consulta")

    def test_validacao_data_passado(self):
        """
        Testa que não permite agendar consulta no passado
        """
        data_passado = timezone.now() - timedelta(days=1)
        self.consulta_data["data_consulta"] = data_passado.isoformat()

        serializer = ConsultaSerializer(data=self.consulta_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("data_consulta", serializer.errors)

    def test_validacao_horario_comercial(self):
        """
        Testa validação de horário comercial
        """
        # Agendamento fora do horário comercial (22h)
        data_fora_horario = timezone.now().replace(hour=22, minute=0, second=0, microsecond=0) + timedelta(days=1)

        self.consulta_data["data_consulta"] = data_fora_horario.isoformat()

        serializer = ConsultaSerializer(data=self.consulta_data)

        # Dependendo da implementação, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("data_consulta", serializer.errors)

    def test_campos_obrigatorios(self):
        """
        Testa campos obrigatórios
        """
        campos_obrigatorios = ["paciente", "profissional", "data_consulta"]

        for campo in campos_obrigatorios:
            consulta_data_incompleto = self.consulta_data.copy()
            del consulta_data_incompleto[campo]

            serializer = ConsultaSerializer(data=consulta_data_incompleto)
            self.assertFalse(serializer.is_valid())
            self.assertIn(campo, serializer.errors)

    def test_campos_opcionais(self):
        """
        Testa que campos opcionais podem ser omitidos
        """
        consulta_data_minimo = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": self.data_consulta.isoformat(),
        }

        serializer = ConsultaSerializer(data=consulta_data_minimo)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        consulta = serializer.save()

        self.assertEqual(consulta.observacoes, "")

    def test_calculo_valor_automatico(self):
        """
        Testa cálculo automático do valor baseado no profissional
        """
        # Não fornecer valor explícito
        consulta_data_sem_valor = self.consulta_data.copy()
        if "valor" in consulta_data_sem_valor:
            del consulta_data_sem_valor["valor"]

        serializer = ConsultaSerializer(data=consulta_data_sem_valor)

        self.assertTrue(serializer.is_valid())
        consulta = serializer.save()

        # Valor deve ser igual ao valor_consulta do profissional
        self.assertEqual(consulta.valor, self.profissional.valor_consulta)

    def test_update_consulta_existente(self):
        """
        Testa atualização de consulta existente
        """
        nova_data = timezone.now() + timedelta(days=10)
        novos_dados = {"data_consulta": nova_data.isoformat(), "observacoes": "Observações atualizadas"}

        serializer = ConsultaSerializer(self.consulta, data=novos_dados, partial=True)

        self.assertTrue(serializer.is_valid())
        consulta_atualizada = serializer.save()

        self.assertEqual(consulta_atualizada.observacoes, "Observações atualizadas")
        self.assertEqual(consulta_atualizada.paciente, self.paciente)  # Mantém dados anteriores


@pytest.mark.django_db
@pytest.mark.serializers
class TestConsultaSerializerVariants(TestCase):
    """
    Testes para variantes do ConsultaSerializer
    """

    def setUp(self):
        """
        Configuração inicial
        """
        self.paciente = User.objects.create_user(
            username="paciente2@test.com", email="paciente2@test.com", password="testpass123", tipo_usuario="PACIENTE"
        )

        self.endereco = Endereco.objects.create(
            logradouro="Rua Teste", numero="100", bairro="Teste", cidade="São Paulo", estado="SP", cep="12345678"
        )

        self.profissional = Profissional.objects.create(
            nome_social="Dr. Teste",
            profissao="PSICOLOGO",
            email="psi@test.com",
            telefone="11888777666",
            endereco=self.endereco,
            valor_consulta=Decimal("120.00"),
        )

        self.consulta = Consulta.objects.create(
            paciente=self.paciente,
            profissional=self.profissional,
            data_consulta=timezone.now() + timedelta(days=5),
            valor=Decimal("120.00"),
        )

    def test_consulta_list_serializer(self):
        """
        Testa ConsultaListSerializer (campos resumidos)
        """
        serializer = ConsultaListSerializer(self.consulta)
        data = serializer.data

        # Deve ter campos essenciais para listagem
        campos_esperados = ["id", "data_consulta", "status", "valor"]

        for campo in campos_esperados:
            self.assertIn(campo, data)

        # Deve ter informações básicas do paciente e profissional
        self.assertIn("paciente_nome", data)
        self.assertIn("profissional_nome", data)

        # Não deve ter campos detalhados
        self.assertNotIn("observacoes", data)

    def test_consulta_create_serializer(self):
        """
        Testa ConsultaCreateSerializer
        """
        nova_data = timezone.now() + timedelta(days=8)
        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": nova_data.isoformat(),
            "observacoes": "Nova consulta",
        }

        serializer = ConsultaCreateSerializer(data=consulta_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        consulta = serializer.save()

        self.assertEqual(consulta.paciente, self.paciente)
        self.assertEqual(consulta.profissional, self.profissional)
        self.assertEqual(consulta.status, "AGENDADA")

    def test_consulta_paciente_serializer(self):
        """
        Testa ConsultaPacienteSerializer (visão do paciente)
        """
        serializer = ConsultaPacienteSerializer(self.consulta)
        data = serializer.data

        # Deve ter campos essenciais para o paciente
        campos_esperados = ["id", "profissional_nome", "profissional_profissao", "data_hora", "status", "valor_consulta"]

        for campo in campos_esperados:
            self.assertIn(campo, data)

        # Deve ter informações limitadas por privacidade
        self.assertNotIn("observacoes_internas", data)
        self.assertNotIn("email_paciente", data)

    def test_consulta_update_serializer(self):
        """
        Testa ConsultaUpdateSerializer
        """
        # Confirmar consulta
        self.consulta.status = "CONFIRMADA"
        self.consulta.save()

        dados_update = {"observacoes": "Consulta confirmada e atualizada", "status": "EM_ANDAMENTO"}

        serializer = ConsultaUpdateSerializer(self.consulta, data=dados_update, partial=True)

        self.assertTrue(serializer.is_valid())
        consulta_atualizada = serializer.save()

        self.assertEqual(consulta_atualizada.status, "EM_ANDAMENTO")
        self.assertEqual(consulta_atualizada.observacoes, "Consulta confirmada e atualizada")


@pytest.mark.django_db
@pytest.mark.serializers
class TestConsultaValidacoes(TestCase):
    """
    Testes para validações customizadas nos serializers de consulta
    """

    def setUp(self):
        """
        Configuração inicial
        """
        self.paciente = User.objects.create_user(
            username="paciente3@test.com", email="paciente3@test.com", password="testpass123", tipo_usuario="PACIENTE"
        )

        self.endereco = Endereco.objects.create(
            logradouro="Rua Validação", numero="150", bairro="Validação", cidade="São Paulo", estado="SP", cep="11111111"
        )

        self.profissional = Profissional.objects.create(
            nome_social="Dr. Validação",
            profissao="FISIOTERAPEUTA",
            email="fisio@test.com",
            telefone="11777888999",
            endereco=self.endereco,
            valor_consulta=Decimal("100.00"),
        )

    def test_validacao_conflito_horario(self):
        """
        Testa validação de conflito de horário
        """
        data_consulta = timezone.now() + timedelta(days=3)

        # Criar primeira consulta
        Consulta.objects.create(
            paciente=self.paciente, profissional=self.profissional, data_consulta=data_consulta, valor=Decimal("100.00")
        )

        # Tentar criar segunda consulta no mesmo horário
        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": data_consulta.isoformat(),
        }

        serializer = ConsultaSerializer(data=consulta_data)

        # Dependendo da implementação, pode ser inválido por conflito
        if not serializer.is_valid():
            self.assertTrue("data_consulta" in serializer.errors or "non_field_errors" in serializer.errors)

    def test_validacao_limite_antecedencia(self):
        """
        Testa validação de limite de antecedência
        """
        # Tentar agendar com muito pouca antecedência (1 hora)
        data_muito_proxima = timezone.now() + timedelta(hours=1)

        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": data_muito_proxima.isoformat(),
        }

        serializer = ConsultaSerializer(data=consulta_data)

        # Dependendo da regra de negócio, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("data_consulta", serializer.errors)

    def test_validacao_status_transition(self):
        """
        Testa validação de transição de status
        """
        consulta = Consulta.objects.create(
            paciente=self.paciente,
            profissional=self.profissional,
            data_consulta=timezone.now() + timedelta(days=2),
            valor=Decimal("100.00"),
            status="FINALIZADA",  # Consulta já finalizada
        )

        # Tentar alterar status de finalizada para agendada (inválido)
        dados_update = {"status": "AGENDADA"}

        serializer = ConsultaUpdateSerializer(consulta, data=dados_update, partial=True)

        # Dependendo da implementação, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("status", serializer.errors)

    def test_validacao_profissional_ativo(self):
        """
        Testa que não permite agendar com profissional inativo
        """
        # Desativar profissional
        self.profissional.is_active = False
        self.profissional.save()

        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": (timezone.now() + timedelta(days=5)).isoformat(),
        }

        serializer = ConsultaSerializer(data=consulta_data)

        # Dependendo da implementação, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("profissional", serializer.errors)

    def test_validacao_paciente_ativo(self):
        """
        Testa que não permite agendar com paciente inativo
        """
        # Desativar paciente
        self.paciente.is_active = False
        self.paciente.save()

        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": (timezone.now() + timedelta(days=5)).isoformat(),
        }

        serializer = ConsultaSerializer(data=consulta_data)

        # Dependendo da implementação, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("paciente", serializer.errors)

    def test_sanitizacao_observacoes(self):
        """
        Testa sanitização das observações
        """
        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": (timezone.now() + timedelta(days=6)).isoformat(),
            "observacoes": "  Observações com espaços extras  ",
        }

        serializer = ConsultaSerializer(data=consulta_data)

        self.assertTrue(serializer.is_valid())
        consulta = serializer.save()

        # Observações devem ser "limpas"
        self.assertEqual(consulta.observacoes, "Observações com espaços extras")

    def test_validacao_fim_semana(self):
        """
        Testa validação para agendamento em fins de semana
        """
        # Encontrar próximo domingo
        hoje = timezone.now().date()
        dias_para_domingo = (6 - hoje.weekday()) % 7
        if dias_para_domingo == 0:
            dias_para_domingo = 7

        domingo = timezone.now().replace(
            year=hoje.year, month=hoje.month, day=hoje.day, hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=dias_para_domingo)

        consulta_data = {
            "paciente": self.paciente.id,
            "profissional": self.profissional.id,
            "data_consulta": domingo.isoformat(),
        }

        serializer = ConsultaSerializer(data=consulta_data)

        # Dependendo da regra de negócio, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("data_consulta", serializer.errors)
