"""
Filtros personalizados para Consultas - Lacrei Saúde API
========================================================
"""

import django_filters
from django import forms
from django.db import models
from .models import Consulta
from profissionais.models import Profissional


class ConsultaFilter(django_filters.FilterSet):
    """
    Filtros avançados para Consultas
    """
    
    # Filtros por data
    data_inicio = django_filters.DateFilter(
        field_name='data_hora__date', 
        lookup_expr='gte',
        label='Data início',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    data_fim = django_filters.DateFilter(
        field_name='data_hora__date', 
        lookup_expr='lte',
        label='Data fim',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    # Filtro por mês e ano
    mes = django_filters.NumberFilter(
        field_name='data_hora__month',
        label='Mês (1-12)'
    )
    ano = django_filters.NumberFilter(
        field_name='data_hora__year',
        label='Ano'
    )
    
    # Filtro por valor
    valor_min = django_filters.NumberFilter(
        field_name='valor_consulta', 
        lookup_expr='gte',
        label='Valor mínimo'
    )
    valor_max = django_filters.NumberFilter(
        field_name='valor_consulta', 
        lookup_expr='lte',
        label='Valor máximo'
    )
    
    # Filtros por profissional
    profissional_nome = django_filters.CharFilter(
        field_name='profissional__nome_social',
        lookup_expr='icontains',
        label='Nome do profissional'
    )
    profissional_profissao = django_filters.ChoiceFilter(
        field_name='profissional__profissao',
        choices=Profissional.PROFISSOES_CHOICES,
        label='Profissão'
    )
    profissional_cidade = django_filters.CharFilter(
        field_name='profissional__endereco__cidade',
        lookup_expr='icontains',
        label='Cidade do profissional'
    )
    
    # Filtros por paciente
    paciente_nome = django_filters.CharFilter(
        field_name='nome_paciente',
        lookup_expr='icontains',
        label='Nome do paciente'
    )
    paciente_telefone = django_filters.CharFilter(
        field_name='telefone_paciente',
        lookup_expr='icontains',
        label='Telefone do paciente'
    )
    
    # Filtros por status múltiplos
    status_in = django_filters.BaseInFilter(
        field_name='status',
        lookup_expr='in',
        label='Status (múltiplos)'
    )
    
    # Filtro por consultas futuras/passadas
    periodo = django_filters.ChoiceFilter(
        method='filter_periodo',
        choices=[
            ('futuras', 'Futuras'),
            ('passadas', 'Passadas'),
            ('hoje', 'Hoje'),
            ('esta_semana', 'Esta semana'),
            ('este_mes', 'Este mês'),
        ],
        label='Período'
    )
    
    # Filtro por horário
    horario_inicio = django_filters.TimeFilter(
        field_name='data_hora__time',
        lookup_expr='gte',
        label='Horário início',
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    horario_fim = django_filters.TimeFilter(
        field_name='data_hora__time',
        lookup_expr='lte',
        label='Horário fim',
        widget=forms.TimeInput(attrs={'type': 'time'})
    )

    class Meta:
        model = Consulta
        fields = [
            'status', 'tipo_consulta', 'forma_pagamento', 'pago',
            'profissional', 'profissional__profissao'
        ]

    def filter_periodo(self, queryset, name, value):
        """
        Filtrar por períodos específicos
        """
        from django.utils import timezone
        from datetime import timedelta
        
        hoje = timezone.now()
        
        if value == 'futuras':
            return queryset.filter(data_hora__gt=hoje)
        elif value == 'passadas':
            return queryset.filter(data_hora__lt=hoje)
        elif value == 'hoje':
            return queryset.filter(data_hora__date=hoje.date())
        elif value == 'esta_semana':
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            fim_semana = inicio_semana + timedelta(days=6)
            return queryset.filter(
                data_hora__date__gte=inicio_semana.date(),
                data_hora__date__lte=fim_semana.date()
            )
        elif value == 'este_mes':
            return queryset.filter(
                data_hora__year=hoje.year,
                data_hora__month=hoje.month
            )
        
        return queryset