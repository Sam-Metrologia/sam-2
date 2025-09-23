# core/admin_services.py
# Servicios de administración para ejecutar desde la interfaz web

from django.core.management import call_command
from django.utils import timezone
from django.core.cache import cache
from core.monitoring import SystemMonitor, AlertManager
from core.notifications import NotificationScheduler
import io
import logging
import json
from datetime import datetime, timedelta
import threading

logger = logging.getLogger('core')

class AdminService:
    """
    Servicio para ejecutar comandos de administración desde la web.
    """

    @staticmethod
    def execute_maintenance(task_type='all', dry_run=False):
        """
        Ejecuta comandos de mantenimiento y retorna resultados.
        """
        try:
            # Capturar output del comando
            output = io.StringIO()

            call_command(
                'maintenance',
                task=task_type,
                dry_run=dry_run,
                stdout=output,
                stderr=output
            )

            result = {
                'success': True,
                'output': output.getvalue(),
                'timestamp': timezone.now().isoformat(),
                'task_type': task_type,
                'dry_run': dry_run
            }

            # Log de la ejecución
            logger.info(f'Maintenance executed from web interface: {task_type}', extra=result)

            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'task_type': task_type
            }

            logger.error(f'Error executing maintenance from web: {e}', extra=error_result)
            return error_result

    @staticmethod
    def execute_notifications(notification_type='all', dry_run=False):
        """
        Ejecuta comandos de notificaciones y retorna resultados.
        """
        try:
            output = io.StringIO()

            call_command(
                'send_notifications',
                type=notification_type,
                dry_run=dry_run,
                stdout=output,
                stderr=output
            )

            result = {
                'success': True,
                'output': output.getvalue(),
                'timestamp': timezone.now().isoformat(),
                'notification_type': notification_type,
                'dry_run': dry_run
            }

            logger.info(f'Notifications executed from web interface: {notification_type}', extra=result)
            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'notification_type': notification_type
            }

            logger.error(f'Error executing notifications from web: {e}', extra=error_result)
            return error_result

    @staticmethod
    def execute_backup(empresa_id=None, include_files=False, backup_format='both'):
        """
        Ejecuta backup de datos y retorna resultados.
        """
        try:
            output = io.StringIO()

            args = {
                'format': backup_format,
                'include_files': include_files,
                'stdout': output,
                'stderr': output
            }

            if empresa_id:
                args['empresa_id'] = empresa_id

            call_command('backup_data', **args)

            result = {
                'success': True,
                'output': output.getvalue(),
                'timestamp': timezone.now().isoformat(),
                'empresa_id': empresa_id,
                'include_files': include_files,
                'format': backup_format
            }

            logger.info(f'Backup executed from web interface', extra=result)
            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'empresa_id': empresa_id
            }

            logger.error(f'Error executing backup from web: {e}', extra=error_result)
            return error_result

    @staticmethod
    def get_system_status():
        """
        Obtiene estado completo del sistema.
        """
        try:
            # Health check
            health_data = SystemMonitor.get_system_health()

            # Alertas
            alerts = AlertManager.check_system_alerts()

            # Métricas de performance
            performance_data = SystemMonitor.get_performance_metrics()

            return {
                'success': True,
                'health': health_data,
                'alerts': alerts,
                'performance': performance_data,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f'Error getting system status: {e}')
            return {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }

    @staticmethod
    def get_execution_history():
        """
        Obtiene historial de ejecuciones desde cache.
        """
        try:
            history = cache.get('admin_execution_history', [])
            return {
                'success': True,
                'history': history[-20:],  # Últimas 20 ejecuciones
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f'Error getting execution history: {e}')
            return {
                'success': False,
                'error': str(e),
                'history': []
            }

    @staticmethod
    def save_execution_to_history(action, result, user=None):
        """
        Guarda ejecución en el historial.
        """
        try:
            history = cache.get('admin_execution_history', [])

            execution_record = {
                'action': action,
                'timestamp': timezone.now().isoformat(),
                'success': result.get('success', False),
                'user': user.username if user else 'system',
                'summary': AdminService._get_execution_summary(action, result)
            }

            if not result.get('success', False):
                execution_record['error'] = result.get('error', 'Unknown error')

            history.append(execution_record)

            # Mantener solo últimas 50 ejecuciones
            if len(history) > 50:
                history = history[-50:]

            cache.set('admin_execution_history', history, 86400 * 7)  # 7 días

            return True

        except Exception as e:
            logger.error(f'Error saving execution to history: {e}')
            return False

    @staticmethod
    def _get_execution_summary(action, result):
        """
        Genera resumen de ejecución para el historial.
        """
        if not result.get('success', False):
            return f"Error en {action}"

        if 'maintenance' in action:
            return "Mantenimiento ejecutado correctamente"
        elif 'notification' in action:
            return "Notificaciones enviadas"
        elif 'backup' in action:
            return "Backup creado exitosamente"
        elif 'system_status' in action:
            return "Estado del sistema verificado"
        else:
            return f"{action} completado"

    @staticmethod
    def execute_command_async(command_func, *args, **kwargs):
        """
        Ejecuta comando de forma asíncrona para comandos largos.
        """
        def run_command():
            try:
                result = command_func(*args, **kwargs)
                cache_key = f"async_result_{kwargs.get('user_id', 'system')}_{timezone.now().timestamp()}"
                cache.set(cache_key, result, 3600)  # 1 hora
                return cache_key
            except Exception as e:
                logger.error(f'Error in async command execution: {e}')
                return None

        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()

        return {
            'success': True,
            'message': 'Comando ejecutándose en segundo plano',
            'async': True
        }


class ScheduleManager:
    """
    Gestiona la programación automática de tareas.
    """

    SCHEDULE_CACHE_KEY = 'admin_schedule_config'

    @staticmethod
    def get_schedule_config():
        """
        Obtiene configuración de programación.
        """
        default_config = {
            'maintenance_daily': {
                'enabled': False,
                'time': '02:00',
                'tasks': ['cache', 'database']
            },
            'notifications_daily': {
                'enabled': False,
                'time': '08:00',
                'types': ['calibration', 'maintenance']
            },
            'maintenance_weekly': {
                'enabled': False,
                'day': 'sunday',
                'time': '03:00',
                'tasks': ['all']
            },
            'notifications_weekly': {
                'enabled': False,
                'day': 'monday',
                'time': '09:00',
                'types': ['weekly']
            },
            'backup_monthly': {
                'enabled': False,
                'day': 1,
                'time': '01:00',
                'include_files': True
            }
        }

        try:
            config = cache.get(ScheduleManager.SCHEDULE_CACHE_KEY, default_config)
            return config
        except Exception:
            return default_config

    @staticmethod
    def save_schedule_config(config):
        """
        Guarda configuración de programación.
        """
        try:
            cache.set(ScheduleManager.SCHEDULE_CACHE_KEY, config, 86400 * 365)  # 1 año

            logger.info('Schedule configuration updated', extra={'config': config})
            return True
        except Exception as e:
            logger.error(f'Error saving schedule config: {e}')
            return False

    @staticmethod
    def check_scheduled_tasks():
        """
        Verifica si hay tareas programadas que ejecutar.
        Esta función debería ser llamada por un cron job o tarea programada externa.
        """
        try:
            config = ScheduleManager.get_schedule_config()
            current_time = timezone.now()
            executed_tasks = []

            # Verificar tareas diarias
            if config['maintenance_daily']['enabled']:
                if ScheduleManager._should_execute_daily(current_time, config['maintenance_daily']['time']):
                    result = AdminService.execute_maintenance(task_type=','.join(config['maintenance_daily']['tasks']))
                    if result['success']:
                        executed_tasks.append('maintenance_daily')

            if config['notifications_daily']['enabled']:
                if ScheduleManager._should_execute_daily(current_time, config['notifications_daily']['time']):
                    result = AdminService.execute_notifications(notification_type=','.join(config['notifications_daily']['types']))
                    if result['success']:
                        executed_tasks.append('notifications_daily')

            # Verificar tareas semanales
            if config['maintenance_weekly']['enabled']:
                if ScheduleManager._should_execute_weekly(current_time, config['maintenance_weekly']['day'], config['maintenance_weekly']['time']):
                    result = AdminService.execute_maintenance(task_type=','.join(config['maintenance_weekly']['tasks']))
                    if result['success']:
                        executed_tasks.append('maintenance_weekly')

            if config['notifications_weekly']['enabled']:
                if ScheduleManager._should_execute_weekly(current_time, config['notifications_weekly']['day'], config['notifications_weekly']['time']):
                    result = AdminService.execute_notifications(notification_type=','.join(config['notifications_weekly']['types']))
                    if result['success']:
                        executed_tasks.append('notifications_weekly')

            # Verificar backup mensual
            if config['backup_monthly']['enabled']:
                if ScheduleManager._should_execute_monthly(current_time, config['backup_monthly']['day'], config['backup_monthly']['time']):
                    result = AdminService.execute_backup(include_files=config['backup_monthly']['include_files'])
                    if result['success']:
                        executed_tasks.append('backup_monthly')

            return {
                'success': True,
                'executed_tasks': executed_tasks,
                'timestamp': current_time.isoformat()
            }

        except Exception as e:
            logger.error(f'Error checking scheduled tasks: {e}')
            return {
                'success': False,
                'error': str(e),
                'executed_tasks': []
            }

    @staticmethod
    def _should_execute_daily(current_time, target_time):
        """Verifica si debe ejecutar tarea diaria."""
        # Implementación básica - en producción usaríamos un scheduler más robusto
        target_hour, target_minute = map(int, target_time.split(':'))
        return (current_time.hour == target_hour and
                current_time.minute == target_minute)

    @staticmethod
    def _should_execute_weekly(current_time, target_day, target_time):
        """Verifica si debe ejecutar tarea semanal."""
        days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6}

        target_weekday = days.get(target_day.lower(), 0)
        target_hour, target_minute = map(int, target_time.split(':'))

        return (current_time.weekday() == target_weekday and
                current_time.hour == target_hour and
                current_time.minute == target_minute)

    @staticmethod
    def _should_execute_monthly(current_time, target_day, target_time):
        """Verifica si debe ejecutar tarea mensual."""
        target_hour, target_minute = map(int, target_time.split(':'))

        return (current_time.day == target_day and
                current_time.hour == target_hour and
                current_time.minute == target_minute)