"""
Testes para Modelos de Profissionais - Lacrei Saúde API
======================================================
"""

from decimal import Decimal

import pytest

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from profissionais.models import Endereco, Profissional


@pytest.mark.django_db
@pytest.mark.models
class TestEnderecoModel(TestCase):
    """
    Testes para o modelo Endereco
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

    def test_criar_endereco_valido(self):
        """
        Testa criação de endereço com dados válidos
        """
        endereco = Endereco.objects.create(**self.endereco_data)

        self.assertEqual(endereco.logradouro, "Rua das Flores")
        self.assertEqual(endereco.numero, "123")
        self.assertEqual(endereco.bairro, "Centro")
        self.assertEqual(endereco.cidade, "São Paulo")
        self.assertEqual(endereco.estado, "SP")
        self.assertEqual(endereco.cep, "01234567")
        self.assertTrue(endereco.is_active)
        self.assertIsNotNone(endereco.id)

    def test_endereco_completo_property(self):
        """
        Testa a propriedade endereco_completo
        """
        endereco = Endereco.objects.create(**self.endereco_data)
        endereco_esperado = "Rua das Flores, 123 - Centro - São Paulo/SP - CEP: 01234567"

        self.assertEqual(endereco.endereco_completo, endereco_esperado)

    def test_endereco_completo_com_complemento(self):
        """
        Testa endereco_completo com complemento
        """
        self.endereco_data["complemento"] = "Apt 45"
        endereco = Endereco.objects.create(**self.endereco_data)
        endereco_esperado = "Rua das Flores, 123, Apt 45 - Centro - São Paulo/SP - CEP: 01234567"

        self.assertEqual(endereco.endereco_completo, endereco_esperado)

    def test_validacao_cep_formato_invalido(self):
        """
        Testa validação de CEP com formato inválido
        """
        self.endereco_data["cep"] = "123"  # CEP muito curto

        with self.assertRaises(ValidationError):
            endereco = Endereco(**self.endereco_data)
            endereco.full_clean()

    def test_validacao_estado_invalido(self):
        """
        Testa validação de estado inválido
        """
        self.endereco_data["estado"] = "XX"  # Estado não existe

        endereco = Endereco(**self.endereco_data)
        with self.assertRaises(ValidationError):
            endereco.full_clean()

    def test_campos_obrigatorios(self):
        """
        Testa campos obrigatórios do endereço
        """
        campos_obrigatorios = ["logradouro", "numero", "bairro", "cidade", "estado", "cep"]

        for campo in campos_obrigatorios:
            endereco_data_incompleto = self.endereco_data.copy()
            del endereco_data_incompleto[campo]

            with self.assertRaises(ValidationError):
                endereco = Endereco(**endereco_data_incompleto)
                endereco.full_clean()

    def test_str_representation(self):
        """
        Testa representação string do modelo
        """
        endereco = Endereco.objects.create(**self.endereco_data)
        expected_str = "Rua das Flores, 123 - Centro - São Paulo/SP"

        self.assertEqual(str(endereco), expected_str)


@pytest.mark.django_db
@pytest.mark.models
class TestProfissionalModel(TestCase):
    """
    Testes para o modelo Profissional
    """

    def setUp(self):
        """
        Configuração inicial para os testes
        """
        # Criar endereço para usar nos testes
        self.endereco = Endereco.objects.create(
            logradouro="Rua das Flores", numero="123", bairro="Centro", cidade="São Paulo", estado="SP", cep="01234567"
        )

        self.profissional_data = {
            "nome_social": "Dr. João Silva",
            "nome_registro": "João Silva Santos",
            "profissao": "MEDICO",
            "registro_profissional": "CRM123456",
            "especialidade": "Cardiologia",
            "email": "joao.silva@email.com",
            "telefone": "11987654321",
            "endereco": self.endereco,
            "biografia": "Médico especialista em cardiologia com 10 anos de experiência.",
            "aceita_convenio": True,
            "valor_consulta": Decimal("150.00"),
        }

    def test_criar_profissional_valido(self):
        """
        Testa criação de profissional com dados válidos
        """
        profissional = Profissional.objects.create(**self.profissional_data)

        self.assertEqual(profissional.nome_social, "Dr. João Silva")
        self.assertEqual(profissional.profissao, "MEDICO")
        self.assertEqual(profissional.email, "joao.silva@email.com")
        self.assertEqual(profissional.valor_consulta, Decimal("150.00"))
        self.assertTrue(profissional.aceita_convenio)
        self.assertTrue(profissional.is_active)
        self.assertIsNotNone(profissional.id)

    def test_nome_completo_property(self):
        """
        Testa a propriedade nome_completo
        """
        profissional = Profissional.objects.create(**self.profissional_data)

        # Com nome_registro preenchido
        self.assertEqual(profissional.nome_completo, "João Silva Santos")

        # Sem nome_registro
        profissional.nome_registro = ""
        self.assertEqual(profissional.nome_completo, "Dr. João Silva")

    def test_get_contato_formatado(self):
        """
        Testa o método get_contato_formatado
        """
        profissional = Profissional.objects.create(**self.profissional_data)
        contato_esperado = "📧 joao.silva@email.com | 📞 11987654321"

        self.assertEqual(profissional.get_contato_formatado(), contato_esperado)

    def test_get_contato_formatado_com_whatsapp(self):
        """
        Testa get_contato_formatado com WhatsApp
        """
        self.profissional_data["whatsapp"] = "11999888777"
        profissional = Profissional.objects.create(**self.profissional_data)
        contato_esperado = "📧 joao.silva@email.com | 📞 11987654321 | 📱 11999888777"

        self.assertEqual(profissional.get_contato_formatado(), contato_esperado)

    def test_email_unico(self):
        """
        Testa que email deve ser único
        """
        Profissional.objects.create(**self.profissional_data)

        # Tentar criar outro profissional com mesmo email
        profissional_data_2 = self.profissional_data.copy()
        profissional_data_2["nome_social"] = "Dr. Maria"

        with self.assertRaises(IntegrityError):
            Profissional.objects.create(**profissional_data_2)

    def test_validacao_email_formato(self):
        """
        Testa validação de formato de email
        """
        self.profissional_data["email"] = "email_invalido"

        with self.assertRaises(ValidationError):
            profissional = Profissional(**self.profissional_data)
            profissional.full_clean()

    def test_validacao_valor_consulta_negativo(self):
        """
        Testa que valor_consulta não pode ser negativo
        """
        self.profissional_data["valor_consulta"] = Decimal("-10.00")

        with self.assertRaises(ValidationError):
            profissional = Profissional(**self.profissional_data)
            profissional.full_clean()

    def test_choices_profissao(self):
        """
        Testa as choices de profissão
        """
        profissoes_validas = ["MEDICO", "PSICOLOGO", "NUTRICIONISTA", "FISIOTERAPEUTA", "ENFERMEIRO"]

        for profissao in profissoes_validas:
            self.profissional_data["profissao"] = profissao
            profissional = Profissional(**self.profissional_data)

            # Não deve gerar erro de validação
            profissional.full_clean()

    def test_profissao_invalida(self):
        """
        Testa profissão inválida
        """
        self.profissional_data["profissao"] = "PROFISSAO_INEXISTENTE"

        with self.assertRaises(ValidationError):
            profissional = Profissional(**self.profissional_data)
            profissional.full_clean()

    def test_campos_opcionais(self):
        """
        Testa que campos opcionais podem ser vazios
        """
        campos_opcionais = [
            "nome_registro",
            "registro_profissional",
            "especialidade",
            "whatsapp",
            "biografia",
            "valor_consulta",
        ]

        for campo in campos_opcionais:
            profissional_data = {
                "nome_social": "Dr. Test",
                "profissao": "MEDICO",
                "email": f"test_{campo}@email.com",
                "telefone": "11987654321",
                "endereco": self.endereco,
            }

            # Campo opcional pode ser None/vazio
            if campo == "valor_consulta":
                profissional_data[campo] = None
            else:
                profissional_data[campo] = ""

            profissional = Profissional(**profissional_data)
            profissional.full_clean()  # Não deve gerar erro

    def test_str_representation(self):
        """
        Testa representação string do modelo
        """
        profissional = Profissional.objects.create(**self.profissional_data)
        expected_str = "Dr. João Silva - Médico(a) - joao.silva@email.com"

        self.assertEqual(str(profissional), expected_str)

    def test_soft_delete(self):
        """
        Testa soft delete do profissional
        """
        profissional = Profissional.objects.create(**self.profissional_data)
        profissional_id = profissional.id

        # Desativar ao invés de deletar
        profissional.is_active = False
        profissional.save()

        # Profissional ainda existe no banco
        profissional_db = Profissional.objects.get(id=profissional_id)
        self.assertFalse(profissional_db.is_active)

        # Mas não aparece em queries do manager padrão (se implementado)
        profissionais_ativos = Profissional.objects.filter(is_active=True)
        self.assertNotIn(profissional, profissionais_ativos)

    def test_relacionamento_com_endereco(self):
        """
        Testa relacionamento com endereço
        """
        profissional = Profissional.objects.create(**self.profissional_data)

        self.assertEqual(profissional.endereco, self.endereco)
        self.assertEqual(profissional.endereco.cidade, "São Paulo")

    def test_metodos_business_logic(self):
        """
        Testa métodos de lógica de negócio (se existirem)
        """
        profissional = Profissional.objects.create(**self.profissional_data)

        # Testa se tem método para verificar disponibilidade
        if hasattr(profissional, "is_disponivel"):
            self.assertTrue(profissional.is_disponivel())

        # Testa método para cálculo de valor com desconto (se existir)
        if hasattr(profissional, "calcular_valor_com_desconto"):
            valor_com_desconto = profissional.calcular_valor_com_desconto(10)
            self.assertEqual(valor_com_desconto, Decimal("135.00"))


@pytest.mark.django_db
@pytest.mark.models
class TestProfissionalQueryset(TestCase):
    """
    Testes para queryset customizado do Profissional (se existir)
    """

    def setUp(self):
        """
        Configurar dados de teste
        """
        self.endereco = Endereco.objects.create(
            logradouro="Rua Teste", numero="100", bairro="Teste", cidade="São Paulo", estado="SP", cep="12345678"
        )

    def test_filtrar_por_profissao(self):
        """
        Testa filtro por profissão
        """
        # Criar profissionais de diferentes profissões
        Profissional.objects.create(
            nome_social="Dr. João", profissao="MEDICO", email="joao@test.com", telefone="11111111111", endereco=self.endereco
        )

        Profissional.objects.create(
            nome_social="Dra. Maria",
            profissao="PSICOLOGO",
            email="maria@test.com",
            telefone="11111111112",
            endereco=self.endereco,
        )

        medicos = Profissional.objects.filter(profissao="MEDICO")
        psicologos = Profissional.objects.filter(profissao="PSICOLOGO")

        self.assertEqual(medicos.count(), 1)
        self.assertEqual(psicologos.count(), 1)
        self.assertEqual(medicos.first().nome_social, "Dr. João")

    def test_filtrar_ativos(self):
        """
        Testa filtro por profissionais ativos
        """
        # Criar profissional ativo
        prof_ativo = Profissional.objects.create(
            nome_social="Dr. Ativo",
            profissao="MEDICO",
            email="ativo@test.com",
            telefone="11111111111",
            endereco=self.endereco,
            is_active=True,
        )

        # Criar profissional inativo
        prof_inativo = Profissional.objects.create(
            nome_social="Dr. Inativo",
            profissao="MEDICO",
            email="inativo@test.com",
            telefone="11111111112",
            endereco=self.endereco,
            is_active=False,
        )

        ativos = Profissional.objects.filter(is_active=True)

        self.assertEqual(ativos.count(), 1)
        self.assertIn(prof_ativo, ativos)
        self.assertNotIn(prof_inativo, ativos)
