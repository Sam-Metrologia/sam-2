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

logger = logging.getLogger('core')

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
            'site_name': 'SAM Metrología',
        }

        try:
            # Renderizar templates de email
            subject = f"🔔 Calibración próxima a vencer - {equipo.nombre}"
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
            'site_name': 'SAM Metrología',
        }

        try:
            subject = f"🔧 Mantenimiento próximo a vencer - {equipo.nombre}"
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
            'site_name': 'SAM Metrología',
        }

        try:
            subject = f"📊 Resumen semanal - {empresa.nombre}"
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
        Obtiene lista de emails de usuarios de la empresa.
        """
        recipients = []

        # Obtener usuarios activos de la empresa con email
        users = CustomUser.objects.filter(
            empresa=empresa,
            is_active=True,
            email__isnull=False
        ).exclude(email='')

        for user in users:
            if user.email:
                recipients.append(user.email)

        # Si no hay usuarios con email, usar email de la empresa si existe
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
        Envía UN SOLO email consolidado con todas las actividades próximas a vencer.
        Incluye: calibraciones, mantenimientos y comprobaciones.
        """
        today = timezone.localdate()
        target_date = today + timedelta(days=days_ahead)

        # Obtener usuarios de la empresa
        recipients = NotificationService._get_company_recipients(empresa)
        if not recipients:
            logger.warning(f"No recipients found for consolidated reminder: {empresa.nombre}")
            return False

        # Obtener equipos con actividades próximas a vencer
        equipos_calibracion = empresa.equipos.filter(
            proxima_calibracion=target_date,
            estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']
        ).select_related('empresa')

        equipos_mantenimiento = empresa.equipos.filter(
            proximo_mantenimiento=target_date,
            estado__in=['Activo', 'En Calibración', 'En Comprobación']
        ).select_related('empresa')

        equipos_comprobacion = empresa.equipos.filter(
            proxima_comprobacion=target_date,
            estado__in=['Activo', 'En Calibración', 'En Mantenimiento']
        ).select_related('empresa')

        # Solo enviar si hay actividades que notificar
        total_actividades = (equipos_calibracion.count() +
                           equipos_mantenimiento.count() +
                           equipos_comprobacion.count())

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
            'equipos_calibracion': equipos_calibracion,
            'equipos_mantenimiento': equipos_mantenimiento,
            'equipos_comprobacion': equipos_comprobacion,
            'days_ahead': days_ahead,
            'target_date': target_date,
            'urgency_level': urgency_level,
            'urgency_text': urgency_text,
            'total_actividades': total_actividades,
            'site_name': 'SAM Metrología',
            'today': today
        }

        try:
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
        Solo para días configurados: 15, 7, 0 (día de vencimiento)
        """
        today = timezone.localdate()
        reminder_days = [15, 7, 0]  # Días antes del vencimiento (0 = día de vencimiento)

        sent_count = 0
        total_companies = 0

        # Obtener todas las empresas activas
        empresas = Empresa.objects.filter(
            estado_suscripcion='Activo'
        ).prefetch_related('equipos')

        for empresa in empresas:
            total_companies += 1

            for days in reminder_days:
                target_date = today + timedelta(days=days)

                # Verificar si hay equipos con actividades en esa fecha
                has_activities = (
                    empresa.equipos.filter(proxima_calibracion=target_date, estado__in=['Activo', 'En Mantenimiento', 'En Comprobación']).exists() or
                    empresa.equipos.filter(proximo_mantenimiento=target_date, estado__in=['Activo', 'En Calibración', 'En Comprobación']).exists() or
                    empresa.equipos.filter(proxima_comprobacion=target_date, estado__in=['Activo', 'En Calibración', 'En Mantenimiento']).exists()
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
            estado_suscripcion='Activo'
        ).prefetch_related('usuarios_empresa')

        sent_count = 0

        for empresa in empresas:
            if NotificationService.send_weekly_summary(empresa):
                sent_count += 1

        logger.info(f"Weekly summaries sent to {sent_count} companies")
        return sent_count