"""
Views de Monitoramento - Lacrei Saúde API
========================================
"""

import json
import os
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsOwnerOrAdmin


class LogStatsView(View):
    """
    View para estatísticas de logs
    """
    
    def get(self, request):
        """
        Retorna estatísticas dos logs
        """
        if not self._is_admin_user(request):
            return JsonResponse({'error': 'Admin access required'}, status=403)
        
        logs_dir = settings.BASE_DIR / 'logs'
        stats = {
            'log_files': {},
            'total_size_mb': 0,
            'last_updated': None,
        }
        
        if logs_dir.exists():
            for log_file in logs_dir.glob('*.log'):
                file_stats = log_file.stat()
                size_mb = round(file_stats.st_size / (1024 * 1024), 2)
                
                stats['log_files'][log_file.name] = {
                    'size_mb': size_mb,
                    'last_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    'lines_count': self._count_lines(log_file),
                }
                stats['total_size_mb'] += size_mb
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        
        return JsonResponse(stats)
    
    def _count_lines(self, file_path):
        """
        Conta linhas em um arquivo
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def _is_admin_user(self, request):
        """
        Verifica se o usuário é admin
        """
        return (hasattr(request, 'user') and 
                hasattr(request.user, 'is_admin') and 
                request.user.is_admin)


class AccessLogAnalysisView(View):
    """
    View para análise de logs de acesso
    """
    
    def get(self, request):
        """
        Analisa logs de acesso das últimas horas
        """
        if not self._is_admin_user(request):
            return JsonResponse({'error': 'Admin access required'}, status=403)
        
        hours = int(request.GET.get('hours', 24))
        analysis = self._analyze_access_logs(hours)
        
        return JsonResponse(analysis)
    
    def _analyze_access_logs(self, hours):
        """
        Analisa logs de acesso
        """
        logs_dir = settings.BASE_DIR / 'logs'
        access_log = logs_dir / 'access.log'
        
        analysis = {
            'period_hours': hours,
            'total_requests': 0,
            'requests_by_status': {},
            'requests_by_endpoint': {},
            'requests_by_method': {},
            'top_ips': {},
            'auth_types': {},
            'avg_response_time': 0,
            'slow_requests': 0,
        }
        
        if not access_log.exists():
            return analysis
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        total_response_time = 0
        response_time_count = 0
        
        try:
            with open(access_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    # Parse da linha de log
                    log_data = self._parse_access_log_line(line)
                    if not log_data or log_data.get('timestamp', datetime.min) < cutoff_time:
                        continue
                    
                    analysis['total_requests'] += 1
                    
                    # Status codes
                    status = log_data.get('status_code', 'unknown')
                    analysis['requests_by_status'][status] = analysis['requests_by_status'].get(status, 0) + 1
                    
                    # Endpoints
                    path = log_data.get('path', 'unknown')
                    analysis['requests_by_endpoint'][path] = analysis['requests_by_endpoint'].get(path, 0) + 1
                    
                    # Métodos HTTP
                    method = log_data.get('method', 'unknown')
                    analysis['requests_by_method'][method] = analysis['requests_by_method'].get(method, 0) + 1
                    
                    # IPs
                    ip = log_data.get('ip_address', 'unknown')
                    analysis['top_ips'][ip] = analysis['top_ips'].get(ip, 0) + 1
                    
                    # Tipos de auth
                    auth_type = log_data.get('auth_type', 'none')
                    analysis['auth_types'][auth_type] = analysis['auth_types'].get(auth_type, 0) + 1
                    
                    # Response time
                    duration = log_data.get('duration_ms', 0)
                    if duration > 0:
                        total_response_time += duration
                        response_time_count += 1
                        
                        if duration > 2000:  # Requisições > 2s
                            analysis['slow_requests'] += 1
        
        except Exception as e:
            analysis['error'] = str(e)
        
        # Calcular média de response time
        if response_time_count > 0:
            analysis['avg_response_time'] = round(total_response_time / response_time_count, 2)
        
        # Ordenar os top IPs
        analysis['top_ips'] = dict(sorted(
            analysis['top_ips'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10])
        
        return analysis
    
    def _parse_access_log_line(self, line):
        """
        Faz parse de uma linha de log de acesso
        """
        try:
            # Exemplo: [2026-01-27 17:30:00] ACCESS | API GET /api/v1/profissionais/ | Status: 200 | Duration: 45.2ms | User: admin | IP: 172.21.0.1 | Auth: api_key
            if '| Status:' in line and '| Duration:' in line:
                parts = line.split('|')
                
                # Timestamp
                timestamp_str = line.split(']')[0].replace('[', '').strip()
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = datetime.now()
                
                # Method e Path
                if 'API' in parts[1]:
                    method_path = parts[1].replace('ACCESS', '').replace('API', '').strip()
                    method, path = method_path.split(' ', 1)
                else:
                    method_path = parts[1].replace('ACCESS', '').strip()
                    method, path = method_path.split(' ', 1)
                
                # Status
                status_part = [p for p in parts if 'Status:' in p][0]
                status_code = status_part.split('Status:')[1].strip()
                
                # Duration
                duration_part = [p for p in parts if 'Duration:' in p][0]
                duration_str = duration_part.split('Duration:')[1].replace('ms', '').strip()
                duration_ms = float(duration_str)
                
                # IP
                ip_part = [p for p in parts if 'IP:' in p][0]
                ip_address = ip_part.split('IP:')[1].strip()
                
                # Auth type
                auth_type = 'none'
                auth_parts = [p for p in parts if 'Auth:' in p]
                if auth_parts:
                    auth_type = auth_parts[0].split('Auth:')[1].strip()
                
                return {
                    'timestamp': timestamp,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration_ms': duration_ms,
                    'ip_address': ip_address,
                    'auth_type': auth_type,
                }
        except:
            return None
        
        return None
    
    def _is_admin_user(self, request):
        """
        Verifica se o usuário é admin
        """
        return (hasattr(request, 'user') and 
                hasattr(request.user, 'is_admin') and 
                request.user.is_admin)


class ErrorLogView(View):
    """
    View para análise de logs de erro
    """
    
    def get(self, request):
        """
        Retorna últimos erros
        """
        if not self._is_admin_user(request):
            return JsonResponse({'error': 'Admin access required'}, status=403)
        
        limit = int(request.GET.get('limit', 50))
        errors = self._get_recent_errors(limit)
        
        return JsonResponse({
            'errors': errors,
            'count': len(errors),
        })
    
    def _get_recent_errors(self, limit):
        """
        Obtém erros recentes
        """
        logs_dir = settings.BASE_DIR / 'logs'
        error_log = logs_dir / 'errors.log'
        
        if not error_log.exists():
            return []
        
        errors = []
        try:
            with open(error_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # Ler as últimas linhas
                for line in reversed(lines[-limit*3:]):  # *3 para ter margem
                    if not line.strip():
                        continue
                    
                    error_data = self._parse_error_log_line(line)
                    if error_data:
                        errors.append(error_data)
                        
                        if len(errors) >= limit:
                            break
        
        except Exception as e:
            return [{'error': f'Failed to read error log: {str(e)}'}]
        
        return errors[:limit]
    
    def _parse_error_log_line(self, line):
        """
        Faz parse de uma linha de log de erro
        """
        try:
            if 'EXCEPTION' in line:
                # Exemplo: [2026-01-27 17:30:00] ERROR django.request | EXCEPTION ValueError: Invalid input | Path: /api/test/ | Method: POST
                parts = line.split('|')
                
                # Timestamp
                timestamp_str = line.split(']')[0].replace('[', '').strip()
                
                # Exception info
                exception_part = [p for p in parts if 'EXCEPTION' in p][0]
                exception_info = exception_part.replace('EXCEPTION', '').strip()
                
                # Path
                path = 'unknown'
                path_parts = [p for p in parts if 'Path:' in p]
                if path_parts:
                    path = path_parts[0].split('Path:')[1].strip()
                
                return {
                    'timestamp': timestamp_str,
                    'exception': exception_info,
                    'path': path,
                }
        except:
            return None
        
        return None
    
    def _is_admin_user(self, request):
        """
        Verifica se o usuário é admin
        """
        return (hasattr(request, 'user') and 
                hasattr(request.user, 'is_admin') and 
                request.user.is_admin)


class HealthCheckView(View):
    """
    View para health check da aplicação
    """
    
    def get(self, request):
        """
        Verifica saúde da aplicação
        """
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'checks': {},
        }
        
        # Verificar banco de dados
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_data['checks']['database'] = 'healthy'
        except Exception as e:
            health_data['checks']['database'] = f'unhealthy: {str(e)}'
            health_data['status'] = 'unhealthy'
        
        # Verificar logs
        try:
            logs_dir = settings.BASE_DIR / 'logs'
            if logs_dir.exists():
                health_data['checks']['logs_directory'] = 'healthy'
            else:
                health_data['checks']['logs_directory'] = 'unhealthy: logs directory not found'
                health_data['status'] = 'unhealthy'
        except Exception as e:
            health_data['checks']['logs_directory'] = f'unhealthy: {str(e)}'
            health_data['status'] = 'unhealthy'
        
        # Verificar disco
        try:
            import shutil
            disk_usage = shutil.disk_usage(settings.BASE_DIR)
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            if free_percent > 10:
                health_data['checks']['disk_space'] = f'healthy: {free_percent:.1f}% free'
            else:
                health_data['checks']['disk_space'] = f'warning: {free_percent:.1f}% free'
        except Exception as e:
            health_data['checks']['disk_space'] = f'unknown: {str(e)}'
        
        status_code = 200 if health_data['status'] == 'healthy' else 503
        return JsonResponse(health_data, status=status_code)