# core/management/commands/maintenance.py
# Comando de mantenimiento automático del sistema

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import connection, transaction
from core.models import Empresa, Equipo, ZipRequest
from datetime import timedelta
import os
import logging

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Ejecuta tareas de mantenimiento automático del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['cache', 'logs', 'files', 'database', 'zip', 'backups', 'all'],
            default='all',
            help='Tipo de mantenimiento a ejecutar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular ejecución sin hacer cambios reales'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACION - No se haran cambios reales')
            )

        task_type = options['task']
        verbose = options['verbose']
        dry_run = options['dry_run']

        total_cleaned = 0

        try:
            if task_type in ['cache', 'all']:
                cleaned = self.clean_cache(dry_run, verbose)
                total_cleaned += cleaned

            if task_type in ['logs', 'all']:
                cleaned = self.clean_logs(dry_run, verbose)
                total_cleaned += cleaned

            if task_type in ['files', 'all']:
                cleaned = self.clean_orphaned_files(dry_run, verbose)
                total_cleaned += cleaned

            if task_type in ['database', 'all']:
                cleaned = self.optimize_database(dry_run, verbose)
                total_cleaned += cleaned

            if task_type in ['zip', 'all']:
                cleaned = self.clean_zip_files(dry_run, verbose)
                total_cleaned += cleaned

            if task_type in ['backups', 'all']:
                cleaned = self.clean_old_backups(dry_run, verbose)
                total_cleaned += cleaned

            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'Mantenimiento completado. Items procesados: {total_cleaned}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Simulacion completada. Para ejecutar real, quitar --dry-run')
                )

        except Exception as e:
            logger.error(f'Error in maintenance command: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error durante mantenimiento: {e}')
            )

    def clean_cache(self, dry_run=False, verbose=False):
        """Limpia entradas obsoletas del cache."""
        self.stdout.write('Limpiando cache obsoleto...')

        if verbose:
            self.stdout.write('   - Verificando conexión de cache...')

        try:
            # Limpiar cache de storage antiguo (versiones v1 y v2)
            cleaned = 0

            if not dry_run:
                # Obtener todas las empresas para limpiar su cache obsoleto
                empresas = Empresa.objects.all()
                for empresa in empresas:
                    # Limpiar versiones antiguas del cache de storage
                    old_keys = [
                        f"storage_usage_empresa_{empresa.id}_v1",
                        f"storage_usage_empresa_{empresa.id}_v2"
                    ]
                    for key in old_keys:
                        if cache.get(key) is not None:
                            cache.delete(key)
                            cleaned += 1

            if verbose:
                self.stdout.write(f'   - Cache entries limpiadas: {cleaned}')

            self.stdout.write(
                self.style.SUCCESS(f'OK Cache limpiado: {cleaned} entradas')
            )
            return cleaned

        except Exception as e:
            logger.error(f'Error cleaning cache: {e}')
            self.stdout.write(
                self.style.ERROR(f'ERROR Error limpiando cache: {e}')
            )
            return 0

    def clean_logs(self, dry_run=False, verbose=False):
        """Limpia logs antiguos."""
        self.stdout.write('📄 Limpiando logs antiguos...')

        logs_dir = getattr(settings, 'LOGS_DIR', None)
        if not logs_dir:
            logs_dir = os.path.join(settings.BASE_DIR, 'logs')

        if not os.path.exists(logs_dir):
            self.stdout.write('   - No se encontró directorio de logs')
            return 0

        cleaned = 0
        cutoff_date = timezone.now() - timedelta(days=30)  # Mantener 30 días

        try:
            for filename in os.listdir(logs_dir):
                if filename.endswith('.log.1') or filename.endswith('.log.2'):
                    filepath = os.path.join(logs_dir, filename)

                    if os.path.isfile(filepath):
                        file_time = timezone.datetime.fromtimestamp(
                            os.path.getmtime(filepath), tz=timezone.get_current_timezone()
                        )

                        if file_time < cutoff_date:
                            if verbose:
                                self.stdout.write(f'   - Eliminando: {filename}')

                            if not dry_run:
                                os.remove(filepath)
                            cleaned += 1

            self.stdout.write(
                self.style.SUCCESS(f'OK Logs limpiados: {cleaned} archivos')
            )
            return cleaned

        except Exception as e:
            logger.error(f'Error cleaning logs: {e}')
            self.stdout.write(
                self.style.ERROR(f'ERROR Error limpiando logs: {e}')
            )
            return 0

    def clean_orphaned_files(self, dry_run=False, verbose=False):
        """Limpia archivos huérfanos que no tienen referencia en BD."""
        self.stdout.write('📁 Buscando archivos huérfanos...')

        if verbose:
            self.stdout.write('   - Esta operación puede tomar tiempo...')

        # Por ahora solo reportar, implementación completa requiere más análisis
        self.stdout.write(
            self.style.WARNING('⚠️ Limpieza de archivos huérfanos pendiente de implementación')
        )

        return 0

    def optimize_database(self, dry_run=False, verbose=False):
        """Optimiza la base de datos."""
        self.stdout.write('🗄️ Optimizando base de datos...')

        optimized = 0

        try:
            # Procesar expiraciones de empresas
            empresas_procesadas = 0
            if not dry_run:
                empresas = Empresa.objects.all()
                for empresa in empresas:
                    if empresa.verificar_y_procesar_expiraciones():
                        empresas_procesadas += 1

            if verbose:
                self.stdout.write(f'   - Empresas con expiraciones procesadas: {empresas_procesadas}')

            # Actualizar fechas próximas de equipos (solo si están desactualizadas)
            equipos_actualizados = 0
            if not dry_run:
                equipos = Equipo.objects.filter(
                    estado__in=['Activo', 'En Mantenimiento', 'En Calibración', 'En Comprobación']
                ).select_related('empresa')

                for equipo in equipos:
                    original_cal = equipo.proxima_calibracion
                    original_mant = equipo.proximo_mantenimiento
                    original_comp = equipo.proxima_comprobacion

                    equipo.calcular_proxima_calibracion()
                    equipo.calcular_proximo_mantenimiento()
                    equipo.calcular_proxima_comprobacion()

                    # Solo guardar si hay cambios
                    if (equipo.proxima_calibracion != original_cal or
                        equipo.proximo_mantenimiento != original_mant or
                        equipo.proxima_comprobacion != original_comp):

                        equipo.save(update_fields=[
                            'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'
                        ])
                        equipos_actualizados += 1

            if verbose:
                self.stdout.write(f'   - Equipos con fechas actualizadas: {equipos_actualizados}')

            optimized = empresas_procesadas + equipos_actualizados

            self.stdout.write(
                self.style.SUCCESS(f'OK Base de datos optimizada: {optimized} registros')
            )
            return optimized

        except Exception as e:
            logger.error(f'Error optimizing database: {e}')
            self.stdout.write(
                self.style.ERROR(f'ERROR Error optimizando BD: {e}')
            )
            return 0

    def clean_zip_files(self, dry_run=False, verbose=False):
        """Limpia archivos ZIP antiguos y requests expiradas."""
        self.stdout.write('🗜️ Limpiando sistema de archivos ZIP...')

        cleaned = 0

        try:
            # Limpiar requests ZIP antiguas
            cutoff_time = timezone.now() - timedelta(hours=24)

            old_requests = ZipRequest.objects.filter(
                created_at__lt=cutoff_time
            )

            if verbose:
                self.stdout.write(f'   - Encontradas {old_requests.count()} solicitudes antiguas')

            if not dry_run:
                cleaned = old_requests.count()
                old_requests.delete()

            self.stdout.write(
                self.style.SUCCESS(f'OK Sistema ZIP limpiado: {cleaned} solicitudes')
            )
            return cleaned

        except Exception as e:
            logger.error(f'Error cleaning ZIP system: {e}')
            self.stdout.write(
                self.style.ERROR(f'ERROR Error limpiando ZIP: {e}')
            )
            return 0

    def clean_old_backups(self, dry_run=False, verbose=False):
        """Limpia backups de S3 mayores a 6 meses."""
        self.stdout.write('💾 Limpiando backups antiguos de S3 (>6 meses)...')

        # Verificar si AWS está configurado
        if not all([
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            settings.AWS_STORAGE_BUCKET_NAME
        ]):
            self.stdout.write(
                self.style.WARNING('AWS S3 no configurado - Saltando limpieza de backups')
            )
            return 0

        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            self.stdout.write(
                self.style.WARNING('boto3 no instalado - Saltando limpieza de backups')
            )
            return 0

        cleaned = 0

        try:
            # Calcular fecha límite (6 meses)
            cutoff_date = timezone.now() - timedelta(days=180)

            # Conectar a S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-2')
            )

            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            backup_prefix = 'backups/'

            # Listar objetos en el bucket
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix=backup_prefix)

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    file_key = obj['Key']
                    last_modified = obj['LastModified']

                    # Verificar si es más antiguo que 6 meses
                    if last_modified < cutoff_date.replace(tzinfo=last_modified.tzinfo):
                        if verbose:
                            age_days = (timezone.now() - last_modified).days
                            self.stdout.write(
                                f'   - {"[SIMULAR]" if dry_run else "[ELIMINAR]"} {file_key} '
                                f'({age_days} días)'
                            )

                        if not dry_run:
                            s3_client.delete_object(Bucket=bucket_name, Key=file_key)
                            logger.info(f'Backup eliminado de S3: {file_key}')

                        cleaned += 1

            self.stdout.write(
                self.style.SUCCESS(f'OK Backups antiguos limpiados: {cleaned} archivos')
            )
            return cleaned

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f'S3 bucket does not exist: {settings.AWS_STORAGE_BUCKET_NAME}')
                self.stdout.write(
                    self.style.ERROR(f'ERROR Bucket S3 no existe')
                )
            elif error_code == 'AccessDenied':
                logger.error('Access denied to S3 - check IAM permissions')
                self.stdout.write(
                    self.style.ERROR(f'ERROR Acceso denegado a S3')
                )
            else:
                logger.error(f'S3 error cleaning backups: {e}')
                self.stdout.write(
                    self.style.ERROR(f'ERROR Error S3: {e}')
                )
            return 0

        except Exception as e:
            logger.error(f'Error cleaning old backups: {e}')
            self.stdout.write(
                self.style.ERROR(f'ERROR Error limpiando backups: {e}')
            )
            return 0