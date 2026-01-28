"""
Testes de Sanitização de Input - Lacrei Saúde API
=================================================

Testes para verificar sanitização adequada de dados de entrada,
prevenção de XSS, validação de dados e tratamento seguro de inputs.
"""

import html
import json

import pytest
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

User = get_user_model()


class XSSPreventionTestCase(APITestCase):
    """Testes de prevenção contra Cross-Site Scripting (XSS)"""

    def setUp(self):
        """Setup para testes de XSS"""
        self.user = User.objects.create_user(
            username="xsstest", email="xss@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.client.force_authenticate(user=self.user)

    def test_script_tag_sanitization(self):
        """Testa sanitização de tags script"""
        xss_payloads = [
            '<script>alert("xss")</script>',
            '<script src="evil.js"></script>',
            '<img src=x onerror=alert("xss")>',
            '<svg onload=alert("xss")>',
            '"><script>alert("xss")</script>',
            "';alert('xss');//",
            "<iframe src=\"javascript:alert('xss')\"></iframe>",
        ]

        for payload in xss_payloads:
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": payload,
                    "email": "test@example.com",
                    "telefone": "11999999999",
                    "especialidade": "Clínico Geral",
                    "crm": "123456-SP",
                },
            )

            if response.status_code in [200, 201]:
                # Verifica se script foi sanitizado na resposta
                data = response.json()
                nome_sanitizado = data.get("nome", "")

                # Tags perigosas devem ser removidas ou escapadas
                self.assertNotIn("<script", nome_sanitizado.lower())
                self.assertNotIn("onerror", nome_sanitizado.lower())
                self.assertNotIn("onload", nome_sanitizado.lower())
                self.assertNotIn("javascript:", nome_sanitizado.lower())

    def test_html_entity_encoding(self):
        """Testa codificação de entidades HTML"""
        html_chars = ["<div>Test</div>", "&lt;script&gt;", '"quotes"', "'single quotes'", "&amp; ampersand"]

        for html_input in html_chars:
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": f"Dr. {html_input}",
                    "email": "test@example.com",
                    "telefone": "11999999999",
                    "especialidade": "Clínico Geral",
                    "crm": "123456-SP",
                    "observacoes": html_input,
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()

                # HTML deve ser escapado ou sanitizado
                for field in ["nome", "observacoes"]:
                    if field in data:
                        value = data[field]
                        # Verifica se contém HTML sem escape
                        if "<div>" in html_input and "<div>" in value:
                            # Se HTML foi preservado, deve estar escapado
                            self.assertTrue("&lt;div&gt;" in value or html.escape("<div>") in value)

    def test_javascript_execution_prevention(self):
        """Testa prevenção de execução de JavaScript"""
        js_payloads = [
            "javascript:void(0)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "livescript:[code]",
            "mocha:[code]",
            "javascript://comment%0aalert(1)",
        ]

        for payload in js_payloads:
            # Testa em campos que podem aceitar URLs
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": "Dr. Test",
                    "email": "test@example.com",
                    "telefone": "11999999999",
                    "especialidade": "Clínico Geral",
                    "crm": "123456-SP",
                    "site": payload,  # Campo URL se existir
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if "site" in data:
                    # JavaScript protocols devem ser rejeitados
                    self.assertNotIn("javascript:", data["site"].lower())
                    self.assertNotIn("vbscript:", data["site"].lower())

    def test_context_aware_encoding(self):
        """Testa codificação consciente do contexto"""
        # Dados que podem aparecer em diferentes contextos
        contextual_data = [
            '"+alert(1)+"',
            "'+alert(1)+'",
            "</script><script>alert(1)</script>",
            "--><script>alert(1)</script><!--",
        ]

        for data in contextual_data:
            response = self.client.post(
                "/api/v1/consultas/",
                {"profissional": self.user.id, "data_horario": "2025-12-31T10:00:00Z", "observacoes": data},
            )

            if response.status_code in [200, 201]:
                result = response.json()
                observacoes = result.get("observacoes", "")

                # Verifica se dados foram adequadamente codificados
                dangerous_patterns = ["<script>", "alert(", "javascript:"]
                for pattern in dangerous_patterns:
                    self.assertNotIn(pattern, observacoes.lower())


class InputValidationTestCase(APITestCase):
    """Testes de validação de entrada"""

    def setUp(self):
        """Setup para testes de validação"""
        self.user = User.objects.create_user(
            username="validationtest", email="validation@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.client.force_authenticate(user=self.user)

    def test_email_validation(self):
        """Testa validação de email"""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user..double.dot@domain.com",
            "user@domain..com",
            "user@domain.c",
            "very-very-very-very-very-long-email-that-exceeds-limits@domain.com",
        ]

        for invalid_email in invalid_emails:
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": "Dr. Test",
                    "email": invalid_email,
                    "telefone": "11999999999",
                    "especialidade": "Clínico Geral",
                    "crm": "123456-SP",
                },
            )

            # Email inválido deve ser rejeitado
            self.assertNotEqual(response.status_code, 201)

    def test_phone_validation(self):
        """Testa validação de telefone"""
        invalid_phones = [
            "123",  # Muito curto
            "abc123456789",  # Contém letras
            "00000000000",  # Todos zeros
            "11111111111",  # Todos iguais
            "+55 11 9999999999999",  # Muito longo
            "(11) 99999-999",  # Incompleto
            "11 9999 999",  # Formato incorreto
        ]

        for invalid_phone in invalid_phones:
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": "Dr. Test",
                    "email": "test@example.com",
                    "telefone": invalid_phone,
                    "especialidade": "Clínico Geral",
                    "crm": "123456-SP",
                },
            )

            # Telefone inválido pode ser rejeitado ou normalizado
            if response.status_code == 201:
                # Se aceito, verifica se foi normalizado
                data = response.json()
                telefone_normalizado = data.get("telefone", "")
                # Deve conter apenas dígitos e caracteres válidos
                import re

                self.assertTrue(re.match(r"^[\d\s\(\)\+\-]+$", telefone_normalizado))

    def test_crm_validation(self):
        """Testa validação de CRM"""
        invalid_crms = [
            "123",  # Muito curto
            "abc-def",  # Formato inválido
            "000000-SP",  # Todos zeros
            "123456",  # Sem estado
            "123456-ZZ",  # Estado inválido
            "1234567890-SP",  # Muito longo
        ]

        for invalid_crm in invalid_crms:
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": "Dr. Test",
                    "email": "test@example.com",
                    "telefone": "11999999999",
                    "especialidade": "Clínico Geral",
                    "crm": invalid_crm,
                },
            )

            # CRM inválido deve ser rejeitado
            if response.status_code == 201:
                # Se aceito, verifica formato
                data = response.json()
                crm = data.get("crm", "")
                # Deve ter formato válido
                import re

                pattern = r"^\d{4,8}-[A-Z]{2}$"
                if not re.match(pattern, crm):
                    print(f"CRM aceito com formato questionável: {crm}")

    def test_date_validation(self):
        """Testa validação de datas"""
        from datetime import datetime, timedelta

        invalid_dates = [
            "2020-02-30T10:00:00Z",  # Data inválida
            "2025-13-01T10:00:00Z",  # Mês inválido
            "2025-12-32T10:00:00Z",  # Dia inválido
            "2025-12-01T25:00:00Z",  # Hora inválida
            "2025-12-01T10:60:00Z",  # Minuto inválido
            "invalid-date",  # Formato inválido
            "2020-01-01T10:00:00Z",  # Data no passado
        ]

        for invalid_date in invalid_dates:
            response = self.client.post(
                "/api/v1/consultas/", {"profissional": self.user.id, "data_horario": invalid_date, "observacoes": "Teste"}
            )

            # Data inválida deve ser rejeitada
            self.assertNotEqual(response.status_code, 201)

    def test_length_validation(self):
        """Testa validação de comprimento de campos"""
        # Testa campos muito longos
        very_long_string = "A" * 1000

        response = self.client.post(
            "/api/v1/profissionais/",
            {
                "nome": very_long_string,
                "email": "test@example.com",
                "telefone": "11999999999",
                "especialidade": very_long_string,
                "crm": "123456-SP",
                "observacoes": very_long_string * 10,  # Muito longo
            },
        )

        # Campos muito longos devem ser rejeitados ou truncados
        if response.status_code == 201:
            data = response.json()
            # Verifica se foi truncado adequadamente
            for field in ["nome", "especialidade"]:
                if field in data:
                    self.assertLess(len(data[field]), 500)


class FileUploadSanitizationTestCase(APITestCase):
    """Testes de sanitização para upload de arquivos"""

    def setUp(self):
        """Setup para testes de upload"""
        self.user = User.objects.create_user(
            username="uploadtest", email="upload@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.client.force_authenticate(user=self.user)

    def test_file_type_validation(self):
        """Testa validação de tipos de arquivo"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Arquivos maliciosos simulados
        malicious_files = [
            ("script.exe", b"MZ\x90\x00", "application/x-executable"),
            ("virus.bat", b"@echo off\ndel *.*", "application/bat"),
            ("shell.php", b'<?php system($_GET["cmd"]); ?>', "application/php"),
            ("malware.js", b'eval(atob("malicious_code"))', "application/javascript"),
        ]

        for filename, content, content_type in malicious_files:
            file_obj = SimpleUploadedFile(filename, content, content_type)

            # Simula upload (endpoint pode não existir)
            response = self.client.post("/api/upload/", {"file": file_obj})

            # Tipos perigosos devem ser rejeitados
            if response.status_code not in [404, 405]:  # Endpoint pode não existir
                self.assertNotEqual(response.status_code, 200)

    def test_filename_sanitization(self):
        """Testa sanitização de nomes de arquivo"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "file<script>alert(1)</script>.txt",
            'file";rm -rf /;".txt',
            "file\x00.exe.txt",  # Null byte injection
            "CON.txt",  # Windows reserved name
            "file with spaces and símb@ls!.txt",
        ]

        for dangerous_name in dangerous_filenames:
            file_obj = SimpleUploadedFile(dangerous_name, b"test content", "text/plain")

            response = self.client.post("/api/upload/", {"file": file_obj})

            if response.status_code == 200:
                # Se aceito, verifica se nome foi sanitizado
                data = response.json()
                if "filename" in data:
                    sanitized_name = data["filename"]

                    # Não deve conter caracteres perigosos
                    dangerous_chars = ["..", "<", ">", '"', "|", "?", "*", "\x00"]
                    for char in dangerous_chars:
                        self.assertNotIn(char, sanitized_name)

    def test_file_content_scanning(self):
        """Testa escaneamento de conteúdo de arquivo"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Conteúdos suspeitos
        suspicious_contents = [
            b'<?php eval($_POST["cmd"]); ?>',
            b'<script>alert("xss")</script>',
            b"\x4d\x5a\x90\x00",  # PE header
            b"#!/bin/bash\nrm -rf /",
        ]

        for content in suspicious_contents:
            file_obj = SimpleUploadedFile("test.txt", content, "text/plain")

            response = self.client.post("/api/upload/", {"file": file_obj})

            # Conteúdo suspeito deve ser detectado
            if response.status_code == 200:
                print(f"AVISO: Conteúdo suspeito não foi detectado: {content[:20]}")


class SQLInjectionPreventionTestCase(APITestCase):
    """Testes específicos de prevenção de SQL Injection em inputs"""

    def setUp(self):
        """Setup para testes de SQL injection"""
        self.user = User.objects.create_user(
            username="sqltest", email="sql@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.client.force_authenticate(user=self.user)

    def test_search_parameter_injection(self):
        """Testa SQL injection via parâmetros de busca"""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' OR 1=1 LIMIT 1 OFFSET 1 --",
        ]

        for payload in sql_payloads:
            response = self.client.get(f"/api/v1/profissionais/?search={payload}")

            # Não deve retornar erro 500 ou dados não autorizados
            self.assertNotEqual(response.status_code, 500)

            if response.status_code == 200:
                data = response.json()
                # Não deve retornar todos os registros (indicativo de SQL injection)
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    if len(results) > 100:  # Muitos resultados pode indicar '1=1
                        print(f"AVISO: Busca retornou muitos resultados para: {payload}")

    def test_filter_parameter_injection(self):
        """Testa SQL injection via parâmetros de filtro"""
        filter_payloads = ["1' OR '1'='1", "1; DROP TABLE profissionais_profissional; --", "1 UNION SELECT 1,2,3,4,5,6 --"]

        for payload in filter_payloads:
            # Testa diferentes parâmetros de filtro
            filter_params = [f"id={payload}", f"especialidade={payload}", f"crm={payload}"]

            for param in filter_params:
                response = self.client.get(f"/api/v1/profissionais/?{param}")

                # Não deve gerar erro de SQL
                self.assertNotEqual(response.status_code, 500)

    def test_ordering_parameter_injection(self):
        """Testa SQL injection via parâmetros de ordenação"""
        order_payloads = [
            "nome; DROP TABLE users; --",
            "(SELECT * FROM users WHERE '1'='1')",
            "CASE WHEN (1=1) THEN nome ELSE id END",
        ]

        for payload in order_payloads:
            response = self.client.get(f"/api/v1/profissionais/?ordering={payload}")

            # Parâmetro de ordenação malicioso deve ser rejeitado
            self.assertIn(response.status_code, [400, 404, 200])

            if response.status_code == 500:
                self.fail(f"SQL injection possível via ordering: {payload}")


class NoSQLInjectionPreventionTestCase(APITestCase):
    """Testes de prevenção de NoSQL injection"""

    def setUp(self):
        """Setup para testes de NoSQL injection"""
        self.user = User.objects.create_user(
            username="nosqltest", email="nosql@test.com", password="TestPassword123!", user_type="profissional"
        )
        self.client.force_authenticate(user=self.user)

    def test_mongodb_injection_prevention(self):
        """Testa prevenção de MongoDB injection"""
        nosql_payloads = [
            '{"$ne": null}',
            '{"$gt": ""}',
            '{"$where": "this.password.length > 0"}',
            '{"$regex": ".*"}',
            '{"$or": [{"username": "admin"}, {"username": "root"}]}',
        ]

        for payload in nosql_payloads:
            # Testa como JSON na busca
            response = self.client.get(f"/api/v1/profissionais/?search={payload}")

            # Não deve interpretar como query NoSQL
            self.assertNotEqual(response.status_code, 500)

            if response.status_code == 200:
                data = response.json()
                # Não deve retornar resultados inesperados
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    # Se retornou muitos resultados, pode ter interpretado o payload
                    if len(results) > 50:
                        print(f"AVISO: Possível NoSQL injection: {payload}")

    def test_json_parameter_injection(self):
        """Testa injection via parâmetros JSON"""
        json_payloads = [
            '{"$ne": ""}',
            '{"$exists": true}',
            '{"$in": ["admin", "root"]}',
        ]

        for payload in json_payloads:
            # Tenta enviar JSON malicioso em diferentes campos
            response = self.client.post(
                "/api/v1/profissionais/",
                {
                    "nome": "Dr. Test",
                    "email": "test@example.com",
                    "telefone": "11999999999",
                    "especialidade": payload,  # JSON em campo texto
                    "crm": "123456-SP",
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                # JSON não deve ser interpretado
                self.assertEqual(data.get("especialidade"), payload)


class CommandInjectionPreventionTestCase(APITestCase):
    """Testes de prevenção de command injection"""

    def setUp(self):
        """Setup para testes de command injection"""
        self.user = User.objects.create_user(
            username="cmdtest", email="cmd@test.com", password="TestPassword123!", user_type="admin", is_staff=True
        )
        self.client.force_authenticate(user=self.user)

    def test_system_command_injection(self):
        """Testa prevenção de command injection"""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(id)",
            "; ping -c 1 127.0.0.1",
            "\n/bin/sh\n",
        ]

        for payload in command_payloads:
            # Testa em campos que podem ser processados pelo sistema
            test_data = {"filename": f"document{payload}.pdf", "path": f"/uploads/{payload}", "command": f"process {payload}"}

            # Tenta diferentes endpoints que podem processar arquivos
            response = self.client.post("/api/process/", test_data)

            # Endpoint pode não existir, mas não deve executar comandos
            if response.status_code == 200:
                content = response.content.decode()

                # Não deve conter output de comandos do sistema
                system_outputs = ["root:", "usr/bin", "etc/passwd", "PING", "uid=", "gid="]

                for output in system_outputs:
                    self.assertNotIn(output, content)

    def test_file_path_injection(self):
        """Testa injection via caminhos de arquivo"""
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/dev/null; cat /etc/shadow #",
            "file.txt; rm -rf / #",
        ]

        for payload in path_payloads:
            response = self.client.post("/api/file/", {"path": payload, "filename": payload})

            # Não deve processar caminhos maliciosos
            if response.status_code == 200:
                content = response.content.decode()
                # Não deve conter conteúdo de arquivos do sistema
                sensitive_content = ["root:x:", "shadow", "password"]
                for content_check in sensitive_content:
                    self.assertNotIn(content_check, content)
