"""
Modelos para Profissionais da Saúde - Lacrei Saúde API
=======================================================
"""

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.db import models

from lacrei_saude.models import BaseModelWithManager


class Endereco(BaseModelWithManager):
    """
    Modelo para endereços
    """

    logradouro = models.CharField(max_length=200, help_text="Rua, avenida, alameda, etc.")
    numero = models.CharField(max_length=10, help_text="Número do endereço")
    complemento = models.CharField(max_length=100, blank=True, help_text="Apartamento, sala, bloco, etc.")
    bairro = models.CharField(max_length=100, help_text="Bairro ou distrito")
    cidade = models.CharField(max_length=100, help_text="Cidade")
    estado = models.CharField(
        max_length=2,
        choices=[
            ("AC", "Acre"),
            ("AL", "Alagoas"),
            ("AP", "Amapá"),
            ("AM", "Amazonas"),
            ("BA", "Bahia"),
            ("CE", "Ceará"),
            ("DF", "Distrito Federal"),
            ("ES", "Espírito Santo"),
            ("GO", "Goiás"),
            ("MA", "Maranhão"),
            ("MT", "Mato Grosso"),
            ("MS", "Mato Grosso do Sul"),
            ("MG", "Minas Gerais"),
            ("PA", "Pará"),
            ("PB", "Paraíba"),
            ("PR", "Paraná"),
            ("PE", "Pernambuco"),
            ("PI", "Piauí"),
            ("RJ", "Rio de Janeiro"),
            ("RN", "Rio Grande do Norte"),
            ("RS", "Rio Grande do Sul"),
            ("RO", "Rondônia"),
            ("RR", "Roraima"),
            ("SC", "Santa Catarina"),
            ("SP", "São Paulo"),
            ("SE", "Sergipe"),
            ("TO", "Tocantins"),
        ],
        help_text="Estado (UF)",
    )
    cep = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r"^\d{5}-?\d{3}$", message="CEP deve estar no formato 00000-000")],
        help_text="Código de Endereçamento Postal",
    )
    referencia = models.CharField(max_length=200, blank=True, help_text="Ponto de referência próximo")

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        indexes = [
            models.Index(fields=["cidade", "estado"]),
            models.Index(fields=["cep"]),
        ]

    def __str__(self):
        return f"{self.logradouro}, {self.numero} - {self.bairro}, {self.cidade}/{self.estado}"

    def clean(self):
        """Validações customizadas"""
        super().clean()

        # Normalizar CEP
        if self.cep:
            self.cep = self.cep.replace("-", "")
            if len(self.cep) == 8:
                self.cep = f"{self.cep[:5]}-{self.cep[5:]}"

    @property
    def endereco_completo(self):
        """Retorna endereço formatado completo"""
        partes = [f"{self.logradouro}, {self.numero}"]

        if self.complemento:
            partes.append(self.complemento)

        partes.extend([self.bairro, f"{self.cidade}/{self.estado}", f"CEP: {self.cep}"])

        return " - ".join(partes)


class Profissional(BaseModelWithManager):
    """
    Modelo para Profissionais da Saúde
    """

    # Choices para profissões (pode ser expandido)
    PROFISSOES_CHOICES = [
        ("MEDICO", "Médico(a)"),
        ("ENFERMEIRO", "Enfermeiro(a)"),
        ("PSICOLOGO", "Psicólogo(a)"),
        ("FISIOTERAPEUTA", "Fisioterapeuta"),
        ("NUTRICIONISTA", "Nutricionista"),
        ("DENTISTA", "Dentista"),
        ("FONOAUDIOLOGO", "Fonoaudiólogo(a)"),
        ("TERAPEUTA_OCUPACIONAL", "Terapeuta Ocupacional"),
        ("FARMACEUTICO", "Farmacêutico(a)"),
        ("ASSISTENTE_SOCIAL", "Assistente Social"),
        ("OUTRO", "Outro"),
    ]

    nome_social = models.CharField(max_length=150, help_text="Nome pelo qual o profissional prefere ser chamado")
    nome_registro = models.CharField(max_length=150, blank=True, help_text="Nome civil/registro (opcional, para documentos)")
    profissao = models.CharField(max_length=30, choices=PROFISSOES_CHOICES, help_text="Área de atuação profissional")
    registro_profissional = models.CharField(max_length=50, blank=True, help_text="CRM, CRE, CRP, etc.")
    especialidade = models.CharField(max_length=100, blank=True, help_text="Especialização ou área específica")

    # Contato
    email = models.EmailField(unique=True, validators=[EmailValidator()], help_text="Email profissional")
    telefone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\(?[1-9]{2}\)?\s?9?[0-9]{4}-?[0-9]{4}$",
                message="Telefone deve estar no formato (11) 99999-9999 ou (11) 9999-9999",
            )
        ],
        help_text="Telefone com DDD",
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\(?[1-9]{2}\)?\s?9?[0-9]{4}-?[0-9]{4}$", message="WhatsApp deve estar no formato (11) 99999-9999"
            )
        ],
        help_text="WhatsApp (opcional)",
    )

    # Endereço
    endereco = models.ForeignKey(
        Endereco, on_delete=models.PROTECT, related_name="profissionais", help_text="Endereço de atendimento"
    )

    # Informações complementares
    biografia = models.TextField(blank=True, max_length=1000, help_text="Breve descrição profissional")
    aceita_convenio = models.BooleanField(default=False, help_text="Aceita convênios médicos")
    valor_consulta = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Valor da consulta particular"
    )

    class Meta:
        verbose_name = "Profissional"
        verbose_name_plural = "Profissionais"
        indexes = [
            models.Index(fields=["profissao"]),
            models.Index(fields=["nome_social"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.nome_social} - {self.get_profissao_display()}"

    def clean(self):
        """Validações customizadas"""
        super().clean()

        # Normalizar telefones
        if self.telefone:
            self.telefone = self._normalizar_telefone(self.telefone)

        if self.whatsapp:
            self.whatsapp = self._normalizar_telefone(self.whatsapp)

        # Email em lowercase
        if self.email:
            self.email = self.email.lower()

        # Validar registro profissional
        if self.registro_profissional:
            self._validar_registro_profissional()

    def _normalizar_telefone(self, telefone):
        """Normaliza formato do telefone"""
        # Remove caracteres especiais
        numeros = "".join(filter(str.isdigit, telefone))

        # Formatar conforme tamanho
        if len(numeros) == 11:  # Celular com 9
            return f"({numeros[:2]}) {numeros[2]}{numeros[3:7]}-{numeros[7:]}"
        elif len(numeros) == 10:  # Fixo
            return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"

        return telefone  # Retorna original se não conseguir formatar

    def _validar_registro_profissional(self):
        """Valida formato do registro profissional"""
        # Implementar validações específicas por profissão se necessário
        # Por enquanto, apenas validação básica
        if len(self.registro_profissional.strip()) < 3:
            raise ValidationError("Registro profissional muito curto")

    @property
    def nome_completo(self):
        """Retorna nome completo considerando registro"""
        if self.nome_registro and self.nome_registro != self.nome_social:
            return f"{self.nome_social} ({self.nome_registro})"
        return self.nome_social

    def get_contato_formatado(self):
        """Retorna contato formatado"""
        contato = [f"📧 {self.email}", f"📞 {self.telefone}"]
        if self.whatsapp:
            contato.append(f"📱 {self.whatsapp}")
        return " | ".join(contato)
