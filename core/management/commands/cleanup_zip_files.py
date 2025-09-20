"""
Comando para limpiar archivos ZIP expirados o antiguos.

Uso:
    python manage.py cleanup_zip_files
    python manage.py cleanup_zip_files --force-all  # Eliminar TODOS los ZIPs
    python manage.py cleanup_zip_files --older-than-hours 1  # Eliminar ZIPs de más de 1 hora
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.storage import default_storage
from core.models import ZipRequest
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpia archivos ZIP expirados y solicitudes antiguas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Eliminar TODOS los archivos ZIP sin importar su estado'
        )
        parser.add_argument(
            '--older-than-hours',
            type=int,
            default=6,
            help='Eliminar ZIPs más antiguos que X horas (default: 6)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se eliminaría sin eliminar realmente'
        )

    def handle(self, *args, **options):
        force_all = options['force_all']
        older_than_hours = options['older_than_hours']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write('[DRY RUN] Simulando limpieza - no se eliminará nada')

        if force_all:
            self.stdout.write('[FORZADO] Eliminando TODOS los archivos ZIP')
            self.cleanup_all_zips(dry_run)
        else:
            self.stdout.write(f'[LIMPIEZA] Eliminando ZIPs más antiguos que {older_than_hours} horas')
            self.cleanup_expired_zips(older_than_hours, dry_run)

        self.stdout.write('[COMPLETADO] Limpieza finalizada')

    def cleanup_all_zips(self, dry_run=False):
        """Elimina TODOS los archivos ZIP."""
        all_requests = ZipRequest.objects.all()

        total_deleted = 0
        total_size = 0

        for req in all_requests:
            if req.file_path and default_storage.exists(req.file_path):
                file_size = req.file_size or 0
                total_size += file_size

                if not dry_run:
                    try:
                        default_storage.delete(req.file_path)
                        req.file_path = None
                        req.status = 'expired'
                        req.save()
                        total_deleted += 1
                    except Exception as e:
                        logger.error(f"Error eliminando archivo {req.file_path}: {e}")
                else:
                    total_deleted += 1

                self.stdout.write(f'{"[SIMULADO] " if dry_run else ""}Eliminado: {req.file_path} ({file_size} bytes)')

        if not dry_run:
            # Eliminar solicitudes muy antiguas (más de 7 días)
            old_date = timezone.now() - timedelta(days=7)
            old_requests = ZipRequest.objects.filter(created_at__lt=old_date)
            old_count = old_requests.count()
            old_requests.delete()

            self.stdout.write(f'[LIMPIEZA] Eliminadas {old_count} solicitudes antiguas')

        self.stdout.write(f'[RESUMEN] {"Simularía eliminar" if dry_run else "Eliminados"} {total_deleted} archivos')
        self.stdout.write(f'[RESUMEN] Espacio liberado: {total_size / (1024*1024):.2f} MB')

    def cleanup_expired_zips(self, older_than_hours, dry_run=False):
        """Elimina ZIPs expirados o más antiguos que X horas."""
        cutoff_time = timezone.now() - timedelta(hours=older_than_hours)

        # Buscar solicitudes expiradas
        expired_requests = ZipRequest.objects.filter(
            status='completed',
            completed_at__lt=cutoff_time
        )

        # También buscar solicitudes que ya tienen expires_at y están expiradas
        naturally_expired = ZipRequest.objects.filter(
            status='completed',
            expires_at__lt=timezone.now()
        )

        # Combinar ambos querysets
        requests_to_clean = (expired_requests | naturally_expired).distinct()

        total_deleted = 0
        total_size = 0

        for req in requests_to_clean:
            if req.file_path and default_storage.exists(req.file_path):
                file_size = req.file_size or 0
                total_size += file_size

                if not dry_run:
                    try:
                        default_storage.delete(req.file_path)
                        req.file_path = None
                        req.status = 'expired'
                        req.save()
                        total_deleted += 1
                    except Exception as e:
                        logger.error(f"Error eliminando archivo {req.file_path}: {e}")
                else:
                    total_deleted += 1

                age_hours = (timezone.now() - req.completed_at).total_seconds() / 3600
                self.stdout.write(f'{"[SIMULADO] " if dry_run else ""}Eliminado: {req.file_path} (edad: {age_hours:.1f}h, {file_size} bytes)')

        self.stdout.write(f'[RESUMEN] {"Simularía eliminar" if dry_run else "Eliminados"} {total_deleted} archivos expirados')
        self.stdout.write(f'[RESUMEN] Espacio liberado: {total_size / (1024*1024):.2f} MB')