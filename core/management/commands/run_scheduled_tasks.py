# core/management/commands/run_scheduled_tasks.py
# Comando para ejecutar tareas programadas

from django.core.management.base import BaseCommand
from core.admin_services import ScheduleManager
import logging

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Ejecuta tareas programadas según la configuración del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Solo verificar qué tareas deberían ejecutarse sin ejecutarlas'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar ejecución de todas las tareas habilitadas'
        )

    def handle(self, *args, **options):
        check_only = options['check_only']
        force = options['force']

        try:
            if force:
                self.stdout.write('🚀 Forzando ejecución de todas las tareas habilitadas...')
                result = self.force_all_tasks()
            else:
                self.stdout.write('⏰ Verificando tareas programadas...')
                result = ScheduleManager.check_scheduled_tasks()

            if result['success']:
                executed_tasks = result.get('executed_tasks', [])

                if executed_tasks:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Tareas ejecutadas: {len(executed_tasks)}')
                    )
                    for task in executed_tasks:
                        self.stdout.write(f'   - {task}')
                else:
                    if check_only:
                        self.stdout.write('ℹ️ No hay tareas programadas para ejecutar en este momento')
                    else:
                        self.stdout.write('✅ Verificación completada - No hay tareas pendientes')

            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error: {result.get("error", "Error desconocido")}')
                )

            # Log de la ejecución
            logger.info(f'Scheduled tasks check completed', extra=result)

        except Exception as e:
            logger.error(f'Error in scheduled tasks command: {e}')
            self.stdout.write(
                self.style.ERROR(f'❌ Error ejecutando tareas programadas: {e}')
            )

    def force_all_tasks(self):
        """Fuerza la ejecución de todas las tareas habilitadas."""
        from core.admin_services import AdminService

        config = ScheduleManager.get_schedule_config()
        executed_tasks = []
        errors = []

        try:
            # Forzar mantenimiento diario si está habilitado
            if config['maintenance_daily']['enabled']:
                result = AdminService.execute_maintenance(
                    task_type=','.join(config['maintenance_daily']['tasks'])
                )
                if result['success']:
                    executed_tasks.append('maintenance_daily_forced')
                else:
                    errors.append(f"maintenance_daily: {result.get('error', 'Unknown error')}")

            # Forzar notificaciones diarias si está habilitado
            if config['notifications_daily']['enabled']:
                result = AdminService.execute_notifications(
                    notification_type=','.join(config['notifications_daily']['types'])
                )
                if result['success']:
                    executed_tasks.append('notifications_daily_forced')
                else:
                    errors.append(f"notifications_daily: {result.get('error', 'Unknown error')}")

            # Forzar mantenimiento semanal si está habilitado
            if config['maintenance_weekly']['enabled']:
                result = AdminService.execute_maintenance(
                    task_type=','.join(config['maintenance_weekly']['tasks'])
                )
                if result['success']:
                    executed_tasks.append('maintenance_weekly_forced')
                else:
                    errors.append(f"maintenance_weekly: {result.get('error', 'Unknown error')}")

            # Forzar notificaciones semanales si está habilitado
            if config['notifications_weekly']['enabled']:
                result = AdminService.execute_notifications(
                    notification_type=','.join(config['notifications_weekly']['types'])
                )
                if result['success']:
                    executed_tasks.append('notifications_weekly_forced')
                else:
                    errors.append(f"notifications_weekly: {result.get('error', 'Unknown error')}")

            # Forzar backup mensual si está habilitado
            if config['backup_monthly']['enabled']:
                result = AdminService.execute_backup(
                    include_files=config['backup_monthly']['include_files']
                )
                if result['success']:
                    executed_tasks.append('backup_monthly_forced')
                else:
                    errors.append(f"backup_monthly: {result.get('error', 'Unknown error')}")

            return {
                'success': len(errors) == 0,
                'executed_tasks': executed_tasks,
                'errors': errors if errors else None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'executed_tasks': executed_tasks
            }