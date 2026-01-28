"""
URLs para Profissionais - Lacrei Saúde API
==========================================
"""

from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import ProfissionalViewSet

app_name = "profissionais"

# Router para ViewSets
router = DefaultRouter()
router.register(r"", ProfissionalViewSet, basename="profissional")

urlpatterns = [
    path("", include(router.urls)),
]
