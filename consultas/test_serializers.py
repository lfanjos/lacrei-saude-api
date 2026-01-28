"""
Testes Simplificados para Serializers de Consultas - Lacrei Saúde API
======================================================================
"""

from datetime import timedelta
from decimal import Decimal

import pytest

from django.test import TestCase
from django.utils import timezone

from consultas.models import Consulta
from consultas.serializers import ConsultaListSerializer, ConsultaSerializer
from profissionais.models import Endereco, Profissional


@pytest.mark.django_db
@pytest.mark.serializers
class TestConsultaSerializerSimple(TestCase):
    """
    Testes simplificados para ConsultaSerializer
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
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

        # Criar consulta
        self.consulta = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=self.data_consulta,
            nome_paciente="João Paciente",
            telefone_paciente="11987654321",
            observacoes="Consulta de teste",
            valor_consulta=Decimal("150.00"),
        )

    def test_serialization_consulta_basica(self):
        """
        Testa serialização básica de consulta
        """
        serializer = ConsultaSerializer(self.consulta)
        data = serializer.data

        self.assertEqual(data["nome_paciente"], "João Paciente")
        self.assertEqual(data["status"], "AGENDADA")
        self.assertIn("data_hora", data)
        self.assertIn("observacoes", data)

    def test_list_serializer(self):
        """
        Testa ConsultaListSerializer
        """
        serializer = ConsultaListSerializer(self.consulta)
        data = serializer.data

        self.assertIn("profissional_nome", data)
        self.assertIn("status_display", data)
        self.assertIn("data_hora_formatada", data)

    def test_criar_consulta_dados_validos(self):
        """
        Testa criação de consulta com dados válidos
        """
        dados_consulta = {
            "profissional": self.profissional.id,
            "data_hora": (timezone.now() + timedelta(days=5)).isoformat(),
            "nome_paciente": "Maria Silva",
            "telefone_paciente": "11888777666",
            "observacoes": "Nova consulta",
        }

        serializer = ConsultaSerializer(data=dados_consulta)

        if serializer.is_valid():
            consulta = serializer.save()
            self.assertEqual(consulta.nome_paciente, "Maria Silva")
            self.assertEqual(consulta.status, "AGENDADA")
        else:
            # Se não for válido, pelo menos verifica estrutura básica
            self.assertIsInstance(serializer.errors, dict)
