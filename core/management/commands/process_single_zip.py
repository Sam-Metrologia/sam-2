"""
Comando para procesar UNA SOLA solicitud ZIP.
Diseñado específicamente para Render y entornos con limitaciones de procesos background.

Este comando procesa solo la próxima solicitud en cola y termina,
permitiendo que sea llamado periódicamente o bajo demanda.

Uso:
    python manage.py process_single_zip
    python manage.py process_single_zip --cleanup-expired
"""

import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.storage import default_storage
from django.http import HttpRequest
from django.contrib.auth import get_user_model
from core.models import ZipRequest
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa UNA solicitud ZIP (ideal para Render)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup-expired',
            action='store_true',
            help='Limpiar solicitudes expiradas antes de procesar'
        )

    def handle(self, *args, **options):
        cleanup_expired = options['cleanup_expired']

        self.stdout.write('[RENDER-ZIP] Iniciando procesamiento de una solicitud')

        # Limpiar expiradas si se solicita
        if cleanup_expired:
            self.cleanup_expired_requests()

        # Buscar próxima solicitud pendiente
        next_request = ZipRequest.objects.filter(
            status='pending'
        ).order_by('position_in_queue').first()

        if next_request:
            self.stdout.write(f'[PROCESANDO] Solicitud #{next_request.id} de {next_request.user.username}')
            success = self.process_zip_request(next_request)

            if success:
                self.stdout.write('[ÉXITO] Solicitud procesada correctamente')
                return
            else:
                self.stdout.write('[ERROR] Error procesando solicitud')
                return
        else:
            self.stdout.write('[COLA-VACÍA] No hay solicitudes pendientes')
            return

    def process_zip_request(self, zip_request):
        """Procesa una solicitud ZIP específica."""
        try:
            # Importar aquí para evitar problemas de circular imports
            from core.management.commands.process_zip_queue import Command as QueueCommand

            # Crear instancia del comando original y usar su método
            queue_command = QueueCommand()
            queue_command.stdout = self.stdout

            # Procesar la solicitud
            queue_command.process_zip_request(zip_request)
            return True

        except Exception as e:
            self.stdout.write(f'[ERROR] Error procesando solicitud {zip_request.id}: {e}')
            logger.error(f'Error en process_single_zip para solicitud {zip_request.id}: {e}', exc_info=True)
            return False

    def cleanup_expired_requests(self):
        """Limpia solicitudes expiradas (versión rápida)."""
        self.stdout.write('[LIMPIEZA] Limpiando solicitudes expiradas...')

        expired_requests = ZipRequest.objects.filter(
            status='completed',
            expires_at__lt=timezone.now()
        )

        count = 0
        for req in expired_requests[:10]:  # Limitar a 10 para no usar mucho tiempo
            if req.file_path and default_storage.exists(req.file_path):
                try:
                    default_storage.delete(req.file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting expired file {req.file_path}: {e}")

            req.status = 'expired'
            req.file_path = None
            req.save()

        self.stdout.write(f'[LIMPIEZA] Procesadas {count} solicitudes expiradas')