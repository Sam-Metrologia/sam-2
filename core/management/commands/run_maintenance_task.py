# core/management/commands/run_maintenance_task.py
"""
Comando para ejecutar tareas de mantenimiento programadas.
Diseñado para ser llamado desde la interfaz web.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.cache import cache
from django.core.management import call_command
from core.models import MaintenanceTask, CommandLog, Empresa, Equipo, CustomUser
import time
import io
import sys
from pathlib import Path
import shutil
from datetime import datetime


class Command(BaseCommand):
    help = 'Ejecuta una tarea de mantenimiento específica'

    def add_arguments(self, parser):
        parser.add_argument(
            'task_id',
            type=int,
            help='ID de la tarea a ejecutar'
        )

    def handle(self, *args, **options):
        task_id = options['task_id']

        try:
            task = MaintenanceTask.objects.get(id=task_id)
        except MaintenanceTask.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Tarea {task_id} no encontrada'))
            return

        # Verificar que la tarea esté pendiente
        if task.status != 'pending':
            self.stdout.write(self.style.WARNING(f'Tarea {task_id} ya fue ejecutada (estado: {task.status})'))
            return

        # Marcar como en ejecución
        task.status = 'running'
        task.started_at = timezone.now()
        task.save()

        self.log_message(task, 'INFO', f'Iniciando tarea: {task.get_task_type_display()}')

        # Capturar output
        output_buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        start_time = time.time()
        success = False

        try:
            # Ejecutar tarea según tipo
            if task.task_type == 'backup_db':
                success = self.backup_database(task)
            elif task.task_type == 'clear_cache':
                success = self.clear_cache(task)
            elif task.task_type == 'cleanup_files':
                success = self.cleanup_files(task)
            elif task.task_type == 'run_tests':
                success = self.run_tests(task)
            elif task.task_type == 'check_system':
                success = self.check_system(task)
            elif task.task_type == 'optimize_db':
                success = self.optimize_database(task)
            elif task.task_type == 'collect_static':
                success = self.collect_static(task)
            elif task.task_type == 'migrate_db':
                success = self.migrate_database(task)
            elif task.task_type == 'custom':
                success = self.run_custom_command(task)
            else:
                self.log_message(task, 'ERROR', f'Tipo de tarea desconocido: {task.task_type}')
                success = False

        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en ejecución: {str(e)}')
            task.error_message = str(e)
            success = False

        finally:
            # Restaurar stdout
            sys.stdout = old_stdout
            output = output_buffer.getvalue()
            output_buffer.close()

            # Calcular duración
            duration = time.time() - start_time

            # Actualizar tarea
            task.completed_at = timezone.now()
            task.duration_seconds = duration
            task.output = output[:10000]  # Limitar a 10KB
            task.status = 'completed' if success else 'failed'
            task.save()

            self.log_message(
                task,
                'INFO',
                f'Tarea finalizada en {duration:.2f}s - Estado: {task.status}'
            )

            # Output para terminal
            if success:
                self.stdout.write(self.style.SUCCESS(f'Tarea {task_id} completada exitosamente'))
            else:
                self.stdout.write(self.style.ERROR(f'Tarea {task_id} falló'))

    def log_message(self, task, level, message):
        """Registra mensaje en CommandLog"""
        CommandLog.objects.create(
            task=task,
            level=level,
            message=message
        )
        print(f"[{level}] {message}")

    def backup_database(self, task):
        """Crea backup de la base de datos"""
        try:
            self.log_message(task, 'INFO', 'Iniciando backup de base de datos...')

            BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
            db_file = BASE_DIR / 'db.sqlite3'

            if not db_file.exists():
                self.log_message(task, 'ERROR', 'Archivo de base de datos no encontrado')
                return False

            backup_dir = BASE_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'db_backup_{timestamp}.sqlite3'

            shutil.copy2(db_file, backup_file)

            size_mb = backup_file.stat().st_size / (1024 * 1024)
            self.log_message(task, 'INFO', f'Backup creado: {backup_file.name} ({size_mb:.2f} MB)')

            # Limpiar backups antiguos (mantener últimos 10)
            backups = sorted(backup_dir.glob('db_backup_*.sqlite3'), reverse=True)
            for old_backup in backups[10:]:
                old_backup.unlink()
                self.log_message(task, 'INFO', f'Backup antiguo eliminado: {old_backup.name}')

            return True

        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en backup: {str(e)}')
            return False

    def clear_cache(self, task):
        """Limpia el cache del sistema"""
        try:
            self.log_message(task, 'INFO', 'Limpiando cache...')
            cache.clear()
            self.log_message(task, 'INFO', 'Cache limpiado exitosamente')
            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error al limpiar cache: {str(e)}')
            return False

    def cleanup_files(self, task):
        """Limpia archivos temporales"""
        try:
            self.log_message(task, 'INFO', 'Limpiando archivos temporales...')

            # Limpiar ZIPs antiguos
            call_command('cleanup_zip_files', '--older-than-hours', '6')
            self.log_message(task, 'INFO', 'Archivos ZIP antiguos eliminados')

            # Limpiar notificaciones antiguas
            try:
                call_command('cleanup_notifications', '--days', '30')
                self.log_message(task, 'INFO', 'Notificaciones antiguas limpiadas')
            except Exception:
                pass

            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en limpieza: {str(e)}')
            return False

    def run_tests(self, task):
        """Ejecuta tests del sistema"""
        try:
            self.log_message(task, 'INFO', 'Ejecutando tests...')
            self.log_message(task, 'WARNING', 'Sistema de tests no configurado aún')
            # TODO: Implementar cuando pytest esté configurado
            # call_command('test')
            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en tests: {str(e)}')
            return False

    def check_system(self, task):
        """Verifica el estado del sistema"""
        try:
            self.log_message(task, 'INFO', 'Verificando estado del sistema...')

            # Contar registros
            total_empresas = Empresa.objects.filter(is_deleted=False).count()
            total_equipos = Equipo.objects.count()
            total_usuarios = CustomUser.objects.count()

            self.log_message(task, 'INFO', f'Empresas activas: {total_empresas}')
            self.log_message(task, 'INFO', f'Equipos registrados: {total_equipos}')
            self.log_message(task, 'INFO', f'Usuarios totales: {total_usuarios}')

            # Test de cache
            try:
                test_key = f'health_check_{timezone.now().timestamp()}'
                cache.set(test_key, 'OK', 60)
                if cache.get(test_key) == 'OK':
                    self.log_message(task, 'INFO', 'Cache: FUNCIONANDO')
                else:
                    self.log_message(task, 'WARNING', 'Cache: NO FUNCIONA')
            except Exception as e:
                self.log_message(task, 'WARNING', f'Cache: ERROR - {str(e)}')

            # Test de base de datos
            try:
                start = time.time()
                Empresa.objects.first()
                db_time = (time.time() - start) * 1000
                self.log_message(task, 'INFO', f'Base de datos: OK ({db_time:.2f}ms)')
            except Exception as e:
                self.log_message(task, 'ERROR', f'Base de datos: ERROR - {str(e)}')
                return False

            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en verificación: {str(e)}')
            return False

    def optimize_database(self, task):
        """Optimiza la base de datos"""
        try:
            self.log_message(task, 'INFO', 'Optimizando base de datos...')
            self.log_message(task, 'INFO', 'Nota: SQLite se optimiza automáticamente')
            # Para SQLite no hay mucho que optimizar manualmente
            # En PostgreSQL usaríamos VACUUM, ANALYZE, etc.
            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en optimización: {str(e)}')
            return False

    def collect_static(self, task):
        """Recolecta archivos estáticos"""
        try:
            self.log_message(task, 'INFO', 'Recolectando archivos estáticos...')
            call_command('collectstatic', '--noinput', '--clear')
            self.log_message(task, 'INFO', 'Archivos estáticos recolectados')
            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error recolectando estáticos: {str(e)}')
            return False

    def migrate_database(self, task):
        """Aplica migraciones pendientes"""
        try:
            self.log_message(task, 'INFO', 'Aplicando migraciones...')
            call_command('migrate', '--noinput')
            self.log_message(task, 'INFO', 'Migraciones aplicadas')
            return True
        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en migraciones: {str(e)}')
            return False

    def run_custom_command(self, task):
        """Ejecuta comando personalizado (solo para superusuarios)"""
        try:
            if not task.command:
                self.log_message(task, 'ERROR', 'No se especificó comando personalizado')
                return False

            self.log_message(task, 'WARNING', f'Ejecutando comando: {task.command}')
            self.log_message(task, 'ERROR', 'Comandos personalizados deshabilitados por seguridad')
            return False

            # TODO: Implementar con validación estricta de seguridad
            # Solo permitir comandos de Django manage.py

        except Exception as e:
            self.log_message(task, 'ERROR', f'Error en comando personalizado: {str(e)}')
            return False
