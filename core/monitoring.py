# core/monitoring.py
# Sistema de monitoreo y métricas básico

from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q, Avg
from django.conf import settings
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion, CustomUser
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger('core')

class SystemMonitor:
    """
    Monitor del sistema para recopilar métricas básicas de uso y performance.
    """

    @staticmethod
    def get_system_health():
        """
        Obtiene métricas básicas de salud del sistema.
        """
        try:
            health_data = {
                'timestamp': timezone.now().isoformat(),
                'status': 'healthy',
                'metrics': {
                    'database': SystemMonitor._check_database_health(),
                    'cache': SystemMonitor._check_cache_health(),
                    'storage': SystemMonitor._check_storage_health(),
                    'users': SystemMonitor._get_user_metrics(),
                    'business': SystemMonitor._get_business_metrics()
                }
            }

            # Guardar métricas en cache por 1 hora
            cache.set('system_health_metrics', health_data, 3600)
            return health_data

        except Exception as e:
            logger.error(f'Error collecting system health metrics: {e}')
            return {
                'timestamp': timezone.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def _check_database_health():
        """Verifica la salud de la base de datos."""
        try:
            start_time = timezone.now()

            # Test básico de conectividad
            total_empresas = Empresa.objects.count()
            total_equipos = Equipo.objects.count()
            total_usuarios = CustomUser.objects.count()

            response_time = (timezone.now() - start_time).total_seconds() * 1000

            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'total_empresas': total_empresas,
                'total_equipos': total_equipos,
                'total_usuarios': total_usuarios,
                'last_check': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Database health check failed: {e}')
            return {
                'status': 'error',
                'error': str(e),
                'last_check': timezone.now().isoformat()
            }

    @staticmethod
    def _check_cache_health():
        """Verifica la salud del sistema de cache."""
        try:
            start_time = timezone.now()

            # Test de escritura/lectura
            test_key = f'health_check_{timezone.now().timestamp()}'
            test_value = 'test_value'

            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)

            response_time = (timezone.now() - start_time).total_seconds() * 1000

            if retrieved_value == test_value:
                cache.delete(test_key)
                return {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2),
                    'last_check': timezone.now().isoformat()
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'Cache read/write test failed',
                    'last_check': timezone.now().isoformat()
                }

        except Exception as e:
            logger.error(f'Cache health check failed: {e}')
            return {
                'status': 'error',
                'error': str(e),
                'last_check': timezone.now().isoformat()
            }

    @staticmethod
    def _check_storage_health():
        """Verifica métricas básicas de almacenamiento."""
        try:
            # Calcular uso promedio de almacenamiento
            empresas_con_storage = []
            total_storage_mb = 0

            for empresa in Empresa.objects.all():
                try:
                    storage_mb = empresa.get_total_storage_used_mb()
                    empresas_con_storage.append({
                        'empresa_id': empresa.id,
                        'storage_mb': storage_mb,
                        'limite_mb': empresa.get_limite_almacenamiento(),
                        'porcentaje_uso': empresa.get_storage_usage_percentage()
                    })
                    total_storage_mb += storage_mb
                except Exception:
                    pass

            avg_storage = total_storage_mb / len(empresas_con_storage) if empresas_con_storage else 0

            return {
                'status': 'healthy',
                'total_empresas_monitoreadas': len(empresas_con_storage),
                'total_storage_mb': round(total_storage_mb, 2),
                'avg_storage_per_empresa_mb': round(avg_storage, 2),
                'last_check': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Storage health check failed: {e}')
            return {
                'status': 'error',
                'error': str(e),
                'last_check': timezone.now().isoformat()
            }

    @staticmethod
    def _get_user_metrics():
        """Obtiene métricas de usuarios."""
        try:
            now = timezone.now()
            last_week = now - timedelta(days=7)
            last_month = now - timedelta(days=30)

            # Incluir información de usuarios activos recientes (últimas 24 horas de actividad)
            last_24h = now - timedelta(hours=24)

            # Obtener usuarios activos de cache (últimos 15 minutos)
            active_users_15min = cache.get('active_users_15min', {})
            active_users_count = len(active_users_15min)

            # Obtener detalles de usuarios activos
            active_users_details = []
            for user_data in active_users_15min.values():
                try:
                    activity_time = datetime.fromisoformat(user_data['last_activity'])
                    active_users_details.append({
                        'username': user_data['username'],
                        'last_activity': activity_time.strftime('%H:%M:%S'),
                        'minutes_ago': int((now.timestamp() - user_data['timestamp']) / 60)
                    })
                except (KeyError, ValueError):
                    continue

            # Ordenar por actividad más reciente
            active_users_details.sort(key=lambda x: x['minutes_ago'])

            # Calcular uso del sistema de manera más realista
            # Basado en usuarios activos, operaciones de DB y actividad general
            base_usage = 15  # Uso base del sistema
            user_load = min(active_users_count * 5, 25)  # Máximo 25% por usuarios
            db_load = min(CustomUser.objects.count() * 0.1, 10)  # Carga de DB
            system_usage = min(base_usage + user_load + db_load, 95)  # Máximo 95%

            metrics = {
                'total_users': CustomUser.objects.count(),
                'active_users': CustomUser.objects.filter(is_active=True).count(),
                'users_with_empresa': CustomUser.objects.filter(empresa__isnull=False).count(),
                'superusers': CustomUser.objects.filter(is_superuser=True).count(),
                'users_logged_recently': CustomUser.objects.filter(last_login__gte=last_24h).count(),
                'users_active_15min': active_users_count,
                'active_users_details': active_users_details,
                'system_usage_percentage': round(system_usage, 1),
                'system_load_breakdown': {
                    'base_system': base_usage,
                    'user_activity': user_load,
                    'database_load': db_load
                },
                'new_users_this_week': CustomUser.objects.filter(date_joined__gte=last_week).count(),
                'new_users_this_month': CustomUser.objects.filter(date_joined__gte=last_month).count(),
                'active_user_list': [
                    {
                        'username': u.username,
                        'empresa': u.empresa.nombre if u.empresa else 'Sin empresa',
                        'last_login': u.last_login.isoformat() if u.last_login else 'Nunca',
                        'is_superuser': u.is_superuser
                    } for u in CustomUser.objects.filter(is_active=True)[:10]  # Máximo 10
                ],
                'last_check': now.isoformat()
            }

            return metrics

        except Exception as e:
            logger.error(f'Error getting user metrics: {e}')
            return {'error': str(e)}

    @staticmethod
    def _get_business_metrics():
        """Obtiene métricas de negocio."""
        try:
            now = timezone.now()
            today = now.date()
            last_week = now - timedelta(days=7)
            last_month = now - timedelta(days=30)

            # Métricas de empresas (solo empresas activas, no eliminadas)
            empresas_activas = Empresa.objects.filter(
                is_deleted=False,
                estado_suscripcion='Activo'
            ).count()

            # Si no hay empresas activas con ese estado, contar todas las no eliminadas
            if empresas_activas == 0:
                empresas_activas = Empresa.objects.filter(is_deleted=False).count()

            empresas_trial = Empresa.objects.filter(
                is_deleted=False,
                es_periodo_prueba=True
            ).count()

            # Métricas de equipos (solo de empresas activas)
            equipos_activos = Equipo.objects.filter(
                empresa__is_deleted=False,
                estado='Activo'
            ).count()
            equipos_mantenimiento = Equipo.objects.filter(
                empresa__is_deleted=False,
                estado='En Mantenimiento'
            ).count()
            equipos_calibracion = Equipo.objects.filter(estado='En Calibración').count()

            # Métricas de actividades recientes
            calibraciones_semana = Calibracion.objects.filter(fecha_calibracion__gte=last_week).count()
            mantenimientos_semana = Mantenimiento.objects.filter(fecha_mantenimiento__gte=last_week).count()
            comprobaciones_semana = Comprobacion.objects.filter(fecha_comprobacion__gte=last_week).count()

            # Próximas actividades críticas (próximos 7 días)
            next_week = now.date() + timedelta(days=7)
            calibraciones_proximas = Equipo.objects.filter(
                proxima_calibracion__lte=next_week,
                proxima_calibracion__gt=now.date(),
                estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
            ).count()

            mantenimientos_proximos = Equipo.objects.filter(
                proximo_mantenimiento__lte=next_week,
                proximo_mantenimiento__gt=now.date(),
                estado__in=['Activo', 'En Calibración', 'En Comprobación']
            ).count()

            metrics = {
                'empresas': {
                    'total': Empresa.objects.filter(is_deleted=False).count(),
                    'activas': empresas_activas,
                    'trial': empresas_trial,
                    'nuevas_este_mes': Empresa.objects.filter(
                        is_deleted=False,
                        fecha_registro__gte=last_month
                    ).count()
                },
                'equipos': {
                    'total': Equipo.objects.filter(empresa__is_deleted=False).count(),
                    'activos': equipos_activos,
                    'en_mantenimiento': equipos_mantenimiento,
                    'en_calibracion': equipos_calibracion,
                    'nuevos_este_mes': Equipo.objects.filter(
                        empresa__is_deleted=False,
                        fecha_registro__gte=last_month
                    ).count()
                },
                'actividades_recientes': {
                    'calibraciones_hoy': Calibracion.objects.filter(
                        fecha_calibracion__gte=now.date(),
                        fecha_calibracion__lt=now.date() + timedelta(days=1)
                    ).count(),
                    'mantenimientos_hoy': Mantenimiento.objects.filter(
                        fecha_mantenimiento__gte=now.date(),
                        fecha_mantenimiento__lt=now.date() + timedelta(days=1)
                    ).count(),
                    'comprobaciones_hoy': Comprobacion.objects.filter(
                        fecha_comprobacion__gte=now.date(),
                        fecha_comprobacion__lt=now.date() + timedelta(days=1)
                    ).count(),
                    'calibraciones_esta_semana': calibraciones_semana,
                    'mantenimientos_esta_semana': mantenimientos_semana,
                    'comprobaciones_esta_semana': comprobaciones_semana
                },
                'empresas_detalle': [
                    {
                        'nombre': e.nombre,
                        'equipos': e.equipos.filter(empresa__is_deleted=False).count(),
                        'estado': e.estado_suscripcion,
                        'limite': e.limite_equipos_empresa,
                        'porcentaje_uso': round((e.equipos.filter(empresa__is_deleted=False).count() / max(e.limite_equipos_empresa, 1)) * 100, 1)
                    } for e in Empresa.objects.filter(is_deleted=False)[:5]
                ],
                'proximas_actividades': {
                    'calibraciones_proxima_semana': calibraciones_proximas,
                    'mantenimientos_proxima_semana': mantenimientos_proximos
                },
                'last_check': now.isoformat()
            }

            return metrics

        except Exception as e:
            logger.error(f'Error getting business metrics: {e}')
            return {'error': str(e)}

    @staticmethod
    def get_performance_metrics():
        """
        Obtiene métricas de performance del sistema.
        """
        try:
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'cache_stats': SystemMonitor._get_cache_stats(),
                'database_stats': SystemMonitor._get_database_stats(),
                'error_rate': SystemMonitor._get_error_rate()
            }

            return metrics

        except Exception as e:
            logger.error(f'Error collecting performance metrics: {e}')
            return {'error': str(e)}

    @staticmethod
    def _get_cache_stats():
        """Obtiene estadísticas básicas del cache."""
        try:
            # Contar claves de cache relacionadas con storage
            storage_cache_count = 0
            test_keys = ['storage_usage_empresa_*']

            # Esto es básico, en un sistema real usarías Redis INFO
            return {
                'estimated_storage_cache_entries': storage_cache_count,
                'status': 'monitored',
                'last_check': timezone.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_database_stats():
        """Obtiene estadísticas básicas de la base de datos."""
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                # Contar total de registros en tablas principales
                stats = {}

                tables = [
                    'core_empresa', 'core_equipo', 'core_calibracion',
                    'core_mantenimiento', 'core_comprobacion', 'core_customuser'
                ]

                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        stats[table] = count
                    except Exception:
                        stats[table] = 'unknown'

                return {
                    'table_counts': stats,
                    'last_check': timezone.now().isoformat()
                }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_error_rate():
        """Obtiene tasa básica de errores (simplificado)."""
        try:
            # En un sistema real, esto leería de logs estructurados
            return {
                'error_rate_last_hour': 'unknown',
                'total_errors_today': 'unknown',
                'status': 'basic_monitoring',
                'last_check': timezone.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def log_system_event(event_type, details=None, user=None):
        """
        Registra eventos del sistema para monitoreo.
        """
        try:
            event_data = {
                'timestamp': timezone.now().isoformat(),
                'event_type': event_type,
                'details': details or {},
                'user': user.username if user else 'system'
            }

            # Log del evento
            logger.info(f'System event: {event_type}', extra=event_data)

            # También podríamos guardarlo en una tabla de eventos si fuera necesario
            return True

        except Exception as e:
            logger.error(f'Error logging system event: {e}')
            return False


class AlertManager:
    """
    Gestiona alertas básicas del sistema.
    """

    @staticmethod
    def check_system_alerts():
        """
        Verifica condiciones que requieren alertas.
        """
        alerts = []

        try:
            # Verificar empresas con storage alto
            empresas_storage_alto = []
            for empresa in Empresa.objects.all():
                try:
                    percentage = empresa.get_storage_usage_percentage()
                    if percentage >= 90:
                        empresas_storage_alto.append({
                            'empresa': empresa.nombre,
                            'percentage': percentage
                        })
                except Exception:
                    pass

            if empresas_storage_alto:
                alerts.append({
                    'type': 'storage_warning',
                    'severity': 'high',
                    'message': f'{len(empresas_storage_alto)} empresas con storage >90%',
                    'details': empresas_storage_alto
                })

            # Verificar calibraciones vencidas
            equipos_vencidos = Equipo.objects.filter(
                proxima_calibracion__lt=timezone.now().date(),
                estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
            ).count()

            if equipos_vencidos > 0:
                alerts.append({
                    'type': 'calibration_overdue',
                    'severity': 'medium',
                    'message': f'{equipos_vencidos} equipos con calibración vencida',
                    'count': equipos_vencidos
                })

            # Verificar empresas en período de prueba próximo a expirar
            empresas_trial_expiring = []
            for empresa in Empresa.objects.filter(es_periodo_prueba=True):
                try:
                    dias_restantes = empresa.get_dias_restantes_plan()
                    if isinstance(dias_restantes, (int, float)) and dias_restantes <= 3:
                        empresas_trial_expiring.append({
                            'empresa': empresa.nombre,
                            'dias_restantes': dias_restantes
                        })
                except Exception:
                    pass

            if empresas_trial_expiring:
                alerts.append({
                    'type': 'trial_expiring',
                    'severity': 'medium',
                    'message': f'{len(empresas_trial_expiring)} trials expiran en ≤3 días',
                    'details': empresas_trial_expiring
                })

            return alerts

        except Exception as e:
            logger.error(f'Error checking system alerts: {e}')
            return [{'type': 'system_error', 'severity': 'high', 'message': str(e)}]


# Decorator para monitoreo de views
def monitor_view(func):
    """
    Decorator simple para monitorear views (placeholder).
    En el futuro se puede expandir para métricas de performance.
    """
    def wrapper(*args, **kwargs):
        # Por ahora solo ejecuta la vista normalmente
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper