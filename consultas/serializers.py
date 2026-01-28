"""
Serializers para Consultas - Lacrei Saúde API
==============================================
"""

from rest_framework import serializers

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils import timezone

from lacrei_saude.serializers import BaseModelSerializer, TimestampsMixin, ValidationMixin
from lacrei_saude.validators import sanitize_email, validate_money_amount, validate_name, validate_observation, validate_phone
from profissionais.models import Profissional
from profissionais.serializers import ProfissionalListSerializer

from .models import Consulta


class ConsultaSerializer(BaseModelSerializer, TimestampsMixin, ValidationMixin):
    """
    Serializer principal para o modelo Consulta
    """

    profissional_info = ProfissionalListSerializer(source="profissional", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    tipo_consulta_display = serializers.CharField(source="get_tipo_consulta_display", read_only=True)
    forma_pagamento_display = serializers.CharField(source="get_forma_pagamento_display", read_only=True)

    # Campos calculados
    duracao_real_minutos = serializers.ReadOnlyField(source="duracao_real")
    tempo_restante_minutos = serializers.ReadOnlyField(source="tempo_restante")
    pode_cancelar = serializers.ReadOnlyField()
    pode_remarcar = serializers.ReadOnlyField()

    # Formatação de data/hora
    data_hora_formatada = serializers.SerializerMethodField()
    data_hora_fim_formatada = serializers.SerializerMethodField()

    class Meta:
        model = Consulta
        fields = [
            "id",
            "profissional",
            "profissional_info",
            "data_hora",
            "data_hora_formatada",
            "duracao_estimada",
            "data_hora_fim",
            "data_hora_fim_formatada",
            "duracao_real_minutos",
            "tipo_consulta",
            "tipo_consulta_display",
            "status",
            "status_display",
            "nome_paciente",
            "telefone_paciente",
            "email_paciente",
            "motivo_consulta",
            "observacoes",
            "observacoes_internas",
            "valor_consulta",
            "forma_pagamento",
            "forma_pagamento_display",
            "pago",
            "motivo_cancelamento",
            "cancelado_por",
            "data_cancelamento",
            "consulta_origem",
            "tempo_restante_minutos",
            "pode_cancelar",
            "pode_remarcar",
            "created_at",
            "updated_at",
            "is_active",
        ]
        extra_kwargs = {
            "email_paciente": {"required": False, "allow_blank": True},
            "motivo_consulta": {"required": False, "allow_blank": True},
            "observacoes": {"required": False, "allow_blank": True},
            "observacoes_internas": {"required": False, "allow_blank": True},
            "valor_consulta": {"required": False, "allow_null": True},
            "forma_pagamento": {"required": False, "allow_blank": True},
            "motivo_cancelamento": {"required": False, "allow_blank": True},
            "cancelado_por": {"required": False, "allow_blank": True},
            "data_cancelamento": {"required": False, "allow_null": True},
            "data_hora_fim": {"required": False, "allow_null": True},
            "consulta_origem": {"required": False, "allow_null": True},
        }

    def get_data_hora_formatada(self, obj):
        """Retorna data/hora formatada"""
        if obj.data_hora:
            return obj.data_hora.strftime("%d/%m/%Y às %H:%M")
        return None

    def get_data_hora_fim_formatada(self, obj):
        """Retorna data/hora de fim formatada"""
        if obj.data_hora_fim:
            return obj.data_hora_fim.strftime("%d/%m/%Y às %H:%M")
        return None

    def validate_profissional(self, value):
        """Validar se o profissional está ativo"""
        if not value.is_active:
            raise serializers.ValidationError("Não é possível agendar consulta com profissional inativo")
        return value

    def validate_data_hora(self, value):
        """Validar data/hora da consulta"""
        if value <= timezone.now():
            raise serializers.ValidationError("Data e hora da consulta devem ser no futuro")
        return value

    def validate_telefone_paciente(self, value):
        """Validar telefone do paciente"""
        return super().validate_telefone(value)

    def validate_valor_consulta(self, value):
        """Validar valor da consulta"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Valor da consulta não pode ser negativo")
        return value

    def validate_duracao_estimada(self, value):
        """Validar duração estimada"""
        if value <= 0:
            raise serializers.ValidationError("Duração estimada deve ser maior que zero")
        if value > 480:  # 8 horas
            raise serializers.ValidationError("Duração estimada não pode exceder 8 horas (480 minutos)")
        return value

    def validate(self, data):
        """Validações gerais da consulta"""
        # Verificar conflito de horário para o profissional
        if "profissional" in data and "data_hora" in data:
            profissional = data["profissional"]
            data_hora = data["data_hora"]
            duracao = data.get("duracao_estimada", 60)

            data_hora_fim = data_hora + timezone.timedelta(minutes=duracao)

            # Query para verificar conflitos (excluindo a própria consulta se for update)
            conflitos = Consulta.objects.filter(
                profissional=profissional, is_active=True, status__in=["AGENDADA", "CONFIRMADA", "EM_ANDAMENTO"]
            ).exclude(
                # Excluir consultas que terminam antes ou começam depois
                models.Q(data_hora_fim__lte=data_hora)
                | models.Q(data_hora__gte=data_hora_fim)
            )

            # Excluir a própria consulta em caso de update
            if self.instance:
                conflitos = conflitos.exclude(pk=self.instance.pk)

            if conflitos.exists():
                raise serializers.ValidationError(
                    {"data_hora": "Já existe uma consulta agendada para este profissional no horário solicitado"}
                )

        # Se valor não informado, usar valor padrão do profissional
        if "profissional" in data and not data.get("valor_consulta"):
            profissional = data["profissional"]
            if profissional.valor_consulta:
                data["valor_consulta"] = profissional.valor_consulta

        return data


class ConsultaListSerializer(BaseModelSerializer):
    """
    Serializer simplificado para listagem de consultas
    """

    profissional_nome = serializers.CharField(source="profissional.nome_social", read_only=True)
    profissional_profissao = serializers.CharField(source="profissional.get_profissao_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    data_hora_formatada = serializers.SerializerMethodField()

    class Meta:
        model = Consulta
        fields = [
            "id",
            "profissional_nome",
            "profissional_profissao",
            "data_hora",
            "data_hora_formatada",
            "tipo_consulta",
            "status",
            "status_display",
            "nome_paciente",
            "valor_consulta",
            "pago",
        ]

    def get_data_hora_formatada(self, obj):
        """Retorna data/hora formatada"""
        if obj.data_hora:
            return obj.data_hora.strftime("%d/%m/%Y às %H:%M")
        return None


class ConsultaCreateSerializer(ConsultaSerializer):
    """
    Serializer para criação de consultas
    """

    class Meta(ConsultaSerializer.Meta):
        fields = [
            "profissional",
            "data_hora",
            "duracao_estimada",
            "tipo_consulta",
            "nome_paciente",
            "telefone_paciente",
            "email_paciente",
            "motivo_consulta",
            "observacoes",
            "valor_consulta",
        ]
        extra_kwargs = {
            "profissional": {"required": True},
            "data_hora": {"required": True},
            "nome_paciente": {"required": True},
            "telefone_paciente": {"required": True},
        }


class ConsultaUpdateSerializer(ConsultaSerializer):
    """
    Serializer para atualização de consultas
    Permite apenas alguns campos específicos
    """

    class Meta(ConsultaSerializer.Meta):
        fields = [
            "data_hora",
            "duracao_estimada",
            "telefone_paciente",
            "email_paciente",
            "motivo_consulta",
            "observacoes",
            "valor_consulta",
            "forma_pagamento",
        ]

    def validate(self, data):
        """Validações específicas para update"""
        # Não permitir alteração se consulta já foi realizada ou cancelada
        if self.instance and self.instance.status in ["CONCLUIDA", "CANCELADA"]:
            raise serializers.ValidationError("Não é possível alterar consulta finalizada")

        return super().validate(data)


class ConsultaActionSerializer(serializers.Serializer):
    """
    Serializer para ações específicas das consultas
    """

    action = serializers.ChoiceField(
        choices=[
            ("confirmar", "Confirmar"),
            ("iniciar", "Iniciar"),
            ("finalizar", "Finalizar"),
            ("cancelar", "Cancelar"),
            ("remarcar", "Remarcar"),
        ]
    )
    motivo = serializers.CharField(max_length=500, required=False, allow_blank=True)
    nova_data_hora = serializers.DateTimeField(required=False)
    cancelado_por = serializers.ChoiceField(
        choices=[("PACIENTE", "Paciente"), ("PROFISSIONAL", "Profissional"), ("SISTEMA", "Sistema")], required=False
    )

    def validate(self, data):
        """Validações específicas por ação"""
        action = data.get("action")

        if action == "cancelar":
            if not data.get("motivo"):
                raise serializers.ValidationError({"motivo": "Motivo é obrigatório para cancelamento"})

        if action == "remarcar":
            if not data.get("nova_data_hora"):
                raise serializers.ValidationError({"nova_data_hora": "Nova data e hora são obrigatórias para remarcação"})

            # Validar se nova data é no futuro
            if data["nova_data_hora"] <= timezone.now():
                raise serializers.ValidationError({"nova_data_hora": "Nova data deve ser no futuro"})

        return data


class ConsultaPacienteSerializer(BaseModelSerializer):
    """
    Serializer para consultas do ponto de vista do paciente
    (informações limitadas por privacidade)
    """

    profissional_nome = serializers.CharField(source="profissional.nome_social", read_only=True)
    profissional_profissao = serializers.CharField(source="profissional.get_profissao_display", read_only=True)
    endereco_atendimento = serializers.CharField(source="profissional.endereco.endereco_completo", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    data_hora_formatada = serializers.SerializerMethodField()

    class Meta:
        model = Consulta
        fields = [
            "id",
            "profissional_nome",
            "profissional_profissao",
            "endereco_atendimento",
            "data_hora",
            "data_hora_formatada",
            "duracao_estimada",
            "tipo_consulta",
            "status",
            "status_display",
            "motivo_consulta",
            "observacoes",
            "valor_consulta",
            "pago",
        ]

    def get_data_hora_formatada(self, obj):
        """Retorna data/hora formatada"""
        if obj.data_hora:
            return obj.data_hora.strftime("%d/%m/%Y às %H:%M")
        return None
