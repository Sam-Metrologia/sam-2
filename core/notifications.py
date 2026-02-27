# core/notifications.py
# Sistema de notificaciones por email para SAM Metrología

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from .models import Equipo, Empresa, CustomUser
import logging
from .constants import (
    ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_DE_BAJA,
    ESTADO_EN_CALIBRACION, ESTADO_EN_MANTENIMIENTO
)

logger = logging.getLogger('core')

def configure_email_settings():
    """Configura Django con la configuración de email activa."""
    try:
        from .models import EmailConfiguration
        config = EmailConfiguration.get_active_config()

        if config and config.is_active:
            # Aplicar configuración dinámicamente
            settings.EMAIL_BACKEND = config.email_backend
            settings.EMAIL_HOST = config.email_host
            settings.EMAIL_PORT = config.email_port
            settings.EMAIL_USE_TLS = config.email_use_tls
            settings.EMAIL_USE_SSL = config.email_use_ssl
            settings.EMAIL_HOST_USER = config.email_host_user
            settings.EMAIL_HOST_PASSWORD = config.email_host_password
            settings.DEFAULT_FROM_EMAIL = config.default_from_email

            logger.info(f'Email settings configured: {config.email_host} - {config.email_host_user}')
            return True
        else:
            logger.warning('No active email configuration found')
            return False
    except Exception as e:
        logger.error(f'Error configuring email settings: {e}')
        return False

class NotificationService:
    """
    Servicio centralizado para manejo de notificaciones por email.
    """

    @staticmethod
    def send_calibration_reminder(equipo, days_until_due, recipients=None):
        """
        Envía recordatorio de calibración próxima a vencer.

        Args:
            equipo: Instancia del equipo
            days_until_due: Días hasta que venza la calibración
            recipients: Lista de emails (opcional, por defecto usuarios de la empresa)
        """
        if not recipients:
            recipients = NotificationService._get_company_recipients(equipo.empresa)

        if not recipients:
            logger.warning(f"No recipients found for calibration reminder: {equipo.codigo_interno}")
            return False

        # Contexto para el template
        context = {
            'equipo': equipo,
            'empresa': equipo.empresa,
            'days_until_due': days_until_due,
            'due_date': equipo.proxima_calibracion,
            'urgency_level': NotificationService._get_urgency_level(days_until_due),
            'site_name': 'SAM Metrologia',
        }

        try:
            # Configurar email dinámicamente
            if not configure_email_settings():
                logger.error("Failed to configure email settings")
                return False

            # Renderizar templates de email
            subject = f"NOTIFICACION: Calibracion proxima a vencer - {equipo.nombre}"
            text_content = render_to_string('emails/calibration_reminder.txt', context)
            html_content = render_to_string('emails/calibration_reminder.html', context)

            # Crear email con versión HTML y texto
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Calibration reminder sent for {equipo.codigo_interno} to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send calibration reminder for {equipo.codigo_interno}: {e}")
            return False

    @staticmethod
    def send_maintenance_reminder(equipo, days_until_due, recipients=None):
        """
        Envía recordatorio de mantenimiento próximo a vencer.
        """
        if not recipients:
            recipients = NotificationService._get_company_recipients(equipo.empresa)

        if not recipients:
            return False

        context = {
            'equipo': equipo,
            'empresa': equipo.empresa,
            'days_until_due': days_until_due,
            'due_date': equipo.proximo_mantenimiento,
            'urgency_level': NotificationService._get_urgency_level(days_until_due),
            'site_name': 'SAM Metrologia',
        }

        try:
            # Configurar email dinámicamente
            if not configure_email_settings():
                logger.error("Failed to configure email settings")
                return False

            subject = f"NOTIFICACION: Mantenimiento proximo a vencer - {equipo.nombre}"
            text_content = render_to_string('emails/maintenance_reminder.txt', context)
            html_content = render_to_string('emails/maintenance_reminder.html', context)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Maintenance reminder sent for {equipo.codigo_interno} to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance reminder for {equipo.codigo_interno}: {e}")
            return False

    @staticmethod
    def send_weekly_summary(empresa, recipients=None):
        """
        Envía resumen semanal de actividades pendientes.
        """
        if not recipients:
            recipients = NotificationService._get_company_recipients(empresa)

        if not recipients:
            return False

        # Obtener equipos con actividades próximas a vencer
        today = timezone.localdate()
        next_week = today + timedelta(days=7)
        next_month = today + timedelta(days=30)

        equipos_calibracion_urgente = empresa.equipos.filter(
            proxima_calibracion__lte=next_week,
            proxima_calibracion__gt=today,
            estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
        ).order_by('proxima_calibracion')

        equipos_mantenimiento_urgente = empresa.equipos.filter(
            proximo_mantenimiento__lte=next_week,
            proximo_mantenimiento__gt=today,
            estado__in=['Activo', 'En Calibración', 'En Comprobación']
        ).order_by('proximo_mantenimiento')

        equipos_calibracion_proximo = empresa.equipos.filter(
            proxima_calibracion__lte=next_month,
            proxima_calibracion__gt=next_week,
            estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
        ).order_by('proxima_calibracion')

        equipos_mantenimiento_proximo = empresa.equipos.filter(
            proximo_mantenimiento__lte=next_month,
            proximo_mantenimiento__gt=next_week,
            estado__in=['Activo', 'En Calibración', 'En Comprobación']
        ).order_by('proximo_mantenimiento')

        context = {
            'empresa': empresa,
            'equipos_calibracion_urgente': equipos_calibracion_urgente,
            'equipos_mantenimiento_urgente': equipos_mantenimiento_urgente,
            'equipos_calibracion_proximo': equipos_calibracion_proximo,
            'equipos_mantenimiento_proximo': equipos_mantenimiento_proximo,
            'today': today,
            'site_name': 'SAM Metrologia',
        }

        try:
            # Configurar email dinámicamente
            if not configure_email_settings():
                logger.error("Failed to configure email settings for weekly summary")
                return False

            subject = f"RESUMEN SEMANAL - {empresa.nombre}"
            text_content = render_to_string('emails/weekly_summary.txt', context)
            html_content = render_to_string('emails/weekly_summary.html', context)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Weekly summary sent for {empresa.nombre} to {len(recipients)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send weekly summary for {empresa.nombre}: {e}")
            return False

    @staticmethod
    def _get_company_recipients(empresa):
        """
        Obtiene lista de emails de notificaciones de la empresa.
        Prioridad: correos_notificaciones (si configurado) → usuarios activos → email empresa.
        """
        recipients = []

        # 1. Usar correos_notificaciones si están configurados
        if empresa.correos_notificaciones:
            for email in empresa.correos_notificaciones.split(','):
                email = email.strip()
                if email:
                    recipients.append(email)

        # 2. Si no hay correos_notificaciones, usar usuarios activos con email
        if not recipients:
            users = CustomUser.objects.filter(
                empresa=empresa,
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            for user in users:
                if user.email:
                    recipients.append(user.email)

        # 3. Último recurso: email principal de la empresa
        if not recipients and empresa.email:
            recipients.append(empresa.email)

        return recipients

    @staticmethod
    def _get_urgency_level(days_until_due):
        """
        Determina el nivel de urgencia basado en días restantes.
        """
        if days_until_due <= 0:
            return 'critical'  # Vencido
        elif days_until_due <= 3:
            return 'high'      # Muy urgente
        elif days_until_due <= 7:
            return 'medium'    # Urgente
        elif days_until_due <= 15:
            return 'low'       # Próximo
        else:
            return 'info'      # Informativo


class NotificationScheduler:
    """
    Programador de notificaciones automáticas.
    """

    @staticmethod
    def send_consolidated_reminder(empresa, days_ahead):
        """
        Envía UN SOLO email consolidado con todas las actividades próximas a vencer Y vencidas.
        Incluye: calibraciones, mantenimientos y comprobaciones.
        Separa claramente actividades vencidas de próximas.
        """
        today = timezone.localdate()
        target_date = today + timedelta(days=days_ahead)

        # Obtener usuarios de la empresa
        recipients = NotificationService._get_company_recipients(empresa)
        if not recipients:
            logger.warning(f"No recipients found for consolidated reminder: {empresa.nombre}")
            return False

        # ACTIVIDADES PRÓXIMAS (futuras, no vencidas)
        equipos_calibracion_proximas = empresa.equipos.filter(
            proxima_calibracion__gte=today,  # Solo futuras
            proxima_calibracion__lte=target_date,
            estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
        ).select_related('empresa').order_by('proxima_calibracion')

        equipos_mantenimiento_proximos = empresa.equipos.filter(
            proximo_mantenimiento__gte=today,  # Solo futuras
            proximo_mantenimiento__lte=target_date,
            estado__in=['Activo', 'En Calibración', 'En Comprobación']
        ).select_related('empresa').order_by('proximo_mantenimiento')

        equipos_comprobacion_proximas = empresa.equipos.filter(
            proxima_comprobacion__gte=today,  # Solo futuras
            proxima_comprobacion__lte=target_date,
            estado__in=[ESTADO_ACTIVO, ESTADO_EN_CALIBRACION, 'En Mantenimiento']
        ).select_related('empresa').order_by('proxima_comprobacion')

        # ACTIVIDADES VENCIDAS (hasta 30 días atrás)
        equipos_calibracion_vencidas = empresa.equipos.filter(
            proxima_calibracion__lt=today,  # Vencidas
            proxima_calibracion__gte=today - timedelta(days=30),  # Máximo 30 días atrás
            estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
        ).select_related('empresa').order_by('proxima_calibracion')

        equipos_mantenimiento_vencidos = empresa.equipos.filter(
            proximo_mantenimiento__lt=today,  # Vencidos
            proximo_mantenimiento__gte=today - timedelta(days=30),  # Máximo 30 días atrás
            estado__in=['Activo', 'En Calibración', 'En Comprobación']
        ).select_related('empresa').order_by('proximo_mantenimiento')

        equipos_comprobacion_vencidas = empresa.equipos.filter(
            proxima_comprobacion__lt=today,  # Vencidas
            proxima_comprobacion__gte=today - timedelta(days=30),  # Máximo 30 días atrás
            estado__in=[ESTADO_ACTIVO, ESTADO_EN_CALIBRACION, 'En Mantenimiento']
        ).select_related('empresa').order_by('proxima_comprobacion')

        # Contar totales
        total_proximas = (equipos_calibracion_proximas.count() +
                         equipos_mantenimiento_proximos.count() +
                         equipos_comprobacion_proximas.count())

        total_vencidas = (equipos_calibracion_vencidas.count() +
                         equipos_mantenimiento_vencidos.count() +
                         equipos_comprobacion_vencidas.count())

        total_actividades = total_proximas + total_vencidas

        # Solo enviar si hay actividades que notificar
        if total_actividades == 0:
            logger.info(f"No activities due in {days_ahead} days for {empresa.nombre}")
            return True  # No es error, simplemente no hay actividades

        # Determinar tipo de urgencia según días restantes
        if days_ahead == 0:
            urgency_level = 'critical'
            urgency_text = 'VENCEN HOY'
        elif days_ahead <= 7:
            urgency_level = 'high'
            urgency_text = f'VENCEN EN {days_ahead} DÍAS'
        else:
            urgency_level = 'medium'
            urgency_text = f'VENCEN EN {days_ahead} DÍAS'

        # Contexto para el template
        context = {
            'empresa': empresa,
            # PRÓXIMAS (futuras)
            'equipos_calibracion_proximas': equipos_calibracion_proximas,
            'equipos_mantenimiento_proximos': equipos_mantenimiento_proximos,
            'equipos_comprobacion_proximas': equipos_comprobacion_proximas,
            # VENCIDAS
            'equipos_calibracion_vencidas': equipos_calibracion_vencidas,
            'equipos_mantenimiento_vencidos': equipos_mantenimiento_vencidos,
            'equipos_comprobacion_vencidas': equipos_comprobacion_vencidas,
            # CONTADORES
            'total_proximas': total_proximas,
            'total_vencidas': total_vencidas,
            'total_actividades': total_actividades,
            # OTROS
            'days_ahead': days_ahead,
            'target_date': target_date,
            'urgency_level': urgency_level,
            'urgency_text': urgency_text,
            'site_name': 'SAM Metrologia',
            'today': today
        }

        try:
            # Configurar email dinámicamente
            if not configure_email_settings():
                logger.error("Failed to configure email settings")
                return False

            # Renderizar templates de email
            subject = f"Recordatorio Consolidado - {urgency_text} - {empresa.nombre}"
            text_content = render_to_string('emails/consolidated_reminder.txt', context)
            html_content = render_to_string('emails/consolidated_reminder.html', context)

            # Crear email con versión HTML y texto
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Consolidated reminder sent for {empresa.nombre}: {total_actividades} activities due in {days_ahead} days")
            return True

        except Exception as e:
            logger.error(f"Failed to send consolidated reminder for {empresa.nombre}: {e}")
            return False

    @staticmethod
    def check_all_reminders():
        """
        Revisa TODAS las empresas y envía recordatorios consolidados.
        Solo para días configurados: 30, 15, 7, 0 (día de vencimiento)
        """
        today = timezone.localdate()
        reminder_days = [30, 15, 7, 0]  # Días antes del vencimiento (0 = día de vencimiento)

        sent_count = 0
        total_companies = 0

        # Obtener todas las empresas activas (excluir eliminadas)
        empresas = Empresa.objects.filter(
            estado_suscripcion='Activo',
            is_deleted=False
        ).prefetch_related('equipos')

        for empresa in empresas:
            total_companies += 1

            for days in reminder_days:
                target_date = today + timedelta(days=days)

                # Verificar si hay equipos con actividades en esa fecha
                has_activities = (
                    empresa.equipos.filter(proxima_calibracion=target_date, estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']).exists() or
                    empresa.equipos.filter(proximo_mantenimiento=target_date, estado__in=['Activo', 'En Calibración', 'En Comprobación']).exists() or
                    empresa.equipos.filter(proxima_comprobacion=target_date, estado__in=[ESTADO_ACTIVO, ESTADO_EN_CALIBRACION, 'En Mantenimiento']).exists()
                )

                if has_activities:
                    if NotificationScheduler.send_consolidated_reminder(empresa, days):
                        sent_count += 1
                        logger.info(f"Consolidated reminder sent to {empresa.nombre} for activities due in {days} days")

        logger.info(f"Consolidated reminders check completed. Sent: {sent_count} emails to {total_companies} companies")
        return sent_count

    @staticmethod
    def check_calibration_reminders():
        """
        OBSOLETO: Reemplazado por check_all_reminders() que envía emails consolidados.
        Se mantiene para compatibilidad.
        """
        return NotificationScheduler.check_all_reminders()

    @staticmethod
    def check_maintenance_reminders():
        """
        Revisa todos los equipos y envía recordatorios de mantenimiento.
        """
        today = timezone.localdate()
        reminder_days = [1, 3, 7, 15]

        sent_count = 0

        for days in reminder_days:
            target_date = today + timedelta(days=days)

            equipos = Equipo.objects.filter(
                proximo_mantenimiento=target_date,
                estado__in=['Activo', 'En Calibración', 'En Comprobación']
            ).select_related('empresa')

            for equipo in equipos:
                if NotificationService.send_maintenance_reminder(equipo, days):
                    sent_count += 1

        logger.info(f"Maintenance reminders check completed. Sent: {sent_count}")
        return sent_count

    @staticmethod
    def send_weekly_summaries():
        """
        Envía resúmenes semanales a todas las empresas.
        """
        empresas = Empresa.objects.filter(
            estado_suscripcion='Activo',
            is_deleted=False
        ).prefetch_related('usuarios_empresa')

        sent_count = 0

        for empresa in empresas:
            if NotificationService.send_weekly_summary(empresa):
                sent_count += 1

        logger.info(f"Weekly summaries sent to {sent_count} companies")
        return sent_count

    @staticmethod
    def send_weekly_overdue_reminders():
        """
        Envía recordatorios semanales para equipos con actividades vencidas.

        - Se envía el mismo día de la semana cada semana
        - Máximo 3 recordatorios por actividad vencida
        - Deja de enviar si la actividad fue completada
        - Solo para empresas activas no eliminadas

        Retorna:
            sent_count: Número de recordatorios enviados
        """
        from .models import NotificacionVencimiento

        today = timezone.localdate()
        sent_count = 0

        # Obtener todas las empresas activas no eliminadas
        empresas = Empresa.objects.filter(
            estado_suscripcion='Activo',
            is_deleted=False
        ).prefetch_related('equipos')

        for empresa in empresas:
            # Recopilar equipos vencidos por tipo de actividad
            equipos_vencidos = {
                'calibracion': [],
                'mantenimiento': [],
                'comprobacion': []
            }

            # CALIBRACIONES VENCIDAS
            for equipo in empresa.equipos.filter(
                proxima_calibracion__lt=today,
                estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
            ).select_related('empresa'):
                # Verificar si la fecha cambió (actividad fue completada)
                puede_enviar, numero_recordatorio = NotificacionVencimiento.puede_enviar_recordatorio(
                    equipo, 'calibracion', equipo.proxima_calibracion
                )

                if puede_enviar:
                    equipos_vencidos['calibracion'].append(equipo)
                    # Registrar que se enviará notificación
                    NotificacionVencimiento.objects.create(
                        equipo=equipo,
                        tipo_actividad='calibracion',
                        fecha_vencimiento=equipo.proxima_calibracion,
                        numero_recordatorio=numero_recordatorio,
                        fecha_ultima_revision=equipo.proxima_calibracion
                    )

            # MANTENIMIENTOS VENCIDOS
            for equipo in empresa.equipos.filter(
                proximo_mantenimiento__lt=today,
                estado__in=['Activo', 'En Calibración', 'En Comprobación']
            ).select_related('empresa'):
                puede_enviar, numero_recordatorio = NotificacionVencimiento.puede_enviar_recordatorio(
                    equipo, 'mantenimiento', equipo.proximo_mantenimiento
                )

                if puede_enviar:
                    equipos_vencidos['mantenimiento'].append(equipo)
                    NotificacionVencimiento.objects.create(
                        equipo=equipo,
                        tipo_actividad='mantenimiento',
                        fecha_vencimiento=equipo.proximo_mantenimiento,
                        numero_recordatorio=numero_recordatorio,
                        fecha_ultima_revision=equipo.proximo_mantenimiento
                    )

            # COMPROBACIONES VENCIDAS
            for equipo in empresa.equipos.filter(
                proxima_comprobacion__lt=today,
                estado__in=[ESTADO_ACTIVO, ESTADO_EN_CALIBRACION, 'En Mantenimiento']
            ).select_related('empresa'):
                puede_enviar, numero_recordatorio = NotificacionVencimiento.puede_enviar_recordatorio(
                    equipo, 'comprobacion', equipo.proxima_comprobacion
                )

                if puede_enviar:
                    equipos_vencidos['comprobacion'].append(equipo)
                    NotificacionVencimiento.objects.create(
                        equipo=equipo,
                        tipo_actividad='comprobacion',
                        fecha_vencimiento=equipo.proxima_comprobacion,
                        numero_recordatorio=numero_recordatorio,
                        fecha_ultima_revision=equipo.proxima_comprobacion
                    )

            # Si hay equipos vencidos para esta empresa, enviar email consolidado
            total_vencidos = (len(equipos_vencidos['calibracion']) +
                            len(equipos_vencidos['mantenimiento']) +
                            len(equipos_vencidos['comprobacion']))

            if total_vencidos > 0:
                # Enviar email de recordatorio semanal
                if NotificationScheduler._send_weekly_overdue_email(
                    empresa,
                    equipos_vencidos['calibracion'],
                    equipos_vencidos['mantenimiento'],
                    equipos_vencidos['comprobacion']
                ):
                    sent_count += 1
                    logger.info(f"Weekly overdue reminder sent to {empresa.nombre}: {total_vencidos} overdue activities")

        logger.info(f"Weekly overdue reminders completed. Sent: {sent_count} emails")
        return sent_count

    @staticmethod
    def _send_weekly_overdue_email(empresa, calibraciones_vencidas, mantenimientos_vencidos, comprobaciones_vencidas):
        """
        Envía email consolidado con recordatorio semanal de actividades vencidas.
        """
        # Obtener usuarios de la empresa
        recipients = NotificationService._get_company_recipients(empresa)
        if not recipients:
            logger.warning(f"No recipients found for weekly overdue reminder: {empresa.nombre}")
            return False

        today = timezone.localdate()
        total_vencidos = len(calibraciones_vencidas) + len(mantenimientos_vencidos) + len(comprobaciones_vencidas)

        # Contexto para el template
        context = {
            'empresa': empresa,
            'equipos_calibracion_vencidas': calibraciones_vencidas,
            'equipos_mantenimiento_vencidos': mantenimientos_vencidos,
            'equipos_comprobacion_vencidas': comprobaciones_vencidas,
            'total_vencidos': total_vencidos,
            'site_name': 'SAM Metrologia',
            'today': today,
            'es_recordatorio_semanal': True
        }

        try:
            # Configurar email dinámicamente
            if not configure_email_settings():
                logger.error("Failed to configure email settings")
                return False

            # Renderizar templates de email
            subject = f"⚠️ RECORDATORIO SEMANAL - Actividades Vencidas - {empresa.nombre}"
            text_content = render_to_string('emails/weekly_overdue_reminder.txt', context)
            html_content = render_to_string('emails/weekly_overdue_reminder.html', context)

            # Crear email con versión HTML y texto
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Weekly overdue reminder sent for {empresa.nombre}: {total_vencidos} overdue activities")
            return True

        except Exception as e:
            logger.error(f"Failed to send weekly overdue reminder for {empresa.nombre}: {e}")
            return False