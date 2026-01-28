"""
Admin configuration for Profissionais app
"""

from django.contrib import admin
from .models import Endereco, Profissional


@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    """Admin configuration for Endereco model"""
    
    list_display = ('logradouro', 'numero', 'bairro', 'cidade', 'estado', 'cep', 'is_active')
    list_filter = ('estado', 'cidade', 'is_active', 'created_at')
    search_fields = ('logradouro', 'numero', 'bairro', 'cidade', 'cep')
    readonly_fields = ('id', 'created_at', 'updated_at', 'endereco_completo')
    
    fieldsets = (
        ('Endereço', {
            'fields': ('logradouro', 'numero', 'complemento', 'bairro')
        }),
        ('Localização', {
            'fields': ('cidade', 'estado', 'cep', 'referencia')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Informações do Sistema', {
            'fields': ('id', 'created_at', 'updated_at', 'endereco_completo'),
            'classes': ('collapse',)
        }),
    )
    
    def endereco_completo(self, obj):
        """Display formatted complete address"""
        return obj.endereco_completo if obj else ''
    endereco_completo.short_description = 'Endereço Completo'


@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    """Admin configuration for Profissional model"""
    
    list_display = (
        'nome_social', 'profissao', 'email', 'telefone', 
        'cidade_atendimento', 'aceita_convenio', 'is_active'
    )
    list_filter = (
        'profissao', 'aceita_convenio', 'endereco__cidade', 
        'endereco__estado', 'is_active', 'created_at'
    )
    search_fields = (
        'nome_social', 'nome_registro', 'email', 'telefone', 
        'registro_profissional', 'especialidade'
    )
    readonly_fields = ('id', 'created_at', 'updated_at', 'nome_completo', 'get_contato_formatado')
    
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome_social', 'nome_registro')
        }),
        ('Informações Profissionais', {
            'fields': ('profissao', 'registro_profissional', 'especialidade', 'biografia')
        }),
        ('Contato', {
            'fields': ('email', 'telefone', 'whatsapp')
        }),
        ('Endereço', {
            'fields': ('endereco',)
        }),
        ('Serviços', {
            'fields': ('aceita_convenio', 'valor_consulta')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Informações do Sistema', {
            'fields': ('id', 'created_at', 'updated_at', 'nome_completo', 'get_contato_formatado'),
            'classes': ('collapse',)
        }),
    )
    
    def cidade_atendimento(self, obj):
        """Display city of service"""
        return f"{obj.endereco.cidade}/{obj.endereco.estado}" if obj.endereco else ''
    cidade_atendimento.short_description = 'Cidade de Atendimento'
    cidade_atendimento.admin_order_field = 'endereco__cidade'
    
    def nome_completo(self, obj):
        """Display complete name"""
        return obj.nome_completo if obj else ''
    nome_completo.short_description = 'Nome Completo'
    
    def get_contato_formatado(self, obj):
        """Display formatted contact"""
        return obj.get_contato_formatado() if obj else ''
    get_contato_formatado.short_description = 'Contato Formatado'