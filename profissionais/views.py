"""
Views para Profissionais - Lacrei Saúde API
===========================================
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Q

from authentication.permissions import IsOwnerOrAdmin, IsProfissionalOrAdmin, ReadOnlyOrOwner
from lacrei_saude.pagination import StandardResultsSetPagination

from .filters import ProfissionalFilter
from .models import Profissional
from .serializers import (
    ProfissionalCreateSerializer,
    ProfissionalDetailSerializer,
    ProfissionalListSerializer,
    ProfissionalSerializer,
)


class ProfissionalViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de Profissionais
    """

    queryset = Profissional.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated, ReadOnlyOrOwner]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Usar filtro personalizado
    filterset_class = ProfissionalFilter

    # Campos para busca
    search_fields = ["nome_social", "nome_registro", "especialidade", "endereco__cidade", "endereco__bairro"]

    # Campos para ordenação
    ordering_fields = [
        "nome_social",
        "profissao",
        "created_at",
        "valor_consulta",
        "especialidade",
        "endereco__cidade",
        "endereco__estado",
    ]
    ordering = ["nome_social"]

    def get_serializer_class(self):
        """
        Retorna serializer apropriado baseado na ação
        """
        if self.action == "list":
            return ProfissionalListSerializer
        elif self.action == "create":
            return ProfissionalCreateSerializer
        elif self.action == "retrieve":
            return ProfissionalDetailSerializer
        return ProfissionalSerializer

    def get_queryset(self):
        """
        Filtrar queryset baseado em parâmetros opcionais
        """
        queryset = super().get_queryset()

        # Filtro por disponibilidade para consulta
        disponivel = self.request.query_params.get("disponivel", None)
        if disponivel == "true":
            # Filtrar profissionais ativos que aceitam consultas
            queryset = queryset.filter(is_active=True)

        # Filtro por valor máximo de consulta
        valor_max = self.request.query_params.get("valor_max", None)
        if valor_max:
            try:
                valor_max = float(valor_max)
                queryset = queryset.filter(Q(valor_consulta__lte=valor_max) | Q(valor_consulta__isnull=True))
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        """
        Personalizar criação do profissional
        """
        # Adicionar informações do usuário se necessário
        serializer.save()

    def perform_update(self, serializer):
        """
        Personalizar atualização do profissional
        """
        serializer.save()

    def perform_destroy(self, instance):
        """
        Soft delete do profissional
        """
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=["get"])
    def consultas(self, request, pk=None):
        """
        Listar consultas do profissional
        """
        profissional = self.get_object()
        consultas = profissional.consultas.filter(is_active=True)

        # Filtros opcionais
        status_consulta = request.query_params.get("status", None)
        if status_consulta:
            consultas = consultas.filter(status=status_consulta)

        data_inicio = request.query_params.get("data_inicio", None)
        data_fim = request.query_params.get("data_fim", None)

        if data_inicio:
            consultas = consultas.filter(data_hora__date__gte=data_inicio)
        if data_fim:
            consultas = consultas.filter(data_hora__date__lte=data_fim)

        # Serializar consultas
        from consultas.serializers import ConsultaListSerializer

        serializer = ConsultaListSerializer(consultas, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def agenda(self, request, pk=None):
        """
        Visualizar agenda do profissional com horários livres
        """
        profissional = self.get_object()
        data = request.query_params.get("data", None)

        if not data:
            return Response(
                {"error": "Parâmetro data é obrigatório (formato: YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from datetime import datetime

            data_consulta = datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de data inválido. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar consultas agendadas para a data
        consultas_agendadas = profissional.consultas.filter(
            data_hora__date=data_consulta, status__in=["AGENDADA", "CONFIRMADA", "EM_ANDAMENTO"], is_active=True
        ).order_by("data_hora")

        # Serializar consultas agendadas
        from consultas.serializers import ConsultaListSerializer

        consultas_serializer = ConsultaListSerializer(consultas_agendadas, many=True)

        return Response(
            {
                "profissional": profissional.nome_social,
                "data": data,
                "consultas_agendadas": consultas_serializer.data,
                "total_consultas": consultas_agendadas.count(),
            }
        )

    @action(detail=True, methods=["post"])
    def desativar(self, request, pk=None):
        """
        Desativar profissional
        """
        profissional = self.get_object()

        # Verificar se há consultas futuras
        from django.utils import timezone

        consultas_futuras = profissional.consultas.filter(
            data_hora__gt=timezone.now(), status__in=["AGENDADA", "CONFIRMADA"], is_active=True
        )

        if consultas_futuras.exists():
            return Response(
                {
                    "error": "Não é possível desativar profissional com consultas futuras agendadas",
                    "consultas_futuras": consultas_futuras.count(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profissional.is_active = False
        profissional.save()

        return Response({"message": "Profissional desativado com sucesso"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reativar(self, request, pk=None):
        """
        Reativar profissional
        """
        profissional = self.get_object()
        profissional.is_active = True
        profissional.save()

        return Response({"message": "Profissional reativado com sucesso"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def estatisticas(self, request):
        """
        Estatísticas gerais dos profissionais
        """
        queryset = self.get_queryset()

        stats = {
            "total_profissionais": queryset.count(),
            "profissionais_ativos": queryset.filter(is_active=True).count(),
            "por_profissao": {},
            "aceita_convenio": queryset.filter(aceita_convenio=True).count(),
            "valor_medio_consulta": 0,
        }

        # Estatísticas por profissão
        from django.db.models import Avg, Count

        profissoes_stats = queryset.values("profissao").annotate(total=Count("id"), valor_medio=Avg("valor_consulta"))

        for prof_stat in profissoes_stats:
            profissao_display = dict(Profissional._meta.get_field("profissao").choices).get(
                prof_stat["profissao"], prof_stat["profissao"]
            )
            stats["por_profissao"][profissao_display] = {
                "total": prof_stat["total"],
                "valor_medio": prof_stat["valor_medio"] or 0,
            }

        # Valor médio geral
        valor_medio = queryset.aggregate(media=Avg("valor_consulta"))["media"]
        stats["valor_medio_consulta"] = valor_medio or 0

        return Response(stats)
