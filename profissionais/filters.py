"""
Filtros personalizados para Profissionais - Lacrei Saúde API
============================================================
"""

import django_filters
from django import forms
from .models import Profissional, Endereco


class ProfissionalFilter(django_filters.FilterSet):
    """
    Filtros avançados para Profissionais
    """
    
    # Filtro por nome (múltiplas variações)
    nome = django_filters.CharFilter(
        method='filter_nome',
        label='Nome (busca em nome social e registro)'
    )
    
    # Filtros por valor da consulta
    valor_min = django_filters.NumberFilter(
        field_name='valor_consulta',
        lookup_expr='gte',
        label='Valor mínimo da consulta'
    )
    valor_max = django_filters.NumberFilter(
        field_name='valor_consulta',
        lookup_expr='lte',
        label='Valor máximo da consulta'
    )
    
    # Filtros de localização
    estado = django_filters.ChoiceFilter(
        field_name='endereco__estado',
        choices=[
            ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'),
            ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'),
            ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'),
            ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'),
            ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
            ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'),
            ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'),
            ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'),
            ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'),
            ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins'),
        ],
        label='Estado'
    )
    cidade = django_filters.CharFilter(
        field_name='endereco__cidade',
        lookup_expr='icontains',
        label='Cidade'
    )
    bairro = django_filters.CharFilter(
        field_name='endereco__bairro',
        lookup_expr='icontains',
        label='Bairro'
    )
    cep = django_filters.CharFilter(
        field_name='endereco__cep',
        lookup_expr='icontains',
        label='CEP'
    )
    
    # Filtro por especialidade
    especialidade = django_filters.CharFilter(
        field_name='especialidade',
        lookup_expr='icontains',
        label='Especialidade'
    )
    
    # Filtros por contato
    telefone = django_filters.CharFilter(
        field_name='telefone',
        lookup_expr='icontains',
        label='Telefone'
    )
    email = django_filters.CharFilter(
        field_name='email',
        lookup_expr='icontains',
        label='Email'
    )
    
    # Filtros por profissão múltipla
    profissao_in = django_filters.BaseInFilter(
        field_name='profissao',
        lookup_expr='in',
        label='Profissões (múltiplas)'
    )
    
    # Filtro por disponibilidade
    disponivel = django_filters.BooleanFilter(
        method='filter_disponivel',
        label='Disponível para consultas'
    )
    
    # Filtro por faixa de preço
    faixa_preco = django_filters.ChoiceFilter(
        method='filter_faixa_preco',
        choices=[
            ('ate_100', 'Até R$ 100'),
            ('100_200', 'R$ 100 - R$ 200'),
            ('200_300', 'R$ 200 - R$ 300'),
            ('acima_300', 'Acima de R$ 300'),
        ],
        label='Faixa de preço'
    )

    class Meta:
        model = Profissional
        fields = [
            'profissao', 'aceita_convenio', 'is_active'
        ]

    def filter_nome(self, queryset, name, value):
        """
        Buscar por nome social ou nome de registro
        """
        from django.db.models import Q
        return queryset.filter(
            Q(nome_social__icontains=value) | 
            Q(nome_registro__icontains=value)
        )

    def filter_disponivel(self, queryset, name, value):
        """
        Filtrar profissionais disponíveis
        """
        if value:
            return queryset.filter(is_active=True)
        return queryset

    def filter_faixa_preco(self, queryset, name, value):
        """
        Filtrar por faixa de preço
        """
        from django.db.models import Q
        
        if value == 'ate_100':
            return queryset.filter(
                Q(valor_consulta__lte=100) | Q(valor_consulta__isnull=True)
            )
        elif value == '100_200':
            return queryset.filter(
                valor_consulta__gt=100, valor_consulta__lte=200
            )
        elif value == '200_300':
            return queryset.filter(
                valor_consulta__gt=200, valor_consulta__lte=300
            )
        elif value == 'acima_300':
            return queryset.filter(valor_consulta__gt=300)
        
        return queryset