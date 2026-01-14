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
from .constants import ESTADO_ACTIVO, ESTADO_EN_MANTENIMIENTO, ESTADO_EN_COMPROBACION

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
    def execute_notifications(notification_type='all', dry_run=False, empresa_id=None, days_ahead=15):
        """
        Ejecuta comandos de notificaciones y retorna resultados.
        """
        try:
            from core.notifications import NotificationScheduler
            from core.models import Empresa

            emails_sent = 0
            empresas_processed = 0
            output_messages = []

            if empresa_id:
                # Enviar solo a empresa específica
                try:
                    empresa = Empresa.objects.get(id=empresa_id)

                    if dry_run:
                        output_messages.append(f'[MODO PRUEBA] Se enviarían notificaciones a: {empresa.nombre}')
                    else:
                        if notification_type == 'consolidated':
                            result = NotificationScheduler.send_consolidated_reminder(empresa, days_ahead)
                            if result:
                                emails_sent += 1
                                output_messages.append(f'Email consolidado enviado a {empresa.nombre}')
                        else:
                            # Otros tipos de notificación individual
                            result = NotificationScheduler.send_consolidated_reminder(empresa, days_ahead)
                            if result:
                                emails_sent += 1
                                output_messages.append(f'Notificación {notification_type} enviada a {empresa.nombre}')

                    empresas_processed = 1

                except Empresa.DoesNotExist:
                    raise Exception(f'Empresa con ID {empresa_id} no encontrada')

            else:
                # Enviar a todas las empresas
                if notification_type == 'consolidated':
                    if dry_run:
                        empresas = Empresa.objects.filter(estado_suscripcion='Activo', is_deleted=False)
                        output_messages.append(f'[MODO PRUEBA] Se enviarían notificaciones consolidadas a {empresas.count()} empresas')
                        empresas_processed = empresas.count()
                    else:
                        emails_sent = NotificationScheduler.check_all_reminders()
                        empresas_processed = Empresa.objects.filter(estado_suscripcion='Activo', is_deleted=False).count()
                        output_messages.append(f'Notificaciones consolidadas enviadas: {emails_sent} emails')

                elif notification_type == 'weekly':
                    if dry_run:
                        empresas = Empresa.objects.filter(estado_suscripcion='Activo', is_deleted=False)
                        output_messages.append(f'[MODO PRUEBA] Se enviarían resúmenes semanales a {empresas.count()} empresas')
                        empresas_processed = empresas.count()
                    else:
                        emails_sent = NotificationScheduler.send_weekly_summaries()
                        output_messages.append(f'Resúmenes semanales enviados: {emails_sent} emails')
                        empresas_processed = emails_sent

                elif notification_type == 'weekly_overdue':
                    if dry_run:
                        empresas = Empresa.objects.filter(estado_suscripcion='Activo', is_deleted=False)
                        # Count overdue equipment across all companies
                        from datetime import date
                        today = date.today()
                        overdue_count = 0
                        for empresa in empresas:
                            overdue_count += empresa.equipos.filter(
                                proxima_calibracion__lt=today,
                                estado__in=[ESTADO_ACTIVO, ESTADO_EN_MANTENIMIENTO, ESTADO_EN_COMPROBACION]
                            ).count()
                            overdue_count += empresa.equipos.filter(
                                proximo_mantenimiento__lt=today,
                                estado__in=['Activo', 'En Calibración', 'En Comprobación']
                            ).count()
                            overdue_count += empresa.equipos.filter(
                                proxima_comprobacion__lt=today,
                                estado__in=['Activo', 'En Calibración', 'En Mantenimiento']
                            ).count()
                        output_messages.append(f'[MODO PRUEBA] Se enviarían recordatorios semanales para {overdue_count} actividades vencidas')
                        empresas_processed = empresas.count()
                    else:
                        emails_sent = NotificationScheduler.send_weekly_overdue_reminders()
                        output_messages.append(f'Recordatorios semanales vencidos enviados: {emails_sent} emails')
                        empresas_processed = emails_sent

                else:
                    # Para otros tipos, usar el comando original
                    output = io.StringIO()
                    try:
                        call_command(
                            'send_notifications',
                            type=notification_type,
                            dry_run=dry_run,
                            stdout=output,
                            stderr=output
                        )
                        output_messages.append(output.getvalue())
                    except:
                        # Fallback para tipos específicos
                        if notification_type == 'calibration':
                            emails_sent = NotificationScheduler.check_calibration_reminders()
                        elif notification_type == 'maintenance':
                            emails_sent = NotificationScheduler.check_maintenance_reminders()
                        output_messages.append(f'Notificaciones {notification_type} procesadas')

            result = {
                'success': True,
                'output': '\n'.join(output_messages),
                'timestamp': timezone.now().isoformat(),
                'notification_type': notification_type,
                'dry_run': dry_run,
                'details': {
                    'emails_sent': emails_sent,
                    'empresas_processed': empresas_processed,
                    'empresa_id': empresa_id,
                    'days_ahead': days_ahead
                }
            }

            logger.info(f'Notifications executed from web interface: {notification_type}, empresa_id: {empresa_id}', extra=result)
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
    def execute_cleanup_backups(retention_months=6, dry_run=False):
        """
        Ejecuta limpieza de backups antiguos de S3 y retorna resultados.
        """
        try:
            output = io.StringIO()

            call_command(
                'cleanup_old_backups',
                retention_months=retention_months,
                dry_run=dry_run,
                verbose=True,
                stdout=output,
                stderr=output
            )

            output_text = output.getvalue()

            # Extraer números de archivos eliminados y tamaño del output
            import re
            deleted_match = re.search(r'(\d+) archivos', output_text)
            size_match = re.search(r'([\d.]+) MB', output_text)

            deleted_count = int(deleted_match.group(1)) if deleted_match else 0
            total_size_mb = float(size_match.group(1)) if size_match else 0.0

            result = {
                'success': True,
                'output': output_text,
                'timestamp': timezone.now().isoformat(),
                'retention_months': retention_months,
                'dry_run': dry_run,
                'details': {
                    'deleted_count': deleted_count,
                    'total_size_mb': total_size_mb
                }
            }

            logger.info(f'Backup cleanup executed from web interface: {deleted_count} files, {total_size_mb} MB')
            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'retention_months': retention_months,
                'dry_run': dry_run
            }

            logger.error(f'Error executing backup cleanup from web: {e}', extra=error_result)
            return error_result

    @staticmethod
    def execute_restore(backup_file_path, new_name=None, overwrite=False, restore_files=False, dry_run=False):
        """
        Ejecuta restauración de backup y retorna resultados.
        """
        try:
            output = io.StringIO()

            args = {
                'backup_file': backup_file_path,
                'dry_run': dry_run,
                'overwrite': overwrite,
                'restore_files': restore_files,
                'stdout': output,
                'stderr': output
            }

            if new_name:
                args['new_name'] = new_name

            call_command('restore_backup', **args)

            result = {
                'success': True,
                'output': output.getvalue(),
                'timestamp': timezone.now().isoformat(),
                'backup_file': backup_file_path,
                'new_name': new_name,
                'overwrite': overwrite,
                'restore_files': restore_files,
                'dry_run': dry_run
            }

            logger.info(f'Restore executed from web interface', extra=result)
            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
                'backup_file': backup_file_path
            }

            logger.error(f'Error executing restore from web: {e}', extra=error_result)
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
        elif 'restore' in action:
            return "Restauración completada exitosamente"
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

    @staticmethod
    def get_schedule_config():
        """
        Obtiene configuración de programación desde base de datos.
        """
        try:
            from core.models import SystemScheduleConfig
            config_obj = SystemScheduleConfig.get_or_create_config()
            return config_obj.get_config()
        except Exception as e:
            logger.error(f'Error getting schedule config from DB: {e}')
            # Fallback a configuración por defecto
            from core.models import SystemScheduleConfig
            return SystemScheduleConfig.get_default_config()

    @staticmethod
    def save_schedule_config(config):
        """
        Guarda configuración de programación en base de datos.
        """
        try:
            from core.models import SystemScheduleConfig
            config_obj = SystemScheduleConfig.get_or_create_config()
            config_obj.save_config(config)

            logger.info('Schedule configuration updated in database', extra={'config': config})
            return True
        except Exception as e:
            logger.error(f'Error saving schedule config to DB: {e}')
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