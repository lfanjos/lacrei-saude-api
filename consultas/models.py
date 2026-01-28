"""
Modelos para Consultas Médicas - Lacrei Saúde API
==================================================
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from lacrei_saude.models import BaseModelWithManager
from profissionais.models import Profissional


class Consulta(BaseModelWithManager):
    """
    Modelo para Consultas Médicas
    """

    STATUS_CHOICES = [
        ("AGENDADA", "Agendada"),
        ("CONFIRMADA", "Confirmada"),
        ("EM_ANDAMENTO", "Em Andamento"),
        ("CONCLUIDA", "Concluída"),
        ("CANCELADA", "Cancelada"),
        ("NAO_COMPARECEU", "Não Compareceu"),
        ("REMARCADA", "Remarcada"),
    ]

    TIPO_CONSULTA_CHOICES = [
        ("PRESENCIAL", "Presencial"),
        ("TELECONSULTA", "Teleconsulta"),
        ("RETORNO", "Retorno"),
        ("PRIMEIRA_CONSULTA", "Primeira Consulta"),
        ("URGENCIA", "Urgência"),
    ]

    # Relacionamentos
    profissional = models.ForeignKey(
        Profissional, on_delete=models.PROTECT, related_name="consultas", help_text="Profissional responsável pela consulta"
    )

    # Data e hora
    data_hora = models.DateTimeField(help_text="Data e hora agendada para a consulta")
    duracao_estimada = models.PositiveIntegerField(default=60, help_text="Duração estimada em minutos")
    data_hora_fim = models.DateTimeField(null=True, blank=True, help_text="Data e hora de término (calculada ou real)")

    # Informações da consulta
    tipo_consulta = models.CharField(
        max_length=20, choices=TIPO_CONSULTA_CHOICES, default="PRIMEIRA_CONSULTA", help_text="Tipo da consulta"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AGENDADA", help_text="Status atual da consulta")

    # Dados do paciente (simplificado - em um sistema real seria uma ForeignKey)
    nome_paciente = models.CharField(max_length=150, help_text="Nome do paciente")
    telefone_paciente = models.CharField(max_length=20, help_text="Telefone do paciente")
    email_paciente = models.EmailField(blank=True, help_text="Email do paciente (opcional)")

    # Observações e detalhes
    motivo_consulta = models.TextField(max_length=500, blank=True, help_text="Motivo principal da consulta")
    observacoes = models.TextField(blank=True, max_length=1000, help_text="Observações adicionais")
    observacoes_internas = models.TextField(
        blank=True, max_length=1000, help_text="Observações internas (não visíveis ao paciente)"
    )

    # Informações financeiras
    valor_consulta = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Valor cobrado pela consulta"
    )
    forma_pagamento = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("DINHEIRO", "Dinheiro"),
            ("CARTAO_DEBITO", "Cartão de Débito"),
            ("CARTAO_CREDITO", "Cartão de Crédito"),
            ("PIX", "PIX"),
            ("CONVENIO", "Convênio"),
            ("TRANSFERENCIA", "Transferência"),
        ],
        help_text="Forma de pagamento",
    )
    pago = models.BooleanField(default=False, help_text="Consulta foi paga")

    # Histórico de alterações
    motivo_cancelamento = models.TextField(blank=True, max_length=500, help_text="Motivo do cancelamento (se aplicável)")
    cancelado_por = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ("PACIENTE", "Paciente"),
            ("PROFISSIONAL", "Profissional"),
            ("SISTEMA", "Sistema"),
        ],
        help_text="Quem cancelou a consulta",
    )
    data_cancelamento = models.DateTimeField(null=True, blank=True, help_text="Data e hora do cancelamento")

    # Consulta de origem (para remarques)
    consulta_origem = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultas_remarcadas",
        help_text="Consulta original (para remarques)",
    )

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        indexes = [
            models.Index(fields=["data_hora"]),
            models.Index(fields=["profissional", "data_hora"]),
            models.Index(fields=["status"]),
            models.Index(fields=["nome_paciente"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(duracao_estimada__gt=0), name="duracao_positiva"),
            models.CheckConstraint(
                condition=models.Q(valor_consulta__gte=0) | models.Q(valor_consulta__isnull=True), name="valor_nao_negativo"
            ),
        ]

    def __str__(self):
        return f"{self.nome_paciente} - {self.profissional.nome_social} ({self.data_hora.strftime('%d/%m/%Y %H:%M')})"

    def clean(self):
        """Validações customizadas"""
        super().clean()

        # Validar data no futuro para novas consultas
        if not self.pk and self.data_hora and self.data_hora <= timezone.now():
            raise ValidationError("Data da consulta deve ser no futuro")

        # Calcular data_hora_fim se não fornecida
        if self.data_hora and not self.data_hora_fim:
            self.data_hora_fim = self.data_hora + timezone.timedelta(minutes=self.duracao_estimada)

        # Validações de cancelamento
        if self.status == "CANCELADA":
            if not self.motivo_cancelamento:
                raise ValidationError("Motivo do cancelamento é obrigatório")
            if not self.data_cancelamento:
                self.data_cancelamento = timezone.now()

        # Validar valor da consulta
        if not self.valor_consulta and self.profissional.valor_consulta:
            self.valor_consulta = self.profissional.valor_consulta

    def save(self, *args, **kwargs):
        """Override save para validações adicionais"""
        self.full_clean()
        super().save(*args, **kwargs)

    # Métodos de negócio
    def confirmar(self):
        """Confirma a consulta"""
        if self.status != "AGENDADA":
            raise ValidationError("Apenas consultas agendadas podem ser confirmadas")
        self.status = "CONFIRMADA"
        self.save(update_fields=["status", "updated_at"])

    def iniciar(self):
        """Inicia a consulta"""
        if self.status not in ["AGENDADA", "CONFIRMADA"]:
            raise ValidationError("Consulta deve estar agendada ou confirmada para iniciar")
        self.status = "EM_ANDAMENTO"
        self.save(update_fields=["status", "updated_at"])

    def finalizar(self):
        """Finaliza a consulta"""
        if self.status != "EM_ANDAMENTO":
            raise ValidationError("Apenas consultas em andamento podem ser finalizadas")
        self.status = "CONCLUIDA"
        self.data_hora_fim = timezone.now()
        self.save(update_fields=["status", "data_hora_fim", "updated_at"])

    def cancelar(self, motivo, cancelado_por="SISTEMA"):
        """Cancela a consulta"""
        if self.status in ["CONCLUIDA", "CANCELADA"]:
            raise ValidationError("Consulta já finalizada não pode ser cancelada")

        self.status = "CANCELADA"
        self.motivo_cancelamento = motivo
        self.cancelado_por = cancelado_por
        self.data_cancelamento = timezone.now()
        self.save(update_fields=["status", "motivo_cancelamento", "cancelado_por", "data_cancelamento", "updated_at"])

    def remarcar(self, nova_data_hora, motivo=""):
        """Remarca a consulta criando uma nova"""
        if self.status in ["CONCLUIDA", "CANCELADA"]:
            raise ValidationError("Consulta finalizada não pode ser remarcada")

        # Marcar consulta atual como remarcada
        self.status = "REMARCADA"
        self.save(update_fields=["status", "updated_at"])

        # Criar nova consulta
        nova_consulta = Consulta.objects.create(
            profissional=self.profissional,
            data_hora=nova_data_hora,
            duracao_estimada=self.duracao_estimada,
            tipo_consulta=self.tipo_consulta,
            nome_paciente=self.nome_paciente,
            telefone_paciente=self.telefone_paciente,
            email_paciente=self.email_paciente,
            motivo_consulta=self.motivo_consulta,
            valor_consulta=self.valor_consulta,
            observacoes=f"Remarcada. Motivo: {motivo}" if motivo else "Remarcada",
            consulta_origem=self,
        )

        return nova_consulta

    # Propriedades
    @property
    def duracao_real(self):
        """Retorna duração real da consulta em minutos"""
        if self.status == "CONCLUIDA" and self.data_hora_fim:
            delta = self.data_hora_fim - self.data_hora
            return int(delta.total_seconds() / 60)
        return None

    @property
    def tempo_restante(self):
        """Retorna tempo restante para a consulta em minutos"""
        if self.data_hora > timezone.now():
            delta = self.data_hora - timezone.now()
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def pode_cancelar(self):
        """Verifica se a consulta pode ser cancelada"""
        return self.status not in ["CONCLUIDA", "CANCELADA"]

    @property
    def pode_remarcar(self):
        """Verifica se a consulta pode ser remarcada"""
        return self.status not in ["CONCLUIDA", "CANCELADA"]

    def get_status_display_color(self):
        """Retorna cor para exibição do status"""
        colors = {
            "AGENDADA": "#2196F3",  # Azul
            "CONFIRMADA": "#4CAF50",  # Verde
            "EM_ANDAMENTO": "#FF9800",  # Laranja
            "CONCLUIDA": "#8BC34A",  # Verde claro
            "CANCELADA": "#F44336",  # Vermelho
            "NAO_COMPARECEU": "#9C27B0",  # Roxo
            "REMARCADA": "#607D8B",  # Azul acinzentado
        }
        return colors.get(self.status, "#000000")
