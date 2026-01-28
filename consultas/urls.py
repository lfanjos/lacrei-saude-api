"""
URLs para Consultas - Lacrei Saúde API
======================================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultaViewSet

app_name = 'consultas'

# Router para ViewSets
router = DefaultRouter()
router.register(r'', ConsultaViewSet, basename='consulta')

urlpatterns = [
    path('', include(router.urls)),
]