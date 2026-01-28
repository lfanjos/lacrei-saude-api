"""
Views para Consultas - Lacrei Saúde API
=======================================
"""

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, filters
from lacrei_saude.security import (
    QuerySecurityManager, sanitize_search_query, 
    validate_integer_field, SecurePagination
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Consulta
from .serializers import (
    ConsultaSerializer, ConsultaListSerializer, ConsultaCreateSerializer,
    ConsultaUpdateSerializer, ConsultaActionSerializer, ConsultaPacienteSerializer
)
from .filters import ConsultaFilter
from profissionais.models import Profissional
from lacrei_saude.pagination import StandardResultsSetPagination
from authentication.permissions import (
    IsOwnerProfissionalOrAdmin, IsOwnerOrAdmin, ReadOnlyOrOwner
)


class ConsultaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de Consultas
    """
    queryset = Consulta.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, IsOwnerProfissionalOrAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Usar filtro personalizado
    filterset_class = ConsultaFilter
    
    # Campos para busca
    search_fields = [
        'nome_paciente', 'telefone_paciente', 'email_paciente',
        'profissional__nome_social', 'motivo_consulta'
    ]
    
    # Campos para ordenação
    ordering_fields = [
        'data_hora', 'status', 'created_at', 'valor_consulta',
        'nome_paciente', 'profissional__nome_social', 'tipo_consulta'
    ]
    ordering = ['-data_hora']

    def get_serializer_class(self):
        """
        Retorna serializer apropriado baseado na ação
        """
        if self.action == 'list':
            return ConsultaListSerializer
        elif self.action == 'create':
            return ConsultaCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ConsultaUpdateSerializer
        elif self.action in ['confirmar', 'iniciar', 'finalizar', 'cancelar', 'remarcar']:
            return ConsultaActionSerializer
        elif self.action == 'paciente_view':
            return ConsultaPacienteSerializer
        return ConsultaSerializer

    def get_queryset(self):
        """
        Filtrar queryset baseado em parâmetros opcionais
        """
        queryset = super().get_queryset()
        
        # Filtro por profissional
        profissional_id = self.request.query_params.get('profissional_id', None)
        if profissional_id:
            queryset = queryset.filter(profissional__id=profissional_id)
        
        # Filtro por data
        data_inicio = self.request.query_params.get('data_inicio', None)
        data_fim = self.request.query_params.get('data_fim', None)
        
        if data_inicio:
            try:
                queryset = queryset.filter(data_hora__date__gte=data_inicio)
            except ValueError:
                pass
        
        if data_fim:
            try:
                queryset = queryset.filter(data_hora__date__lte=data_fim)
            except ValueError:
                pass
        
        # Filtro por status múltiplo
        status_list = self.request.query_params.get('status_list', None)
        if status_list:
            status_values = status_list.split(',')
            queryset = queryset.filter(status__in=status_values)
        
        # Filtro por consultas futuras/passadas
        periodo = self.request.query_params.get('periodo', None)
        if periodo == 'futuras':
            queryset = queryset.filter(data_hora__gt=timezone.now())
        elif periodo == 'passadas':
            queryset = queryset.filter(data_hora__lt=timezone.now())
        elif periodo == 'hoje':
            hoje = timezone.now().date()
            queryset = queryset.filter(data_hora__date=hoje)
        
        return queryset

    def perform_create(self, serializer):
        """
        Personalizar criação da consulta
        """
        consulta = serializer.save()
        
        # Log da criação
        print(f"Nova consulta criada: {consulta.id} - {consulta.nome_paciente}")

    def perform_update(self, serializer):
        """
        Personalizar atualização da consulta
        """
        consulta = serializer.save()
        
        # Log da atualização
        print(f"Consulta atualizada: {consulta.id} - Status: {consulta.status}")

    def perform_destroy(self, instance):
        """
        Soft delete da consulta
        """
        # Verificar se pode ser excluída
        if instance.status in ['EM_ANDAMENTO', 'CONCLUIDA']:
            return Response(
                {'error': 'Consulta em andamento ou concluída não pode ser excluída'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """
        Confirmar consulta agendada
        """
        consulta = self.get_object()
        
        try:
            consulta.confirmar()
            return Response(
                {'message': 'Consulta confirmada com sucesso'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        """
        Iniciar consulta confirmada
        """
        consulta = self.get_object()
        
        try:
            consulta.iniciar()
            return Response(
                {'message': 'Consulta iniciada com sucesso'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        """
        Finalizar consulta em andamento
        """
        consulta = self.get_object()
        observacoes_internas = request.data.get('observacoes_internas', '')
        
        try:
            consulta.finalizar(observacoes_internas)
            return Response(
                {'message': 'Consulta finalizada com sucesso'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar consulta
        """
        consulta = self.get_object()
        serializer = ConsultaActionSerializer(data=request.data)
        
        if serializer.is_valid():
            motivo = serializer.validated_data['motivo']
            cancelado_por = serializer.validated_data.get('cancelado_por', 'SISTEMA')
            
            try:
                consulta.cancelar(motivo, cancelado_por)
                return Response(
                    {'message': 'Consulta cancelada com sucesso'},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remarcar(self, request, pk=None):
        """
        Remarcar consulta para nova data/hora
        """
        consulta = self.get_object()
        serializer = ConsultaActionSerializer(data=request.data)
        
        if serializer.is_valid():
            nova_data_hora = serializer.validated_data['nova_data_hora']
            motivo = serializer.validated_data.get('motivo', '')
            
            try:
                nova_consulta = consulta.remarcar(nova_data_hora, motivo)
                response_serializer = ConsultaSerializer(nova_consulta)
                return Response({
                    'message': 'Consulta remarcada com sucesso',
                    'nova_consulta': response_serializer.data
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def agenda_dia(self, request):
        """
        Listar consultas do dia para todos os profissionais
        """
        data = request.query_params.get('data', None)
        if not data:
            data = timezone.now().date().isoformat()
        
        try:
            from datetime import datetime
            data_consulta = datetime.strptime(data, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de data inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        consultas = self.get_queryset().filter(
            data_hora__date=data_consulta
        ).order_by('data_hora', 'profissional__nome_social')
        
        # Agrupar por profissional
        agenda = {}
        for consulta in consultas:
            prof_nome = consulta.profissional.nome_social
            if prof_nome not in agenda:
                agenda[prof_nome] = []
            
            agenda[prof_nome].append({
                'id': consulta.id,
                'horario': consulta.data_hora.strftime('%H:%M'),
                'paciente': consulta.nome_paciente,
                'status': consulta.get_status_display(),
                'tipo': consulta.get_tipo_consulta_display()
            })
        
        return Response({
            'data': data,
            'agenda': agenda,
            'total_consultas': consultas.count()
        })

    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """
        Estatísticas das consultas
        """
        queryset = self.get_queryset()
        hoje = timezone.now()
        
        # Filtros por período
        mes_atual = queryset.filter(
            data_hora__year=hoje.year,
            data_hora__month=hoje.month
        )
        
        stats = {
            'total_consultas': queryset.count(),
            'consultas_mes_atual': mes_atual.count(),
            'por_status': {},
            'por_tipo': {},
            'receita_total_mes': 0,
            'consultas_hoje': queryset.filter(data_hora__date=hoje.date()).count()
        }
        
        # Estatísticas por status
        from django.db.models import Count, Sum
        status_stats = queryset.values('status').annotate(total=Count('id'))
        for stat in status_stats:
            status_display = dict(Consulta._meta.get_field('status').choices).get(
                stat['status'], stat['status']
            )
            stats['por_status'][status_display] = stat['total']
        
        # Estatísticas por tipo
        tipo_stats = queryset.values('tipo_consulta').annotate(total=Count('id'))
        for stat in tipo_stats:
            tipo_display = dict(Consulta._meta.get_field('tipo_consulta').choices).get(
                stat['tipo_consulta'], stat['tipo_consulta']
            )
            stats['por_tipo'][tipo_display] = stat['total']
        
        # Receita do mês
        receita = mes_atual.filter(
            pago=True,
            valor_consulta__isnull=False
        ).aggregate(total=Sum('valor_consulta'))['total']
        stats['receita_total_mes'] = receita or 0
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def por_profissional(self, request, profissional_id=None):
        """
        Buscar consultas por ID do profissional
        """
        if not profissional_id:
            profissional_id = request.query_params.get('profissional_id', None)
        
        if not profissional_id:
            return Response(
                {'error': 'ID do profissional é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            profissional = Profissional.objects.get(id=profissional_id, is_active=True)
        except Profissional.DoesNotExist:
            return Response(
                {'error': 'Profissional não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        consultas = self.get_queryset().filter(profissional=profissional)
        
        # Aplicar filtros de data se fornecidos
        data_inicio = request.query_params.get('data_inicio', None)
        data_fim = request.query_params.get('data_fim', None)
        
        if data_inicio:
            consultas = consultas.filter(data_hora__date__gte=data_inicio)
        if data_fim:
            consultas = consultas.filter(data_hora__date__lte=data_fim)
        
        # Paginação
        page = self.paginate_queryset(consultas)
        if page is not None:
            serializer = ConsultaListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ConsultaListSerializer(consultas, many=True)
        return Response({
            'profissional': {
                'id': profissional.id,
                'nome': profissional.nome_social,
                'profissao': profissional.get_profissao_display()
            },
            'consultas': serializer.data,
            'total': consultas.count()
        })

    @action(detail=True, methods=['get'])
    def paciente_view(self, request, pk=None):
        """
        Visualização da consulta para o paciente (dados limitados)
        """
        consulta = self.get_object()
        serializer = ConsultaPacienteSerializer(consulta)
        return Response(serializer.data)
