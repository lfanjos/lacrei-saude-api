"""
URLs para Profissionais - Lacrei Saúde API
==========================================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfissionalViewSet

app_name = 'profissionais'

# Router para ViewSets
router = DefaultRouter()
router.register(r'', ProfissionalViewSet, basename='profissional')

urlpatterns = [
    path('', include(router.urls)),
]