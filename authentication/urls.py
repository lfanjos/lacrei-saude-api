"""
URLs para Autenticação - Lacrei Saúde API
=========================================
"""

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from django.urls import include, path

from .views import (
    APIKeyViewSet,
    CustomTokenObtainPairView,
    UserViewSet,
    auth_status,
    logout_view,
    register_view,
    security_stats,
)

app_name = "authentication"

# Router para ViewSets
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"api-keys", APIKeyViewSet, basename="apikey")

urlpatterns = [
    # Autenticação JWT
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", logout_view, name="logout"),
    path("register/", register_view, name="register"),
    # Status e informações do usuário
    path("status/", auth_status, name="auth_status"),
    path("security/stats/", security_stats, name="security_stats"),
    # ViewSets
    path("", include(router.urls)),
]
