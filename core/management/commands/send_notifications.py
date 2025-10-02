# core/management/commands/send_notifications.py
# Comando para enviar notificaciones automáticas

from django.core.management.base import BaseCommand
from django.conf import settings
from core.notifications import NotificationScheduler
import logging

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Envía notificaciones automáticas consolidadas (calibraciones, mantenimientos y comprobaciones)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['consolidated', 'calibration', 'maintenance', 'comprobacion', 'weekly', 'weekly_overdue', 'all'],
            default='consolidated',
            help='Tipo de notificaciones a enviar (consolidated es recomendado - incluye calibraciones, mantenimientos y comprobaciones en UN email)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular envío sin enviar emails reales'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACION - No se enviaran emails reales')
            )

        notification_type = options['type']
        verbose = options['verbose']

        total_sent = 0

        try:
            # Verificar configuración de email
            if not self._check_email_config():
                self.stdout.write(
                    self.style.ERROR('Configuracion de email no valida. Verificar settings.')
                )
                return

            if notification_type in ['consolidated', 'all']:
                self.stdout.write('Enviando recordatorios consolidados (calibraciones, mantenimientos, comprobaciones)...')
                if not options['dry_run']:
                    sent = NotificationScheduler.check_all_reminders()
                    total_sent += sent
                    self.stdout.write(
                        self.style.SUCCESS(f'Recordatorios consolidados enviados: {sent}')
                    )
                else:
                    self.stdout.write('   [SIMULADO] Recordatorios consolidados')

            if notification_type in ['calibration', 'all']:
                self.stdout.write('Enviando recordatorios individuales de calibracion...')
                if not options['dry_run']:
                    sent = NotificationScheduler.check_calibration_reminders()
                    total_sent += sent
                    self.stdout.write(
                        self.style.SUCCESS(f'Recordatorios de calibracion enviados: {sent}')
                    )
                else:
                    self.stdout.write('   [SIMULADO] Recordatorios de calibracion')

            if notification_type in ['maintenance', 'all']:
                self.stdout.write('Enviando recordatorios individuales de mantenimiento...')
                if not options['dry_run']:
                    sent = NotificationScheduler.check_maintenance_reminders()
                    total_sent += sent
                    self.stdout.write(
                        self.style.SUCCESS(f'Recordatorios de mantenimiento enviados: {sent}')
                    )
                else:
                    self.stdout.write('   [SIMULADO] Recordatorios de mantenimiento')

            if notification_type in ['comprobacion', 'all']:
                self.stdout.write('Enviando recordatorios individuales de comprobacion...')
                if not options['dry_run']:
                    # Nota: Las comprobaciones ya están incluidas en el sistema consolidado
                    # Para mantener compatibilidad, redirigimos al sistema consolidado
                    self.stdout.write('Las comprobaciones se envian a traves del sistema consolidado')
                    sent = 0
                    total_sent += sent
                    self.stdout.write(
                        self.style.SUCCESS(f'Use --type consolidated para incluir comprobaciones: {sent}')
                    )
                else:
                    self.stdout.write('   [SIMULADO] Recordatorios de comprobacion')

            if notification_type in ['weekly', 'all']:
                self.stdout.write('Enviando resumenes semanales...')
                if not options['dry_run']:
                    sent = NotificationScheduler.send_weekly_summaries()
                    total_sent += sent
                    self.stdout.write(
                        self.style.SUCCESS(f'Resumenes semanales enviados: {sent}')
                    )
                else:
                    self.stdout.write('   [SIMULADO] Resumenes semanales')

            if notification_type in ['weekly_overdue', 'all']:
                self.stdout.write('Enviando recordatorios semanales de equipos vencidos...')
                if not options['dry_run']:
                    sent = NotificationScheduler.send_weekly_overdue_reminders()
                    total_sent += sent
                    self.stdout.write(
                        self.style.SUCCESS(f'Recordatorios semanales vencidos enviados: {sent}')
                    )
                else:
                    self.stdout.write('   [SIMULADO] Recordatorios semanales vencidos')

            if not options['dry_run']:
                self.stdout.write(
                    self.style.SUCCESS(f'Total de notificaciones enviadas: {total_sent}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Simulacion completada. Para enviar reales, quitar --dry-run')
                )

        except Exception as e:
            logger.error(f'Error in notification command: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error al enviar notificaciones: {e}')
            )

    def _check_email_config(self):
        """Verifica que la configuración de email esté correcta."""
        try:
            # Verificar configuraciones básicas
            email_backend = getattr(settings, 'EMAIL_BACKEND', None)
            default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)

            if not email_backend:
                self.stdout.write(self.style.ERROR('EMAIL_BACKEND no configurado'))
                return False

            if not default_from_email:
                self.stdout.write(self.style.ERROR('DEFAULT_FROM_EMAIL no configurado'))
                return False

            # Si es SMTP, verificar configuraciones adicionales
            if 'smtp' in email_backend.lower():
                email_host = getattr(settings, 'EMAIL_HOST', None)
                if not email_host:
                    self.stdout.write(self.style.ERROR('EMAIL_HOST no configurado para SMTP'))
                    return False

            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error verificando configuración: {e}'))
            return False