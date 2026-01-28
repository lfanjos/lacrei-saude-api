"""
Testes para Modelos de Consultas - Lacrei Saúde API
==================================================
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from consultas.models import Consulta
from profissionais.models import Endereco, Profissional


@pytest.mark.django_db
@pytest.mark.models
class TestConsultaModel(TestCase):
    """
    Testes para o modelo Consulta
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
            email="joao.silva@email.com",
            telefone="11987654321",
            endereco=self.endereco,
            valor_consulta=Decimal("150.00"),
        )

        # Data futura para a consulta
        self.data_futura = timezone.now() + timedelta(days=7)

        self.consulta_data = {
            "profissional": self.profissional,
            "data_hora": self.data_futura,
            "duracao_estimada": 60,
            "tipo_consulta": "PRESENCIAL",
            "status": "AGENDADA",
            "nome_paciente": "Maria Silva",
            "telefone_paciente": "11999888777",
            "email_paciente": "maria@email.com",
            "motivo_consulta": "Consulta de rotina",
            "valor_consulta": Decimal("150.00"),
        }

    def test_criar_consulta_valida(self):
        """
        Testa criação de consulta com dados válidos
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        self.assertEqual(consulta.profissional, self.profissional)
        self.assertEqual(consulta.nome_paciente, "Maria Silva")
        self.assertEqual(consulta.status, "AGENDADA")
        self.assertEqual(consulta.tipo_consulta, "PRESENCIAL")
        self.assertEqual(consulta.valor_consulta, Decimal("150.00"))
        self.assertFalse(consulta.pago)
        self.assertTrue(consulta.is_active)
        self.assertIsNotNone(consulta.id)

    def test_pode_cancelar_consulta_agendada(self):
        """
        Testa que consulta agendada pode ser cancelada
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        self.assertTrue(consulta.pode_cancelar)

    def test_nao_pode_cancelar_consulta_finalizada(self):
        """
        Testa que consulta finalizada não pode ser cancelada
        """
        self.consulta_data["status"] = "CONCLUIDA"
        consulta = Consulta.objects.create(**self.consulta_data)

        self.assertFalse(consulta.pode_cancelar)

    def test_pode_remarcar_consulta_agendada(self):
        """
        Testa que consulta agendada pode ser remarcada
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        self.assertTrue(consulta.pode_remarcar)

    def test_nao_pode_remarcar_consulta_em_andamento(self):
        """
        Testa que consulta em andamento não pode ser remarcada
        """
        self.consulta_data["status"] = "EM_ANDAMENTO"
        consulta = Consulta.objects.create(**self.consulta_data)

        self.assertFalse(consulta.pode_remarcar)

    def test_confirmar_consulta(self):
        """
        Testa método confirmar consulta
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        consulta.confirmar()

        self.assertEqual(consulta.status, "CONFIRMADA")

    def test_confirmar_consulta_status_invalido(self):
        """
        Testa erro ao confirmar consulta com status inválido
        """
        self.consulta_data["status"] = "CONCLUIDA"
        consulta = Consulta.objects.create(**self.consulta_data)

        with self.assertRaises(ValueError):
            consulta.confirmar()

    def test_iniciar_consulta(self):
        """
        Testa método iniciar consulta
        """
        consulta = Consulta.objects.create(**self.consulta_data)
        consulta.status = "CONFIRMADA"
        consulta.save()

        consulta.iniciar()

        self.assertEqual(consulta.status, "EM_ANDAMENTO")
        self.assertIsNotNone(consulta.data_hora_inicio_real)

    def test_finalizar_consulta(self):
        """
        Testa método finalizar consulta
        """
        consulta = Consulta.objects.create(**self.consulta_data)
        consulta.status = "EM_ANDAMENTO"
        consulta.data_hora_inicio_real = timezone.now()
        consulta.save()

        observacoes = "Consulta realizada com sucesso"
        consulta.finalizar(observacoes)

        self.assertEqual(consulta.status, "CONCLUIDA")
        self.assertEqual(consulta.observacoes_internas, observacoes)
        self.assertIsNotNone(consulta.data_hora_fim)

    def test_cancelar_consulta(self):
        """
        Testa método cancelar consulta
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        motivo = "Paciente cancelou"
        consulta.cancelar(motivo, "PACIENTE")

        self.assertEqual(consulta.status, "CANCELADA")
        self.assertEqual(consulta.motivo_cancelamento, motivo)
        self.assertEqual(consulta.cancelado_por, "PACIENTE")
        self.assertIsNotNone(consulta.data_cancelamento)

    def test_remarcar_consulta(self):
        """
        Testa método remarcar consulta
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        nova_data = self.data_futura + timedelta(days=1)
        motivo = "Conflito de agenda"

        nova_consulta = consulta.remarcar(nova_data, motivo)

        # Consulta original cancelada
        consulta.refresh_from_db()
        self.assertEqual(consulta.status, "CANCELADA")
        self.assertEqual(consulta.motivo_cancelamento, f"Remarcada: {motivo}")

        # Nova consulta criada
        self.assertIsNotNone(nova_consulta)
        self.assertEqual(nova_consulta.data_hora, nova_data)
        self.assertEqual(nova_consulta.status, "AGENDADA")
        self.assertEqual(nova_consulta.consulta_origem, consulta)

    def test_duracao_real_property(self):
        """
        Testa propriedade duracao_real
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        # Sem data de início/fim
        self.assertIsNone(consulta.duracao_real)

        # Com início mas sem fim
        consulta.data_hora_inicio_real = timezone.now()
        consulta.save()
        self.assertIsNone(consulta.duracao_real)

        # Com início e fim
        consulta.data_hora_fim = consulta.data_hora_inicio_real + timedelta(minutes=45)
        consulta.save()
        self.assertEqual(consulta.duracao_real, 45)

    def test_tempo_restante_property(self):
        """
        Testa propriedade tempo_restante
        """
        # Consulta futura
        consulta = Consulta.objects.create(**self.consulta_data)
        tempo_restante = consulta.tempo_restante
        self.assertIsNotNone(tempo_restante)
        self.assertGreater(tempo_restante, 0)

        # Consulta passada
        consulta.data_hora = timezone.now() - timedelta(days=1)
        consulta.save()
        self.assertEqual(consulta.tempo_restante, 0)

    def test_validacao_data_no_passado(self):
        """
        Testa validação de data no passado
        """
        self.consulta_data["data_hora"] = timezone.now() - timedelta(days=1)

        with self.assertRaises(ValidationError):
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()

    def test_validacao_duracao_estimada(self):
        """
        Testa validação de duração estimada
        """
        # Duração negativa
        self.consulta_data["duracao_estimada"] = -30
        with self.assertRaises(ValidationError):
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()

        # Duração zero
        self.consulta_data["duracao_estimada"] = 0
        with self.assertRaises(ValidationError):
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()

        # Duração muito alta
        self.consulta_data["duracao_estimada"] = 500
        with self.assertRaises(ValidationError):
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()

    def test_validacao_valor_consulta_negativo(self):
        """
        Testa que valor da consulta não pode ser negativo
        """
        self.consulta_data["valor_consulta"] = Decimal("-10.00")

        with self.assertRaises(ValidationError):
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()

    def test_choices_status(self):
        """
        Testa as choices de status
        """
        status_validos = ["AGENDADA", "CONFIRMADA", "EM_ANDAMENTO", "CONCLUIDA"]

        for status in status_validos:
            self.consulta_data["status"] = status
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()  # Não deve gerar erro

        # Teste especial para CANCELADA (que requer motivo)
        self.consulta_data["status"] = "CANCELADA"
        self.consulta_data["motivo_cancelamento"] = "Cancelado pelo paciente"
        consulta = Consulta(**self.consulta_data)
        consulta.full_clean()  # Não deve gerar erro com motivo

    def test_choices_tipo_consulta(self):
        """
        Testa as choices de tipo de consulta
        """
        tipos_validos = ["PRESENCIAL", "TELECONSULTA"]

        for tipo in tipos_validos:
            self.consulta_data["tipo_consulta"] = tipo
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()  # Não deve gerar erro

    def test_choices_forma_pagamento(self):
        """
        Testa as choices de forma de pagamento
        """
        formas_validas = ["DINHEIRO", "CARTAO_CREDITO", "CARTAO_DEBITO", "PIX", "CONVENIO"]

        for forma in formas_validas:
            self.consulta_data["forma_pagamento"] = forma
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()  # Não deve gerar erro

    def test_validacao_email_paciente_formato(self):
        """
        Testa validação de formato de email do paciente
        """
        self.consulta_data["email_paciente"] = "email_invalido"

        with self.assertRaises(ValidationError):
            consulta = Consulta(**self.consulta_data)
            consulta.full_clean()

    def test_campos_opcionais(self):
        """
        Testa que campos opcionais podem ser vazios
        """
        campos_opcionais = ["email_paciente", "motivo_consulta", "observacoes", "observacoes_internas", "forma_pagamento"]

        for campo in campos_opcionais:
            consulta_data = {
                "profissional": self.profissional,
                "data_hora": self.data_futura,
                "nome_paciente": "Test Patient",
                "telefone_paciente": "11999999999",
                "valor_consulta": Decimal("100.00"),
            }

            # Campo opcional pode ser vazio
            consulta_data[campo] = "" if campo != "forma_pagamento" else None

            consulta = Consulta(**consulta_data)
            consulta.full_clean()  # Não deve gerar erro

    def test_str_representation(self):
        """
        Testa representação string do modelo
        """
        consulta = Consulta.objects.create(**self.consulta_data)
        expected_str = f"Maria Silva - {self.data_futura.strftime('%d/%m/%Y %H:%M')} - Dr. João Silva"

        self.assertEqual(str(consulta), expected_str)

    def test_soft_delete(self):
        """
        Testa soft delete da consulta
        """
        consulta = Consulta.objects.create(**self.consulta_data)
        consulta_id = consulta.id

        # Desativar ao invés de deletar
        consulta.is_active = False
        consulta.save()

        # Consulta ainda existe no banco
        consulta_db = Consulta.objects.get(id=consulta_id)
        self.assertFalse(consulta_db.is_active)

    def test_relacionamento_com_profissional(self):
        """
        Testa relacionamento com profissional
        """
        consulta = Consulta.objects.create(**self.consulta_data)

        self.assertEqual(consulta.profissional, self.profissional)
        self.assertEqual(consulta.profissional.nome_social, "Dr. João Silva")

    def test_relacionamento_consulta_origem(self):
        """
        Testa relacionamento com consulta de origem (remarcação)
        """
        consulta_original = Consulta.objects.create(**self.consulta_data)

        nova_data = self.data_futura + timedelta(days=1)
        consulta_remarcada = consulta_original.remarcar(nova_data, "Teste")

        self.assertEqual(consulta_remarcada.consulta_origem, consulta_original)


@pytest.mark.django_db
@pytest.mark.models
class TestConsultaQueryset(TestCase):
    """
    Testes para queryset customizado da Consulta
    """

    def setUp(self):
        """
        Configurar dados de teste
        """
        self.endereco = Endereco.objects.create(
            logradouro="Rua Teste", numero="100", bairro="Teste", cidade="São Paulo", estado="SP", cep="12345678"
        )

        self.profissional = Profissional.objects.create(
            nome_social="Dr. Test", profissao="MEDICO", email="test@test.com", telefone="11111111111", endereco=self.endereco
        )

    def test_filtrar_por_status(self):
        """
        Testa filtro por status
        """
        data_futura = timezone.now() + timedelta(days=1)

        # Criar consultas com diferentes status
        consulta_agendada = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=data_futura,
            nome_paciente="Paciente 1",
            telefone_paciente="11111111111",
            status="AGENDADA",
        )

        consulta_confirmada = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=data_futura + timedelta(hours=1),
            nome_paciente="Paciente 2",
            telefone_paciente="11111111112",
            status="CONFIRMADA",
        )

        agendadas = Consulta.objects.filter(status="AGENDADA")
        confirmadas = Consulta.objects.filter(status="CONFIRMADA")

        self.assertEqual(agendadas.count(), 1)
        self.assertEqual(confirmadas.count(), 1)
        self.assertIn(consulta_agendada, agendadas)
        self.assertIn(consulta_confirmada, confirmadas)

    def test_filtrar_por_profissional(self):
        """
        Testa filtro por profissional
        """
        data_futura = timezone.now() + timedelta(days=1)

        # Criar outro profissional
        profissional2 = Profissional.objects.create(
            nome_social="Dr. Test 2",
            profissao="PSICOLOGO",
            email="test2@test.com",
            telefone="11111111112",
            endereco=self.endereco,
        )

        # Criar consultas para cada profissional
        consulta1 = Consulta.objects.create(
            profissional=self.profissional, data_hora=data_futura, nome_paciente="Paciente 1", telefone_paciente="11111111111"
        )

        consulta2 = Consulta.objects.create(
            profissional=profissional2,
            data_hora=data_futura + timedelta(hours=1),
            nome_paciente="Paciente 2",
            telefone_paciente="11111111112",
        )

        consultas_prof1 = Consulta.objects.filter(profissional=self.profissional)
        consultas_prof2 = Consulta.objects.filter(profissional=profissional2)

        self.assertEqual(consultas_prof1.count(), 1)
        self.assertEqual(consultas_prof2.count(), 1)
        self.assertIn(consulta1, consultas_prof1)
        self.assertIn(consulta2, consultas_prof2)

    def test_filtrar_consultas_futuras(self):
        """
        Testa filtro de consultas futuras
        """
        agora = timezone.now()

        # Consulta futura
        consulta_futura = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=agora + timedelta(days=1),
            nome_paciente="Paciente Futuro",
            telefone_paciente="11111111111",
        )

        # Consulta passada
        consulta_passada = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=agora - timedelta(days=1),
            nome_paciente="Paciente Passado",
            telefone_paciente="11111111112",
        )

        consultas_futuras = Consulta.objects.filter(data_hora__gt=agora)

        self.assertEqual(consultas_futuras.count(), 1)
        self.assertIn(consulta_futura, consultas_futuras)
        self.assertNotIn(consulta_passada, consultas_futuras)
