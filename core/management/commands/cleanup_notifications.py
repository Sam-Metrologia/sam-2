"""
Comando para limpiar notificaciones antiguas del sistema.
Elimina notificaciones leídas de más de 7 días y descartadas de más de 1 día.

Uso:
    python manage.py cleanup_notifications
    python manage.py cleanup_notifications --dry-run
    python manage.py cleanup_notifications --days-read 3 --days-dismissed 1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import NotificacionZip
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpia notificaciones antiguas del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se eliminaría sin eliminarlo realmente'
        )
        parser.add_argument(
            '--days-read',
            type=int,
            default=7,
            help='Días después de los cuales eliminar notificaciones leídas (default: 7)'
        )
        parser.add_argument(
            '--days-dismissed',
            type=int,
            default=1,
            help='Días después de los cuales eliminar notificaciones descartadas (default: 1)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_read = options['days_read']
        days_dismissed = options['days_dismissed']

        self.stdout.write(
            self.style.SUCCESS(f'[INICIO] Limpieza de notificaciones (dry-run: {dry_run})')
        )

        # Fechas límite
        read_cutoff = timezone.now() - timedelta(days=days_read)
        dismissed_cutoff = timezone.now() - timedelta(days=days_dismissed)

        # Notificaciones leídas antiguas
        old_read = NotificacionZip.objects.filter(
            status='read',
            read_at__lt=read_cutoff
        )

        # Notificaciones descartadas antiguas
        old_dismissed = NotificacionZip.objects.filter(
            status='dismissed',
            created_at__lt=dismissed_cutoff
        )

        read_count = old_read.count()
        dismissed_count = old_dismissed.count()
        total_count = read_count + dismissed_count

        if dry_run:
            self.stdout.write(f'[DRY-RUN] Se eliminarían:')
            self.stdout.write(f'  - {read_count} notificaciones leídas (>{days_read} días)')
            self.stdout.write(f'  - {dismissed_count} notificaciones descartadas (>{days_dismissed} días)')
            self.stdout.write(f'  - Total: {total_count} notificaciones')

            # Mostrar ejemplos
            if read_count > 0:
                self.stdout.write(f'[EJEMPLOS LEÍDAS]')
                for notif in old_read[:3]:
                    self.stdout.write(f'  - ID {notif.id}: {notif.titulo} (leída: {notif.read_at})')

            if dismissed_count > 0:
                self.stdout.write(f'[EJEMPLOS DESCARTADAS]')
                for notif in old_dismissed[:3]:
                    self.stdout.write(f'  - ID {notif.id}: {notif.titulo} (creada: {notif.created_at})')

        else:
            # Eliminar realmente
            if read_count > 0:
                old_read.delete()
                self.stdout.write(f'[ELIMINADAS] {read_count} notificaciones leídas')

            if dismissed_count > 0:
                old_dismissed.delete()
                self.stdout.write(f'[ELIMINADAS] {dismissed_count} notificaciones descartadas')

            self.stdout.write(
                self.style.SUCCESS(f'[COMPLETADO] {total_count} notificaciones eliminadas')
            )

            logger.info(f"Limpieza de notificaciones: {total_count} eliminadas (read: {read_count}, dismissed: {dismissed_count})")

        # Estadísticas restantes
        remaining = NotificacionZip.objects.count()
        unread = NotificacionZip.objects.filter(status='unread').count()

        self.stdout.write(f'[ESTADÍSTICAS] Restantes: {remaining} total, {unread} no leídas')