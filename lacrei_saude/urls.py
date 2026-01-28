"""
URL configuration for lacrei_saude project.

Lacrei Saúde API - Gerenciamento de Consultas Médicas
=====================================================
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from .security_views import (
    csp_report_view, SecurityCheckView, SecurityHeadersTestView, 
    CORSTestView, security_txt_view
)
from .monitoring_views import (
    LogStatsView, AccessLogAnalysisView, ErrorLogView, HealthCheckView
)

def api_root(request):
    """Endpoint raiz da API"""
    return JsonResponse({
        'message': 'Bem-vindo à API Lacrei Saúde',
        'version': '1.0',
        'endpoints': {
            'profissionais': '/api/v1/profissionais/',
            'consultas': '/api/v1/consultas/',
            'admin': '/admin/'
        }
    })

def test_view(request):
    """Endpoint de teste"""
    return JsonResponse({'status': 'API funcionando!'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_root, name='api-root'),
    path('test/', test_view, name='test'),
    
    # Authentication endpoints
    path('api/auth/', include('authentication.urls')),
    
    # API v1 Endpoints
    path('api/v1/profissionais/', include('profissionais.urls')),
    path('api/v1/consultas/', include('consultas.urls')),
    
    # Security endpoints
    path('api/security/csp-report/', csp_report_view, name='csp-report'),
    path('api/security/check/', SecurityCheckView.as_view(), name='security-check'),
    path('api/security/headers-test/', SecurityHeadersTestView.as_view(), name='headers-test'),
    path('api/security/cors-test/', CORSTestView.as_view(), name='cors-test'),
    path('.well-known/security.txt', security_txt_view, name='security-txt'),
    
    # Monitoring endpoints
    path('api/monitoring/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/monitoring/logs/stats/', LogStatsView.as_view(), name='log-stats'),
    path('api/monitoring/logs/access/', AccessLogAnalysisView.as_view(), name='access-analysis'),
    path('api/monitoring/logs/errors/', ErrorLogView.as_view(), name='error-logs'),
    
    # Django REST Framework browsable API
    path('api-auth/', include('rest_framework.urls')),
]
