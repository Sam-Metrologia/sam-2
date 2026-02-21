"""
Comando para verificar y procesar trials de empresas vencidos.
Incluye eliminación permanente de trials expirados después de 15 días de gracia.

Uso:
    python manage.py check_trial_expiration

Para ejecutar como tarea programada (cron/task scheduler):
    # Ejecutar diariamente a las 9:00 AM
    0 9 * * * cd /path/to/project && python manage.py check_trial_expiration
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import mail_admins
from django.db import models
from core.models import Empresa
import logging

logger = logging.getLogger(__name__)

# Días de gracia después de expiración del trial antes de eliminar datos
TRIAL_RETENCION_DIAS = 15


class Command(BaseCommand):
    help = 'Verifica y procesa trials de empresas vencidos (incluye cleanup 15 días)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué empresas serían afectadas sin hacer cambios'
        )
        parser.add_argument(
            '--notify-admins',
            action='store_true',
            help='Enviar email a administradores con resumen de acciones'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        notify_admins = options['notify_admins']

        self.stdout.write(
            self.style.SUCCESS('[INICIO] Verificando trials de empresas...')
        )

        # Estadísticas
        stats = {
            'checked': 0,
            'expired': 0,
            'warned': 0,
            'suspended': 0,
            'deleted': 0,
            'errors': 0
        }

        # Buscar empresas que tengan algún plan configurado (trial o pagado)
        empresas_con_plan = Empresa.objects.filter(
            models.Q(es_periodo_prueba=True) |
            models.Q(fecha_inicio_plan__isnull=False),
            is_deleted=False,
        ).distinct()

        stats['checked'] = empresas_con_plan.count()
        self.stdout.write(f'[INFO] Encontradas {stats["checked"]} empresas con planes configurados')

        # Procesar cada empresa
        for empresa in empresas_con_plan:
            try:
                self.process_company_trial(empresa, dry_run, stats)
            except Exception as e:
                stats['errors'] += 1
                error_msg = f'Error procesando empresa {empresa.nombre}: {e}'
                self.stdout.write(self.style.ERROR(f'[ERROR] {error_msg}'))
                logger.error(error_msg, exc_info=True)

        # Cleanup: eliminar trials expirados > 15 días
        self.cleanup_expired_trials(dry_run, stats)

        # Mostrar resumen
        self.show_summary(stats, dry_run)

        # Notificar administradores si se solicita
        if notify_admins and not dry_run:
            self.notify_administrators(stats)

    def process_company_trial(self, empresa, dry_run, stats):
        """Procesa el trial y planes de una empresa específica."""
        try:
            if not dry_run:
                # Usar el método de verificación automática
                cambio_realizado = empresa.verificar_y_procesar_expiraciones()
                if cambio_realizado:
                    stats['expired'] += 1
                    plan_actual = empresa.get_plan_actual()
                    self.stdout.write(
                        self.style.WARNING(f'[PROCESADO] {empresa.nombre} - Transicionado a plan {plan_actual}')
                    )
            else:
                # Modo dry-run: solo simular
                estado_plan = empresa.get_estado_suscripcion_display()

                if estado_plan in ["Plan Expirado", "Período de Prueba Expirado"]:
                    if empresa.limite_equipos_empresa != empresa.PLAN_GRATUITO_EQUIPOS:
                        stats['expired'] += 1
                        self.stdout.write(
                            self.style.WARNING(f'[DRY-RUN] {empresa.nombre} - {estado_plan}, sería transicionado')
                        )

            # Verificar avisos de expiración próxima
            dias_restantes = empresa.get_dias_restantes_plan()
            if isinstance(dias_restantes, int) and 0 < dias_restantes <= 2:
                stats['warned'] += 1

                if not dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'[AVISO] {empresa.nombre} - {dias_restantes} días restantes')
                    )
                    logger.info(f'Aviso de expiración para empresa {empresa.nombre} ({dias_restantes} días)')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'[DRY-RUN] {empresa.nombre} - {dias_restantes} días restantes')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error procesando empresa {empresa.nombre}: {str(e)}')
            )
            logger.error(f'Error procesando empresa {empresa.nombre}: {str(e)}', exc_info=True)

    def cleanup_expired_trials(self, dry_run, stats):
        """
        Elimina permanentemente empresas de trial expiradas hace más de 15 días.
        Solo aplica a empresas que fueron creadas como trial (es_periodo_prueba=True
        o que ya fueron marcadas como expiradas tras un trial).
        """
        hoy = timezone.localdate()

        # Buscar empresas trial con fecha de inicio de plan
        # cuyo trial expiró hace más de TRIAL_RETENCION_DIAS días
        empresas_trial = Empresa.objects.filter(
            is_deleted=False,
            fecha_inicio_plan__isnull=False,
            duracion_prueba_dias__gt=0,
        )

        for empresa in empresas_trial:
            try:
                fecha_fin_trial = empresa.fecha_inicio_plan + timedelta(
                    days=empresa.duracion_prueba_dias
                )
                dias_desde_expiracion = (hoy - fecha_fin_trial).days

                # Solo eliminar si:
                # 1. El trial ya expiró
                # 2. Han pasado más de 15 días desde la expiración
                # 3. La empresa NO tiene un plan pagado activo
                if (dias_desde_expiracion > TRIAL_RETENCION_DIAS
                        and empresa.get_plan_actual() != 'paid'):

                    if dry_run:
                        self.stdout.write(
                            self.style.ERROR(
                                f'[DRY-RUN DELETE] {empresa.nombre} - Trial expirado hace '
                                f'{dias_desde_expiracion} días (>{TRIAL_RETENCION_DIAS}d retención)'
                            )
                        )
                    else:
                        nombre = empresa.nombre
                        empresa.delete()
                        stats['deleted'] += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'[ELIMINADA] {nombre} - Trial expirado hace '
                                f'{dias_desde_expiracion} días'
                            )
                        )
                        logger.warning(
                            f'Empresa trial eliminada permanentemente: {nombre} '
                            f'({dias_desde_expiracion} días post-expiración)'
                        )

            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Cleanup empresa {empresa.nombre}: {str(e)}')
                )

    def show_summary(self, stats, dry_run):
        """Muestra resumen de acciones realizadas."""
        mode = "DRY-RUN" if dry_run else "EJECUTADO"

        self.stdout.write(f'\n[RESUMEN {mode}]')
        self.stdout.write(f'- Empresas verificadas: {stats["checked"]}')
        self.stdout.write(f'- Trials expirados: {stats["expired"]}')
        self.stdout.write(f'- Avisos enviados: {stats["warned"]}')
        self.stdout.write(f'- Trials eliminados (>{TRIAL_RETENCION_DIAS}d): {stats["deleted"]}')
        self.stdout.write(f'- Errores: {stats["errors"]}')

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\nEjecute sin --dry-run para aplicar los cambios')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nProceso completado exitosamente')
            )

    def notify_administrators(self, stats):
        """Envía notificación por email a administradores."""
        if stats['expired'] > 0 or stats['warned'] > 0 or stats['deleted'] > 0:
            subject = 'SAM Metrología - Reporte de Trials'
            message = f"""
Reporte automático del sistema de trials:

- Empresas verificadas: {stats['checked']}
- Trials expirados hoy: {stats['expired']}
- Avisos de expiración enviados: {stats['warned']}
- Trials eliminados (retención {TRIAL_RETENCION_DIAS}d): {stats['deleted']}
- Errores encontrados: {stats['errors']}

Este es un reporte automático del sistema SAM Metrología.
            """

            try:
                mail_admins(subject, message)
                self.stdout.write('[EMAIL] Notificación enviada a administradores')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[EMAIL ERROR] No se pudo enviar notificación: {e}')
                )
