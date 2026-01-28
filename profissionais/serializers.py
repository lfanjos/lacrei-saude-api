"""
Serializers para Profissionais - Lacrei Saúde API
==================================================
"""

from rest_framework import serializers
from django.core.validators import EmailValidator
from .models import Endereco, Profissional
from lacrei_saude.serializers import (
    BaseModelSerializer, TimestampsMixin, ValidationMixin
)
from lacrei_saude.validators import (
    validate_cpf, validate_phone, validate_cep, validate_crm,
    validate_name, sanitize_email, validate_money_amount,
    validate_observation
)


class EnderecoSerializer(BaseModelSerializer, TimestampsMixin, ValidationMixin):
    """
    Serializer para o modelo Endereco
    """
    endereco_completo = serializers.ReadOnlyField()
    
    class Meta:
        model = Endereco
        fields = [
            'id', 'logradouro', 'numero', 'complemento', 'bairro',
            'cidade', 'estado', 'cep', 'referencia', 'endereco_completo',
            'created_at', 'updated_at', 'is_active'
        ]
        extra_kwargs = {
            'complemento': {'required': False, 'allow_blank': True},
            'referencia': {'required': False, 'allow_blank': True},
        }

    def validate_cep(self, value):
        """Validação específica para CEP"""
        if value:
            value = validate_cep(value)
            # Normalizar CEP para formato XXXXX-XXX
            digits = ''.join(filter(str.isdigit, value))
            if len(digits) == 8:
                value = f"{digits[:5]}-{digits[5:]}"
        
        return value
    
    def validate_logradouro(self, value):
        """Validação do logradouro"""
        if value:
            value = validate_name(value)
        return value
    
    def validate_bairro(self, value):
        """Validação do bairro"""
        if value:
            value = validate_name(value)
        return value
    
    def validate_cidade(self, value):
        """Validação da cidade"""
        if value:
            value = validate_name(value)
        return value
    
    def validate_complemento(self, value):
        """Validação do complemento"""
        if value:
            value = validate_observation(value)
        return value

    def validate(self, data):
        """Validações gerais do endereço"""
        # Validar se o estado existe
        estados_validos = [choice[0] for choice in Endereco._meta.get_field('estado').choices]
        if data.get('estado') and data['estado'] not in estados_validos:
            raise serializers.ValidationError({
                'estado': 'Estado inválido'
            })
        
        return data


class EnderecoListSerializer(EnderecoSerializer):
    """
    Serializer simplificado para listagem de endereços
    """
    class Meta(EnderecoSerializer.Meta):
        fields = [
            'id', 'logradouro', 'numero', 'bairro', 'cidade', 
            'estado', 'cep', 'endereco_completo'
        ]


class ProfissionalSerializer(BaseModelSerializer, TimestampsMixin, ValidationMixin):
    """
    Serializer principal para o modelo Profissional
    """
    endereco = EnderecoSerializer()
    nome_completo = serializers.ReadOnlyField()
    contato_formatado = serializers.SerializerMethodField()
    profissao_display = serializers.CharField(source='get_profissao_display', read_only=True)
    
    class Meta:
        model = Profissional
        fields = [
            'id', 'nome_social', 'nome_registro', 'nome_completo',
            'profissao', 'profissao_display', 'registro_profissional', 'especialidade',
            'email', 'telefone', 'whatsapp', 'contato_formatado',
            'endereco', 'biografia', 'aceita_convenio', 'valor_consulta',
            'created_at', 'updated_at', 'is_active'
        ]
        extra_kwargs = {
            'nome_registro': {'required': False, 'allow_blank': True},
            'registro_profissional': {'required': False, 'allow_blank': True},
            'especialidade': {'required': False, 'allow_blank': True},
            'whatsapp': {'required': False, 'allow_blank': True},
            'biografia': {'required': False, 'allow_blank': True},
            'valor_consulta': {'required': False, 'allow_null': True},
            'email': {'validators': [EmailValidator()]},
        }

    def get_contato_formatado(self, obj):
        """Retorna contato formatado"""
        return obj.get_contato_formatado()
    
    def validate_nome_social(self, value):
        """Validação do nome social"""
        return validate_name(value)
    
    def validate_nome_registro(self, value):
        """Validação do nome de registro"""
        if value:
            return validate_name(value)
        return value
    
    
    def validate_telefone(self, value):
        """Validação do telefone"""
        if value:
            return validate_phone(value)
        return value
    
    def validate_whatsapp(self, value):
        """Validação do WhatsApp"""
        if value:
            return validate_phone(value)
        return value
    
    def validate_registro_profissional(self, value):
        """Validação do registro profissional"""
        if value and hasattr(self, 'initial_data'):
            profissao = self.initial_data.get('profissao')
            if profissao in ['MEDICO', 'ENFERMEIRO', 'PSICOLOGO']:
                # Para médicos, validar CRM
                if profissao == 'MEDICO':
                    endereco_data = self.initial_data.get('endereco', {})
                    uf = endereco_data.get('estado', '')
                    return validate_crm(value, uf)
                # Para outros profissionais, validação básica
                if not value.strip():
                    raise serializers.ValidationError("Registro profissional é obrigatório")
        return value
    
    def validate_valor_consulta(self, value):
        """Validação do valor da consulta"""
        if value is not None:
            return validate_money_amount(value)
        return value
    
    def validate_biografia(self, value):
        """Validação da biografia"""
        if value:
            return validate_observation(value)
        return value
    
    def validate_especialidade(self, value):
        """Validação da especialidade"""
        if value:
            return validate_observation(value)
        return value

    def validate_email(self, value):
        """Validação de email único"""
        if value:
            value = sanitize_email(value)
            
            # Verificar se email já existe (excluindo o próprio registro na edição)
            queryset = Profissional.objects.filter(email=value, is_active=True)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    "Já existe um profissional ativo com este email"
                )
        
        return value

    def validate_telefone(self, value):
        """Validação específica para telefone"""
        return super().validate_telefone(value)

    def validate_whatsapp(self, value):
        """Validação específica para WhatsApp"""
        if value:
            return self.validate_telefone(value)
        return value

    def validate_valor_consulta(self, value):
        """Validação para valor da consulta"""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Valor da consulta não pode ser negativo"
            )
        return value

    def create(self, validated_data):
        """Criar profissional com endereço aninhado"""
        endereco_data = validated_data.pop('endereco')
        endereco = Endereco.objects.create(**endereco_data)
        profissional = Profissional.objects.create(endereco=endereco, **validated_data)
        return profissional

    def update(self, instance, validated_data):
        """Atualizar profissional com endereço aninhado"""
        endereco_data = validated_data.pop('endereco', None)
        
        # Atualizar dados do profissional
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Atualizar dados do endereço se fornecidos
        if endereco_data:
            endereco_serializer = EnderecoSerializer(
                instance.endereco, 
                data=endereco_data, 
                partial=True
            )
            if endereco_serializer.is_valid(raise_exception=True):
                endereco_serializer.save()
        
        instance.save()
        return instance


class ProfissionalListSerializer(BaseModelSerializer):
    """
    Serializer simplificado para listagem de profissionais
    """
    profissao_display = serializers.CharField(source='get_profissao_display', read_only=True)
    cidade_atendimento = serializers.SerializerMethodField()
    
    class Meta:
        model = Profissional
        fields = [
            'id', 'nome_social', 'profissao', 'profissao_display',
            'especialidade', 'email', 'telefone', 'cidade_atendimento',
            'aceita_convenio', 'valor_consulta'
        ]

    def get_cidade_atendimento(self, obj):
        """Retorna cidade de atendimento"""
        if obj.endereco:
            return f"{obj.endereco.cidade}/{obj.endereco.estado}"
        return None


class ProfissionalCreateSerializer(ProfissionalSerializer):
    """
    Serializer para criação de profissionais (campos obrigatórios)
    """
    class Meta(ProfissionalSerializer.Meta):
        extra_kwargs = {
            **ProfissionalSerializer.Meta.extra_kwargs,
            'endereco': {'required': True},
            'nome_social': {'required': True},
            'profissao': {'required': True},
            'email': {'required': True},
            'telefone': {'required': True},
        }


class ProfissionalDetailSerializer(ProfissionalSerializer):
    """
    Serializer detalhado para visualização de profissional
    Inclui informações estatísticas e relacionadas
    """
    total_consultas = serializers.SerializerMethodField()
    consultas_mes_atual = serializers.SerializerMethodField()
    media_avaliacao = serializers.SerializerMethodField()

    class Meta(ProfissionalSerializer.Meta):
        fields = ProfissionalSerializer.Meta.fields + [
            'total_consultas', 'consultas_mes_atual', 'media_avaliacao'
        ]

    def get_total_consultas(self, obj):
        """Retorna total de consultas do profissional"""
        return obj.consultas.filter(is_active=True).count()

    def get_consultas_mes_atual(self, obj):
        """Retorna consultas do mês atual"""
        from django.utils import timezone
        import datetime
        
        hoje = timezone.now().date()
        primeiro_dia_mes = hoje.replace(day=1)
        
        return obj.consultas.filter(
            is_active=True,
            data_hora__date__gte=primeiro_dia_mes,
            data_hora__date__lte=hoje
        ).count()

    def get_media_avaliacao(self, obj):
        """Retorna média de avaliação (placeholder para futuro)"""
        # Placeholder para sistema de avaliações futuro
        return None