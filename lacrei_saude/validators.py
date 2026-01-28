"""
Validadores personalizados - Lacrei Saúde API
============================================
"""

import re
import html
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def sanitize_string(value):
    """
    Sanitiza strings removendo caracteres perigosos
    """
    if not isinstance(value, str):
        return value
    
    # Remove HTML tags
    value = html.escape(value)
    
    # Remove caracteres perigosos
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
    for char in dangerous_chars:
        if char in value and char not in ['&lt;', '&gt;', '&quot;', '&#x27;', '&amp;']:
            value = value.replace(char, '')
    
    # Remove múltiplos espaços
    value = re.sub(r'\s+', ' ', value).strip()
    
    return value


def validate_cpf(cpf):
    """
    Valida CPF brasileiro
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        raise ValidationError(_('CPF deve ter 11 dígitos'))
    
    # Verifica se não são todos iguais
    if cpf == cpf[0] * 11:
        raise ValidationError(_('CPF inválido'))
    
    # Validação do primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        raise ValidationError(_('CPF inválido'))
    
    # Validação do segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[10]) != digito2:
        raise ValidationError(_('CPF inválido'))
    
    return cpf


def validate_phone(phone):
    """
    Valida telefone brasileiro
    """
    # Remove caracteres não numéricos
    phone = re.sub(r'[^0-9]', '', str(phone))
    
    # Verifica se tem 10 ou 11 dígitos
    if len(phone) not in [10, 11]:
        raise ValidationError(_('Telefone deve ter 10 ou 11 dígitos'))
    
    # Verifica se começa com código de área válido
    if phone[:2] not in ['11', '12', '13', '14', '15', '16', '17', '18', '19',
                         '21', '22', '24', '27', '28', '31', '32', '33', '34',
                         '35', '37', '38', '41', '42', '43', '44', '45', '46',
                         '47', '48', '49', '51', '53', '54', '55', '61', '62',
                         '63', '64', '65', '66', '67', '68', '69', '71', '73',
                         '74', '75', '77', '79', '81', '82', '83', '84', '85',
                         '86', '87', '88', '89', '91', '92', '93', '94', '95',
                         '96', '97', '98', '99']:
        raise ValidationError(_('Código de área inválido'))
    
    return phone


def validate_cep(cep):
    """
    Valida CEP brasileiro
    """
    # Remove caracteres não numéricos
    cep = re.sub(r'[^0-9]', '', str(cep))
    
    if len(cep) != 8:
        raise ValidationError(_('CEP deve ter 8 dígitos'))
    
    # Verifica se não são todos zeros
    if cep == '00000000':
        raise ValidationError(_('CEP inválido'))
    
    return cep


def validate_crm(crm, uf):
    """
    Valida CRM
    """
    crm = str(crm).strip()
    
    if not crm:
        raise ValidationError(_('CRM é obrigatório'))
    
    # Verifica se contém apenas números
    if not re.match(r'^\d+$', crm):
        raise ValidationError(_('CRM deve conter apenas números'))
    
    # Verifica tamanho (geralmente entre 4 e 6 dígitos)
    if len(crm) < 4 or len(crm) > 6:
        raise ValidationError(_('CRM deve ter entre 4 e 6 dígitos'))
    
    # UF deve ter 2 caracteres
    if not uf or len(uf) != 2:
        raise ValidationError(_('UF deve ter 2 caracteres'))
    
    return crm


def validate_password_strength(password):
    """
    Valida força da senha
    """
    if len(password) < 8:
        raise ValidationError(_('Senha deve ter pelo menos 8 caracteres'))
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError(_('Senha deve ter pelo menos uma letra maiúscula'))
    
    if not re.search(r'[a-z]', password):
        raise ValidationError(_('Senha deve ter pelo menos uma letra minúscula'))
    
    if not re.search(r'[0-9]', password):
        raise ValidationError(_('Senha deve ter pelo menos um número'))
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(_('Senha deve ter pelo menos um caractere especial'))
    
    return password


def sanitize_email(email):
    """
    Sanitiza email
    """
    if not email:
        return email
    
    email = str(email).strip().lower()
    
    # Validação básica de formato
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise ValidationError(_('Email inválido'))
    
    return email


def validate_money_amount(amount):
    """
    Valida valor monetário
    """
    if amount is None:
        return amount
    
    if amount < 0:
        raise ValidationError(_('Valor não pode ser negativo'))
    
    if amount > 999999.99:
        raise ValidationError(_('Valor muito alto'))
    
    return amount


def sanitize_html_content(content):
    """
    Sanitiza conteúdo HTML removendo tags perigosas
    """
    if not content:
        return content
    
    # Lista de tags permitidas (apenas para texto)
    allowed_tags = []
    
    # Remove todas as tags HTML
    clean_content = re.sub(r'<[^>]+>', '', content)
    
    # Escapa caracteres HTML
    clean_content = html.escape(clean_content)
    
    return clean_content


def validate_name(name):
    """
    Valida nomes (apenas letras, espaços e alguns caracteres especiais)
    """
    if not name:
        raise ValidationError(_('Nome é obrigatório'))
    
    name = name.strip()
    
    if len(name) < 2:
        raise ValidationError(_('Nome deve ter pelo menos 2 caracteres'))
    
    if len(name) > 100:
        raise ValidationError(_('Nome muito longo'))
    
    # Permite apenas letras, espaços, hífen e apóstrofe
    if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']+$", name):
        raise ValidationError(_('Nome contém caracteres inválidos'))
    
    return name.title()


def validate_observation(text):
    """
    Valida observações e textos livres
    """
    if not text:
        return text
    
    text = sanitize_string(text)
    
    if len(text) > 2000:
        raise ValidationError(_('Texto muito longo (máximo 2000 caracteres)'))
    
    return text