"""
Testes para Validadores Customizados - Lacrei Saúde API
=======================================================
"""

import pytest

from django.core.exceptions import ValidationError
from django.test import TestCase

from lacrei_saude.validators import (
    sanitize_email,
    sanitize_html_content,
    sanitize_string,
    validate_cep,
    validate_cpf,
    validate_crm,
    validate_money_amount,
    validate_name,
    validate_observation,
    validate_password_strength,
    validate_phone,
)


@pytest.mark.unit
class TestSanitizeString(TestCase):
    """
    Testes para função sanitize_string
    """

    def test_sanitizacao_html_tags(self):
        """
        Testa remoção de tags HTML
        """
        texto_com_html = "<script>alert('xss')</script>Texto normal"
        resultado = sanitize_string(texto_com_html)

        self.assertNotIn("<script>", resultado)
        self.assertNotIn("</script>", resultado)
        self.assertIn("Texto normal", resultado)

    def test_sanitizacao_caracteres_perigosos(self):
        """
        Testa remoção de caracteres perigosos
        """
        texto_perigoso = "Texto com caracteres < > \" ' & ; ( ) { } perigosos"
        resultado = sanitize_string(texto_perigoso)

        caracteres_perigosos = ["<", ">", '"', "'", "&", ";", "(", ")", "{", "}"]
        for char in caracteres_perigosos:
            if char not in ["&lt;", "&gt;", "&quot;", "&#x27;", "&amp;"]:
                self.assertNotIn(char, resultado)

    def test_remocao_multiplos_espacos(self):
        """
        Testa remoção de múltiplos espaços
        """
        texto_com_espacos = "Texto    com     múltiplos   espaços"
        resultado = sanitize_string(texto_com_espacos)

        self.assertEqual(resultado, "Texto com múltiplos espaços")

    def test_trim_espacos_inicio_fim(self):
        """
        Testa remoção de espaços no início e fim
        """
        texto_com_espacos = "   Texto com espaços   "
        resultado = sanitize_string(texto_com_espacos)

        self.assertEqual(resultado, "Texto com espaços")

    def test_valor_nao_string(self):
        """
        Testa que valores não-string são retornados sem modificação
        """
        valores_nao_string = [123, None, [], {}]

        for valor in valores_nao_string:
            resultado = sanitize_string(valor)
            self.assertEqual(resultado, valor)


@pytest.mark.unit
class TestValidateCPF(TestCase):
    """
    Testes para validação de CPF
    """

    def test_cpf_valido(self):
        """
        Testa CPFs válidos
        """
        cpfs_validos = ["11144477735", "111.444.777-35", "12345678909", "123.456.789-09"]

        for cpf in cpfs_validos:
            try:
                resultado = validate_cpf(cpf)
                self.assertIsNotNone(resultado)
            except ValidationError:
                self.fail(f"CPF válido {cpf} foi rejeitado")

    def test_cpf_formato_invalido(self):
        """
        Testa CPFs com formato inválido
        """
        cpfs_invalidos = ["123", "123456789012", "abcdefghijk", ""]  # Muito curto  # Muito longo  # Não numérico  # Vazio

        for cpf in cpfs_invalidos:
            with self.assertRaises(ValidationError):
                validate_cpf(cpf)

    def test_cpf_digitos_iguais(self):
        """
        Testa CPFs com todos os dígitos iguais
        """
        cpfs_iguais = ["11111111111", "22222222222", "00000000000"]

        for cpf in cpfs_iguais:
            with self.assertRaises(ValidationError):
                validate_cpf(cpf)

    def test_cpf_digito_verificador_invalido(self):
        """
        Testa CPFs com dígitos verificadores incorretos
        """
        cpfs_digito_invalido = ["11144477736", "12345678901"]

        for cpf in cpfs_digito_invalido:
            with self.assertRaises(ValidationError):
                validate_cpf(cpf)


@pytest.mark.unit
class TestValidatePhone(TestCase):
    """
    Testes para validação de telefone
    """

    def test_telefone_valido(self):
        """
        Testa telefones válidos
        """
        telefones_validos = [
            "11987654321",  # Celular SP
            "1134567890",  # Fixo SP
            "2133334444",  # Rio de Janeiro
            "8533445566",  # Ceará
        ]

        for telefone in telefones_validos:
            try:
                resultado = validate_phone(telefone)
                self.assertIsNotNone(resultado)
            except ValidationError:
                self.fail(f"Telefone válido {telefone} foi rejeitado")

    def test_telefone_tamanho_invalido(self):
        """
        Testa telefones com tamanho incorreto
        """
        telefones_invalidos = ["123", "12345", "123456789012"]  # Muito curto  # Muito curto  # Muito longo

        for telefone in telefones_invalidos:
            with self.assertRaises(ValidationError):
                validate_phone(telefone)

    def test_codigo_area_invalido(self):
        """
        Testa códigos de área inválidos
        """
        telefones_ddd_invalido = ["0123456789", "9987654321", "0011999888777"]

        for telefone in telefones_ddd_invalido:
            with self.assertRaises(ValidationError):
                validate_phone(telefone)


@pytest.mark.unit
class TestValidateCEP(TestCase):
    """
    Testes para validação de CEP
    """

    def test_cep_valido(self):
        """
        Testa CEPs válidos
        """
        ceps_validos = ["01234567", "12345678", "98765432"]

        for cep in ceps_validos:
            try:
                resultado = validate_cep(cep)
                self.assertEqual(len(resultado), 8)
            except ValidationError:
                self.fail(f"CEP válido {cep} foi rejeitado")

    def test_cep_formato_invalido(self):
        """
        Testa CEPs com formato inválido
        """
        ceps_invalidos = [
            "123",  # Muito curto
            "123456789",  # Muito longo
            "abcdefgh",  # Não numérico
            "00000000",  # Todos zeros
        ]

        for cep in ceps_invalidos:
            with self.assertRaises(ValidationError):
                validate_cep(cep)


@pytest.mark.unit
class TestValidateCRM(TestCase):
    """
    Testes para validação de CRM
    """

    def test_crm_valido(self):
        """
        Testa CRMs válidos
        """
        casos_validos = [("123456", "SP"), ("12345", "RJ"), ("1234", "MG")]

        for crm, uf in casos_validos:
            try:
                resultado = validate_crm(crm, uf)
                self.assertEqual(resultado, crm)
            except ValidationError:
                self.fail(f"CRM válido {crm}/{uf} foi rejeitado")

    def test_crm_tamanho_invalido(self):
        """
        Testa CRMs com tamanho inválido
        """
        casos_invalidos = [("123", "SP"), ("1234567", "SP"), ("", "SP")]  # Muito curto  # Muito longo  # Vazio

        for crm, uf in casos_invalidos:
            with self.assertRaises(ValidationError):
                validate_crm(crm, uf)

    def test_crm_formato_invalido(self):
        """
        Testa CRMs com formato inválido
        """
        with self.assertRaises(ValidationError):
            validate_crm("ABC123", "SP")  # Com letras

    def test_uf_invalida(self):
        """
        Testa UFs inválidas
        """
        casos_uf_invalida = [
            ("12345", ""),  # UF vazia
            ("12345", "S"),  # UF muito curta
            ("12345", "SPP"),  # UF muito longa
            ("12345", None),  # UF None
        ]

        for crm, uf in casos_uf_invalida:
            with self.assertRaises(ValidationError):
                validate_crm(crm, uf)


@pytest.mark.unit
class TestValidatePasswordStrength(TestCase):
    """
    Testes para validação de força da senha
    """

    def test_senha_forte_valida(self):
        """
        Testa senhas fortes válidas
        """
        senhas_fortes = ["MinhaSenh@123", "Teste!234Forte", "S3nh@Compl3x@"]

        for senha in senhas_fortes:
            try:
                resultado = validate_password_strength(senha)
                self.assertEqual(resultado, senha)
            except ValidationError:
                self.fail(f"Senha forte {senha} foi rejeitada")

    def test_senha_muito_curta(self):
        """
        Testa senhas muito curtas
        """
        with self.assertRaises(ValidationError):
            validate_password_strength("Abc!1")

    def test_senha_sem_maiuscula(self):
        """
        Testa senhas sem letra maiúscula
        """
        with self.assertRaises(ValidationError):
            validate_password_strength("minhasenha@123")

    def test_senha_sem_minuscula(self):
        """
        Testa senhas sem letra minúscula
        """
        with self.assertRaises(ValidationError):
            validate_password_strength("MINHASENHA@123")

    def test_senha_sem_numero(self):
        """
        Testa senhas sem número
        """
        with self.assertRaises(ValidationError):
            validate_password_strength("MinhaSenha@")

    def test_senha_sem_especial(self):
        """
        Testa senhas sem caractere especial
        """
        with self.assertRaises(ValidationError):
            validate_password_strength("MinhaSenha123")


@pytest.mark.unit
class TestSanitizeEmail(TestCase):
    """
    Testes para sanitização de email
    """

    def test_email_valido(self):
        """
        Testa emails válidos
        """
        emails_validos = ["teste@email.com", "usuario@domain.com.br", "nome.sobrenome@empresa.org"]

        for email in emails_validos:
            try:
                resultado = sanitize_email(email)
                self.assertEqual(resultado.lower(), email.lower())
            except ValidationError:
                self.fail(f"Email válido {email} foi rejeitado")

    def test_email_uppercase_to_lowercase(self):
        """
        Testa conversão de email para minúsculo
        """
        email_upper = "TESTE@EMAIL.COM"
        resultado = sanitize_email(email_upper)
        self.assertEqual(resultado, "teste@email.com")

    def test_email_formato_invalido(self):
        """
        Testa emails com formato inválido
        """
        emails_invalidos = ["email_sem_arroba.com", "@domain.com", "email@", "email@domain", "email..duplo@domain.com"]

        for email in emails_invalidos:
            with self.assertRaises(ValidationError):
                sanitize_email(email)

    def test_email_com_espacos(self):
        """
        Testa remoção de espaços do email
        """
        email_com_espacos = "  teste@email.com  "
        resultado = sanitize_email(email_com_espacos)
        self.assertEqual(resultado, "teste@email.com")


@pytest.mark.unit
class TestValidateMoneyAmount(TestCase):
    """
    Testes para validação de valores monetários
    """

    def test_valor_valido(self):
        """
        Testa valores monetários válidos
        """
        valores_validos = [0, 10.50, 100, 999.99, 50000]

        for valor in valores_validos:
            try:
                resultado = validate_money_amount(valor)
                self.assertEqual(resultado, valor)
            except ValidationError:
                self.fail(f"Valor válido {valor} foi rejeitado")

    def test_valor_negativo(self):
        """
        Testa valores negativos
        """
        with self.assertRaises(ValidationError):
            validate_money_amount(-10)

    def test_valor_muito_alto(self):
        """
        Testa valores muito altos
        """
        with self.assertRaises(ValidationError):
            validate_money_amount(1000000)

    def test_valor_none(self):
        """
        Testa valor None
        """
        resultado = validate_money_amount(None)
        self.assertIsNone(resultado)


@pytest.mark.unit
class TestSanitizeHtmlContent(TestCase):
    """
    Testes para sanitização de conteúdo HTML
    """

    def test_remocao_tags_html(self):
        """
        Testa remoção de tags HTML
        """
        content_with_html = "<p>Parágrafo</p><strong>Texto forte</strong>"
        resultado = sanitize_html_content(content_with_html)

        self.assertNotIn("<p>", resultado)
        self.assertNotIn("</p>", resultado)
        self.assertNotIn("<strong>", resultado)
        self.assertIn("Parágrafo", resultado)
        self.assertIn("Texto forte", resultado)

    def test_escape_caracteres_html(self):
        """
        Testa escape de caracteres HTML
        """
        content = 'Texto com & < > " caracteres'
        resultado = sanitize_html_content(content)

        self.assertIn("&amp;", resultado)
        self.assertIn("&lt;", resultado)
        self.assertIn("&gt;", resultado)
        self.assertIn("&quot;", resultado)

    def test_conteudo_vazio(self):
        """
        Testa conteúdo vazio ou None
        """
        self.assertEqual(sanitize_html_content(""), "")
        self.assertIsNone(sanitize_html_content(None))


@pytest.mark.unit
class TestValidateName(TestCase):
    """
    Testes para validação de nomes
    """

    def test_nome_valido(self):
        """
        Testa nomes válidos
        """
        nomes_validos = ["João Silva", "Maria da Silva", "José-Carlos", "D'Angelo", "Ana"]

        for nome in nomes_validos:
            try:
                resultado = validate_name(nome)
                self.assertTrue(resultado.istitle())
            except ValidationError:
                self.fail(f"Nome válido {nome} foi rejeitado")

    def test_nome_muito_curto(self):
        """
        Testa nomes muito curtos
        """
        with self.assertRaises(ValidationError):
            validate_name("A")

    def test_nome_muito_longo(self):
        """
        Testa nomes muito longos
        """
        nome_longo = "A" * 101
        with self.assertRaises(ValidationError):
            validate_name(nome_longo)

    def test_nome_caracteres_invalidos(self):
        """
        Testa nomes com caracteres inválidos
        """
        nomes_invalidos = ["João123", "Maria@Silva", "José&Carlos"]

        for nome in nomes_invalidos:
            with self.assertRaises(ValidationError):
                validate_name(nome)

    def test_nome_vazio(self):
        """
        Testa nome vazio
        """
        with self.assertRaises(ValidationError):
            validate_name("")

    def test_nome_title_case(self):
        """
        Testa que o nome é retornado em Title Case
        """
        nome = "joão silva"
        resultado = validate_name(nome)
        self.assertEqual(resultado, "João Silva")


@pytest.mark.unit
class TestValidateObservation(TestCase):
    """
    Testes para validação de observações
    """

    def test_observacao_valida(self):
        """
        Testa observações válidas
        """
        observacoes_validas = ["Paciente relatou dor de cabeça", "Consulta de retorno em 30 dias", ""]  # Vazia é permitida

        for obs in observacoes_validas:
            try:
                resultado = validate_observation(obs)
                if obs:  # Se não for vazia
                    self.assertIsInstance(resultado, str)
            except ValidationError:
                self.fail(f"Observação válida foi rejeitada: {obs}")

    def test_observacao_muito_longa(self):
        """
        Testa observações muito longas
        """
        observacao_longa = "A" * 2001
        with self.assertRaises(ValidationError):
            validate_observation(observacao_longa)

    def test_observacao_com_html(self):
        """
        Testa que observações com HTML são sanitizadas
        """
        obs_com_html = '<script>alert("xss")</script>Observação normal'
        resultado = validate_observation(obs_com_html)

        self.assertNotIn("<script>", resultado)
        self.assertIn("Observação normal", resultado)

    def test_observacao_none(self):
        """
        Testa observação None
        """
        resultado = validate_observation(None)
        self.assertIsNone(resultado)
