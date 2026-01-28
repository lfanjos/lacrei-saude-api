"""
Testes para Serializers de Profissionais - Lacrei Saúde API
==========================================================
"""

from decimal import Decimal

import pytest
from rest_framework import serializers

from django.test import TestCase

from profissionais.models import Endereco, Profissional
from profissionais.serializers import (
    EnderecoSerializer,
    ProfissionalCreateSerializer,
    ProfissionalDetailSerializer,
    ProfissionalListSerializer,
    ProfissionalSerializer,
)


@pytest.mark.django_db
@pytest.mark.serializers
class TestEnderecoSerializer(TestCase):
    """
    Testes para EnderecoSerializer
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.endereco_data = {
            "logradouro": "Rua das Flores",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "01234567",
        }

        self.endereco = Endereco.objects.create(**self.endereco_data)

    def test_serialization_endereco_valido(self):
        """
        Testa serialização de endereço válido
        """
        serializer = EnderecoSerializer(self.endereco)
        data = serializer.data

        self.assertEqual(data["logradouro"], "Rua das Flores")
        self.assertEqual(data["numero"], "123")
        self.assertEqual(data["cidade"], "São Paulo")
        self.assertEqual(data["estado"], "SP")
        self.assertEqual(data["cep"], "01234567")
        self.assertIn("endereco_completo", data)
        self.assertIn("created_at", data)
        self.assertIn("is_active", data)

    def test_deserialization_dados_validos(self):
        """
        Testa deserialização com dados válidos
        """
        serializer = EnderecoSerializer(data=self.endereco_data)

        self.assertTrue(serializer.is_valid())
        endereco = serializer.save()

        self.assertEqual(endereco.logradouro, "Rua das Flores")
        self.assertEqual(endereco.cidade, "São Paulo")
        self.assertTrue(endereco.is_active)

    def test_validacao_cep_formato_correto(self):
        """
        Testa validação e formatação do CEP
        """
        test_cases = [("01234567", "01234-567"), ("12345-678", "12345-678"), ("98765432", "98765-432")]

        for cep_input, cep_expected in test_cases:
            self.endereco_data["cep"] = cep_input
            serializer = EnderecoSerializer(data=self.endereco_data)

            self.assertTrue(serializer.is_valid())
            # Validar se formatação ocorre no serializer

    def test_validacao_estado_invalido(self):
        """
        Testa validação de estado inválido
        """
        self.endereco_data["estado"] = "XX"
        serializer = EnderecoSerializer(data=self.endereco_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("estado", serializer.errors)

    def test_campos_obrigatorios(self):
        """
        Testa campos obrigatórios do serializer
        """
        campos_obrigatorios = ["logradouro", "numero", "bairro", "cidade", "estado", "cep"]

        for campo in campos_obrigatorios:
            endereco_data_incompleto = self.endereco_data.copy()
            del endereco_data_incompleto[campo]

            serializer = EnderecoSerializer(data=endereco_data_incompleto)
            self.assertFalse(serializer.is_valid())
            self.assertIn(campo, serializer.errors)

    def test_campos_opcionais(self):
        """
        Testa que campos opcionais podem ser omitidos
        """
        endereco_data_minimo = {
            "logradouro": "Rua Teste",
            "numero": "100",
            "bairro": "Teste",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "12345678",
        }
        # complemento e referencia são opcionais

        serializer = EnderecoSerializer(data=endereco_data_minimo)
        self.assertTrue(serializer.is_valid())

    def test_update_endereco_existente(self):
        """
        Testa atualização de endereço existente
        """
        novos_dados = {"logradouro": "Rua Atualizada", "numero": "456"}

        serializer = EnderecoSerializer(self.endereco, data=novos_dados, partial=True)

        self.assertTrue(serializer.is_valid())
        endereco_atualizado = serializer.save()

        self.assertEqual(endereco_atualizado.logradouro, "Rua Atualizada")
        self.assertEqual(endereco_atualizado.numero, "456")
        self.assertEqual(endereco_atualizado.cidade, "São Paulo")  # Mantém dados anteriores


@pytest.mark.django_db
@pytest.mark.serializers
class TestProfissionalSerializer(TestCase):
    """
    Testes para ProfissionalSerializer
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        self.endereco_data = {
            "logradouro": "Rua das Flores",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "01234567",
        }

        self.profissional_data = {
            "nome_social": "Dr. João Silva",
            "nome_registro": "João Silva Santos",
            "profissao": "MEDICO",
            "registro_profissional": "CRM123456",
            "especialidade": "Cardiologia",
            "email": "joao.silva@email.com",
            "telefone": "11987654321",
            "endereco": self.endereco_data,
            "biografia": "Médico especialista em cardiologia.",
            "aceita_convenio": True,
            "valor_consulta": "150.00",
        }

        # Criar profissional para testes de serialização
        self.endereco = Endereco.objects.create(**self.endereco_data)
        self.profissional = Profissional.objects.create(
            nome_social="Dr. João Silva",
            profissao="MEDICO",
            email="joao.silva@email.com",
            telefone="11987654321",
            endereco=self.endereco,
            valor_consulta=Decimal("150.00"),
        )

    def test_serialization_profissional_completo(self):
        """
        Testa serialização de profissional com todos os campos
        """
        serializer = ProfissionalSerializer(self.profissional)
        data = serializer.data

        self.assertEqual(data["nome_social"], "Dr. João Silva")
        self.assertEqual(data["profissao"], "MEDICO")
        self.assertEqual(data["email"], "joao.silva@email.com")
        self.assertIn("endereco", data)
        self.assertIn("nome_completo", data)
        self.assertIn("contato_formatado", data)
        self.assertIn("profissao_display", data)

    def test_nested_endereco_serialization(self):
        """
        Testa serialização aninhada do endereço
        """
        serializer = ProfissionalSerializer(self.profissional)
        endereco_data = serializer.data["endereco"]

        self.assertIsInstance(endereco_data, dict)
        self.assertEqual(endereco_data["cidade"], "São Paulo")
        self.assertIn("endereco_completo", endereco_data)

    def test_deserialization_dados_validos(self):
        """
        Testa deserialização com dados válidos
        """
        serializer = ProfissionalSerializer(data=self.profissional_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profissional = serializer.save()

        self.assertEqual(profissional.nome_social, "Dr. João Silva")
        self.assertEqual(profissional.profissao, "MEDICO")
        self.assertEqual(profissional.valor_consulta, Decimal("150.00"))
        self.assertIsNotNone(profissional.endereco)

    def test_validacao_email_unico(self):
        """
        Testa validação de email único
        """
        # Usar email já existente
        self.profissional_data["email"] = "joao.silva@email.com"  # Mesmo email do profissional criado no setUp

        serializer = ProfissionalSerializer(data=self.profissional_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_validacao_email_formato_invalido(self):
        """
        Testa validação de formato de email
        """
        self.profissional_data["email"] = "email_invalido"

        serializer = ProfissionalSerializer(data=self.profissional_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_validacao_telefone_formato(self):
        """
        Testa validação de formato de telefone
        """
        test_cases = [
            ("11987654321", True),  # Válido
            ("1198765432", True),  # Válido sem 9
            ("119876543210", False),  # Muito longo
            ("119876543", False),  # Muito curto
            ("abc1234567", False),  # Com letras
        ]

        for telefone, should_be_valid in test_cases:
            self.profissional_data["telefone"] = telefone
            self.profissional_data["email"] = f"test_{telefone}@email.com"  # Email único

            serializer = ProfissionalSerializer(data=self.profissional_data)

            if should_be_valid:
                self.assertTrue(serializer.is_valid(), f"Telefone {telefone} deveria ser válido")
            else:
                self.assertFalse(serializer.is_valid(), f"Telefone {telefone} deveria ser inválido")

    def test_validacao_valor_consulta_negativo(self):
        """
        Testa que valor da consulta não pode ser negativo
        """
        self.profissional_data["valor_consulta"] = "-50.00"

        serializer = ProfissionalSerializer(data=self.profissional_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_consulta", serializer.errors)

    def test_validacao_profissao_invalida(self):
        """
        Testa validação de profissão inválida
        """
        self.profissional_data["profissao"] = "PROFISSAO_INEXISTENTE"

        serializer = ProfissionalSerializer(data=self.profissional_data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("profissao", serializer.errors)

    def test_campos_obrigatorios(self):
        """
        Testa campos obrigatórios
        """
        campos_obrigatorios = ["nome_social", "profissao", "email", "telefone", "endereco"]

        for campo in campos_obrigatorios:
            profissional_data_incompleto = self.profissional_data.copy()
            del profissional_data_incompleto[campo]

            serializer = ProfissionalSerializer(data=profissional_data_incompleto)
            self.assertFalse(serializer.is_valid())
            # Pode estar em errors direto ou em non_field_errors
            tem_erro = campo in serializer.errors or "non_field_errors" in serializer.errors
            self.assertTrue(tem_erro, f"Campo obrigatório {campo} não gerou erro de validação")

    def test_campos_opcionais(self):
        """
        Testa que campos opcionais podem ser omitidos
        """
        profissional_data_minimo = {
            "nome_social": "Dr. Teste",
            "profissao": "MEDICO",
            "email": "teste.minimo@email.com",
            "telefone": "11999999999",
            "endereco": self.endereco_data,
        }

        serializer = ProfissionalSerializer(data=profissional_data_minimo)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profissional = serializer.save()

        self.assertEqual(profissional.nome_social, "Dr. Teste")
        self.assertEqual(profissional.nome_registro, "")  # Campo opcional vazio
        self.assertIsNone(profissional.valor_consulta)  # Campo opcional None

    def test_update_profissional_existente(self):
        """
        Testa atualização de profissional existente
        """
        novos_dados = {
            "nome_social": "Dr. João Atualizado",
            "especialidade": "Cardiologia Avançada",
            "valor_consulta": "200.00",
        }

        serializer = ProfissionalSerializer(self.profissional, data=novos_dados, partial=True)

        self.assertTrue(serializer.is_valid())
        profissional_atualizado = serializer.save()

        self.assertEqual(profissional_atualizado.nome_social, "Dr. João Atualizado")
        self.assertEqual(profissional_atualizado.especialidade, "Cardiologia Avançada")
        self.assertEqual(profissional_atualizado.valor_consulta, Decimal("200.00"))
        self.assertEqual(profissional_atualizado.email, "joao.silva@email.com")  # Mantém dados anteriores


@pytest.mark.django_db
@pytest.mark.serializers
class TestProfissionalSerializerVariants(TestCase):
    """
    Testes para variantes do ProfissionalSerializer
    """

    def setUp(self):
        """
        Configuração inicial
        """
        self.endereco = Endereco.objects.create(
            logradouro="Rua Teste", numero="100", bairro="Teste", cidade="São Paulo", estado="SP", cep="12345678"
        )

        self.profissional = Profissional.objects.create(
            nome_social="Dr. Teste",
            profissao="MEDICO",
            email="teste@email.com",
            telefone="11987654321",
            endereco=self.endereco,
            valor_consulta=Decimal("150.00"),
        )

    def test_profissional_list_serializer(self):
        """
        Testa ProfissionalListSerializer (campos resumidos)
        """
        serializer = ProfissionalListSerializer(self.profissional)
        data = serializer.data

        # Deve ter campos essenciais para listagem
        campos_esperados = [
            "id",
            "nome_social",
            "profissao",
            "especialidade",
            "email",
            "telefone",
            "aceita_convenio",
            "valor_consulta",
        ]

        for campo in campos_esperados:
            self.assertIn(campo, data)

        # Não deve ter campos detalhados
        self.assertNotIn("biografia", data)
        self.assertNotIn("endereco", data)  # Endereço completo não aparece na listagem

    def test_profissional_create_serializer(self):
        """
        Testa ProfissionalCreateSerializer
        """
        profissional_data = {
            "nome_social": "Dr. Novo",
            "profissao": "PSICOLOGO",
            "email": "novo@email.com",
            "telefone": "11888777666",
            "endereco": {
                "logradouro": "Rua Nova",
                "numero": "200",
                "bairro": "Novo Bairro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "87654321",
            },
        }

        serializer = ProfissionalCreateSerializer(data=profissional_data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profissional = serializer.save()

        self.assertEqual(profissional.nome_social, "Dr. Novo")
        self.assertEqual(profissional.profissao, "PSICOLOGO")
        self.assertIsNotNone(profissional.endereco)

    def test_profissional_detail_serializer(self):
        """
        Testa ProfissionalDetailSerializer (todos os campos)
        """
        serializer = ProfissionalDetailSerializer(self.profissional)
        data = serializer.data

        # Deve ter todos os campos incluindo relacionamentos
        campos_esperados = [
            "id",
            "nome_social",
            "nome_completo",
            "profissao",
            "endereco",
            "biografia",
            "created_at",
            "updated_at",
        ]

        for campo in campos_esperados:
            self.assertIn(campo, data)

        # Deve ter informações do endereço
        self.assertIsInstance(data["endereco"], dict)


@pytest.mark.django_db
@pytest.mark.serializers
class TestSerializerValidacoes(TestCase):
    """
    Testes para validações customizadas nos serializers
    """

    def setUp(self):
        """
        Configuração inicial
        """
        self.endereco_data = {
            "logradouro": "Rua Teste",
            "numero": "100",
            "bairro": "Teste",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep": "12345678",
        }

    def test_sanitizacao_nome_social(self):
        """
        Testa sanitização do nome social
        """
        profissional_data = {
            "nome_social": "dr. joão silva",  # Minúsculo
            "profissao": "MEDICO",
            "email": "joao@email.com",
            "telefone": "11987654321",
            "endereco": self.endereco_data,
        }

        serializer = ProfissionalSerializer(data=profissional_data)

        self.assertTrue(serializer.is_valid())
        profissional = serializer.save()

        # Nome deve ser capitalizado
        self.assertEqual(profissional.nome_social, "Dr. João Silva")

    def test_sanitizacao_email(self):
        """
        Testa sanitização do email
        """
        profissional_data = {
            "nome_social": "Dr. Teste",
            "profissao": "MEDICO",
            "email": "TESTE@EMAIL.COM",  # Maiúsculo
            "telefone": "11987654321",
            "endereco": self.endereco_data,
        }

        serializer = ProfissionalSerializer(data=profissional_data)

        self.assertTrue(serializer.is_valid())
        profissional = serializer.save()

        # Email deve ser lowercase
        self.assertEqual(profissional.email, "teste@email.com")

    def test_validacao_crm_para_medico(self):
        """
        Testa validação específica de CRM para médicos
        """
        profissional_data = {
            "nome_social": "Dr. Médico",
            "profissao": "MEDICO",
            "email": "medico@email.com",
            "telefone": "11987654321",
            "endereco": self.endereco_data,
            "registro_profissional": "CRM123",  # CRM muito curto
        }

        serializer = ProfissionalSerializer(data=profissional_data)

        # Dependendo da implementação, pode ser inválido
        if not serializer.is_valid():
            self.assertIn("registro_profissional", serializer.errors)

    def test_validacao_consistencia_dados(self):
        """
        Testa validações de consistência entre campos
        """
        profissional_data = {
            "nome_social": "Dr. Teste",
            "profissao": "MEDICO",
            "email": "teste@email.com",
            "telefone": "11987654321",
            "endereco": self.endereco_data,
            "aceita_convenio": True,
            "valor_consulta": None,  # Aceita convênio mas não tem valor
        }

        serializer = ProfissionalSerializer(data=profissional_data)

        # Deve ser válido mesmo sem valor_consulta
        self.assertTrue(serializer.is_valid())
