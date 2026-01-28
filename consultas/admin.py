"""
Admin configuration for Consultas app
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Consulta


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    """Admin configuration for Consulta model"""
    
    list_display = (
        'nome_paciente', 'profissional_nome', 'data_hora_formatada',
        'tipo_consulta', 'status_colored', 'valor_consulta', 'pago', 'is_active'
    )
    list_filter = (
        'status', 'tipo_consulta', 'profissional__profissao',
        'profissional__endereco__cidade', 'pago', 'forma_pagamento',
        'is_active', 'data_hora', 'created_at'
    )
    search_fields = (
        'nome_paciente', 'telefone_paciente', 'email_paciente',
        'profissional__nome_social', 'motivo_consulta', 'observacoes'
    )
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'duracao_real', 
        'tempo_restante', 'pode_cancelar', 'pode_remarcar',
        'get_status_display_color'
    )
    
    fieldsets = (
        ('Informações da Consulta', {
            'fields': ('profissional', 'data_hora', 'duracao_estimada', 'tipo_consulta')
        }),
        ('Paciente', {
            'fields': ('nome_paciente', 'telefone_paciente', 'email_paciente')
        }),
        ('Detalhes', {
            'fields': ('motivo_consulta', 'observacoes', 'observacoes_internas')
        }),
        ('Status e Controle', {
            'fields': ('status', 'data_hora_fim')
        }),
        ('Financeiro', {
            'fields': ('valor_consulta', 'forma_pagamento', 'pago')
        }),
        ('Cancelamento/Remarcação', {
            'fields': (
                'motivo_cancelamento', 'cancelado_por', 'data_cancelamento',
                'consulta_origem'
            ),
            'classes': ('collapse',)
        }),
        ('Status do Sistema', {
            'fields': ('is_active',)
        }),
        ('Informações do Sistema', {
            'fields': (
                'id', 'created_at', 'updated_at', 'duracao_real',
                'tempo_restante', 'pode_cancelar', 'pode_remarcar'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirmar_consultas', 'cancelar_consultas', 'marcar_como_pago']
    
    def profissional_nome(self, obj):
        """Display professional name"""
        return obj.profissional.nome_social if obj.profissional else ''
    profissional_nome.short_description = 'Profissional'
    profissional_nome.admin_order_field = 'profissional__nome_social'
    
    def data_hora_formatada(self, obj):
        """Display formatted date and time"""
        if obj.data_hora:
            return obj.data_hora.strftime('%d/%m/%Y %H:%M')
        return ''
    data_hora_formatada.short_description = 'Data e Hora'
    data_hora_formatada.admin_order_field = 'data_hora'
    
    def status_colored(self, obj):
        """Display colored status"""
        color = obj.get_status_display_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    def duracao_real(self, obj):
        """Display actual duration"""
        if obj.duracao_real:
            return f"{obj.duracao_real} min"
        return ''
    duracao_real.short_description = 'Duração Real'
    
    def tempo_restante(self, obj):
        """Display remaining time"""
        if obj.tempo_restante > 0:
            horas = obj.tempo_restante // 60
            minutos = obj.tempo_restante % 60
            if horas > 0:
                return f"{horas}h {minutos}min"
            return f"{minutos}min"
        elif obj.data_hora <= timezone.now():
            return "Expirada"
        return ''
    tempo_restante.short_description = 'Tempo Restante'
    
    def pode_cancelar(self, obj):
        """Display if can cancel"""
        return "✅" if obj.pode_cancelar else "❌"
    pode_cancelar.short_description = 'Pode Cancelar'
    
    def pode_remarcar(self, obj):
        """Display if can reschedule"""
        return "✅" if obj.pode_remarcar else "❌"
    pode_remarcar.short_description = 'Pode Remarcar'
    
    # Actions
    def confirmar_consultas(self, request, queryset):
        """Bulk confirm appointments"""
        count = 0
        for consulta in queryset:
            try:
                if consulta.status == 'AGENDADA':
                    consulta.confirmar()
                    count += 1
            except Exception:
                pass
        
        self.message_user(request, f'{count} consultas confirmadas com sucesso.')
    confirmar_consultas.short_description = "Confirmar consultas selecionadas"
    
    def cancelar_consultas(self, request, queryset):
        """Bulk cancel appointments"""
        count = 0
        for consulta in queryset:
            try:
                if consulta.pode_cancelar:
                    consulta.cancelar("Cancelado em massa pelo admin", "SISTEMA")
                    count += 1
            except Exception:
                pass
        
        self.message_user(request, f'{count} consultas canceladas com sucesso.')
    cancelar_consultas.short_description = "Cancelar consultas selecionadas"
    
    def marcar_como_pago(self, request, queryset):
        """Mark appointments as paid"""
        count = queryset.filter(pago=False).update(pago=True)
        self.message_user(request, f'{count} consultas marcadas como pagas.')
    marcar_como_pago.short_description = "Marcar como pago"
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'profissional', 'profissional__endereco', 'consulta_origem'
        )