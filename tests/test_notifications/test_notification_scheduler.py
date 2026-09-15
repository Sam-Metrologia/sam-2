"""
Tests para NotificationScheduler (core/notifications.py).

Cubre funciones sin tests actuales:
- send_consolidated_reminder (líneas 282-412)
- check_all_reminders (líneas 415-451)
- check_calibration_reminders (líneas 453-459)
- check_maintenance_reminders (líneas 461-484)
- send_weekly_summaries (líneas 486-503)

Notas técnicas:
- Equipo.save() recalcula proxima_calibracion → usar .update() para fijar fechas en tests
- empresa.email siempre da un destinatario → usar mock de _get_company_recipients para probar "sin destinatarios"
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from core.models import Equipo, Empresa


# ============================================================================
# Fixtures compartidas
# ============================================================================

@pytest.fixture
def empresa_activa(db):
    """Empresa activa con estado_suscripcion='Activo' e is_deleted=False (defaults)."""
    from tests.factories import EmpresaFactory
    return EmpresaFactory()


@pytest.fixture
def usuario_empresa(empresa_activa):
    """Usuario activo de la empresa."""
    from tests.factories import UserFactory
    return UserFactory(empresa=empresa_activa, email='notif@example.com', is_active=True)


@pytest.fixture
def equipo_activo(empresa_activa):
    """Equipo con estado='Activo' usando .update() para evitar recálculo en save()."""
    from tests.factories import EquipoFactory
    equipo = EquipoFactory(empresa=empresa_activa)
    # Usar update() para fijar estado SIN triggear Equipo.save() que recalcula fechas
    Equipo.objects.filter(pk=equipo.pk).update(estado='Activo')
    equipo.refresh_from_db()
    return equipo


# ============================================================================
# send_consolidated_reminder
# ============================================================================

class TestSendConsolidatedReminder:
    """Tests para NotificationScheduler.send_consolidated_reminder()."""

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService._get_company_recipients', return_value=[])
    def test_sin_destinatarios_retorna_false(self, mock_recip, empresa_activa):
        """Sin destinatarios válidos, retorna False sin enviar email."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=7)

        assert resultado is False
        mock_recip.assert_called_once_with(empresa_activa)

    @pytest.mark.django_db
    def test_sin_actividades_retorna_true(self, empresa_activa, usuario_empresa):
        """Con destinatarios pero sin actividades próximas/vencidas, retorna True (no es error)."""
        from core.notifications import NotificationScheduler

        # Sin equipos → total_actividades == 0 → retorna True sin enviar email
        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=7)

        assert resultado is True

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido email')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_envia_email_con_calibracion_proxima(self, mock_email_cls, mock_render, mock_config,
                                                   empresa_activa, usuario_empresa, equipo_activo):
        """Con calibración próxima a 7 días, envía email y retorna True."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        # Usar .update() para fijar fecha sin triggear Equipo.save()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=7),
            estado='Activo'
        )

        mock_email_instance = MagicMock()
        mock_email_cls.return_value = mock_email_instance

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=7)

        assert resultado is True
        mock_email_instance.send.assert_called_once()

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=False)
    @patch('core.notifications.render_to_string', return_value='contenido')
    def test_fallo_config_email_retorna_false(self, mock_render, mock_config,
                                               empresa_activa, usuario_empresa, equipo_activo):
        """Si configure_email_settings() falla, no se envía el email y retorna False."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=15),
            estado='Activo'
        )

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=15)

        assert resultado is False

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_excepcion_al_enviar_retorna_false(self, mock_email_cls, mock_render, mock_config,
                                               empresa_activa, usuario_empresa, equipo_activo):
        """Si EmailMultiAlternatives.send() lanza excepción, retorna False."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=7),
            estado='Activo'
        )

        mock_email_instance = MagicMock()
        mock_email_instance.send.side_effect = Exception('SMTP connection failed')
        mock_email_cls.return_value = mock_email_instance

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=7)

        assert resultado is False

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_urgencia_alta_con_menos_de_7_dias(self, mock_email_cls, mock_render, mock_config,
                                                empresa_activa, usuario_empresa, equipo_activo):
        """Con days_ahead=5 (<=7), el contexto incluye urgency_level='high'."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=5),
            estado='Activo'
        )

        mock_email_cls.return_value = MagicMock()

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=5)

        assert resultado is True
        # Verificar que urgency_level='high' fue pasado al contexto
        assert mock_render.called
        context = mock_render.call_args[0][1]  # Segundo argumento posicional
        assert context.get('urgency_level') == 'high'

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_urgencia_media_con_mas_de_7_dias(self, mock_email_cls, mock_render, mock_config,
                                               empresa_activa, usuario_empresa, equipo_activo):
        """Con days_ahead=15 (>7), el contexto incluye urgency_level='medium'."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=15),
            estado='Activo'
        )

        mock_email_cls.return_value = MagicMock()

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=15)

        assert resultado is True
        context = mock_render.call_args[0][1]
        assert context.get('urgency_level') == 'medium'

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_con_actividad_vencida_incluida(self, mock_email_cls, mock_render, mock_config,
                                             empresa_activa, usuario_empresa, equipo_activo):
        """Con calibración vencida en los últimos 30 días, se incluye en el email."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today - timedelta(days=10),  # Vencida hace 10 días
            estado='Activo'
        )

        mock_email_cls.return_value = MagicMock()

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=7)

        assert resultado is True
        mock_email_cls.return_value.send.assert_called_once()

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_con_mantenimiento_proximo(self, mock_email_cls, mock_render, mock_config,
                                       empresa_activa, usuario_empresa, equipo_activo):
        """Con mantenimiento próximo también genera email."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proximo_mantenimiento=today + timedelta(days=15),
            estado='Activo'
        )

        mock_email_cls.return_value = MagicMock()

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=15)

        assert resultado is True

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_dias_ahead_cero_urgencia_critica(self, mock_email_cls, mock_render, mock_config,
                                              empresa_activa, usuario_empresa, equipo_activo):
        """Con days_ahead=0, la urgency_level es 'critical' y texto es 'VENCEN HOY'."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today - timedelta(days=5),  # Vencida hace 5 días (en vencidas)
            estado='Activo'
        )

        mock_email_cls.return_value = MagicMock()

        resultado = NotificationScheduler.send_consolidated_reminder(empresa_activa, days_ahead=0)

        assert resultado is True
        context = mock_render.call_args[0][1]
        assert context.get('urgency_level') == 'critical'
        assert context.get('urgency_text') == 'VENCEN HOY'


# ============================================================================
# check_all_reminders
# ============================================================================

class TestCheckAllReminders:
    """Tests para NotificationScheduler.check_all_reminders()."""

    @pytest.mark.django_db
    def test_sin_empresas_activas_retorna_cero(self):
        """Sin empresas con estado_suscripcion='Activo', retorna 0."""
        from core.notifications import NotificationScheduler

        # Marcar todas las empresas como eliminadas
        Empresa.objects.filter(is_deleted=False).update(is_deleted=True)

        resultado = NotificationScheduler.check_all_reminders()

        assert resultado == 0

    @pytest.mark.django_db
    def test_es_alias_de_send_due_today_alerts(self, empresa_activa):
        """
        check_all_reminders() ya no revisa umbrales relativos (30/15/7/0) —
        ahora es solo la alerta del día exacto (send_due_today_alerts),
        se mantiene el nombre por compatibilidad con el cron diario existente.
        """
        from core.notifications import NotificationScheduler

        with patch(
            'core.notifications.NotificationScheduler.send_due_today_alerts', return_value=3
        ) as mock_due_today:
            resultado = NotificationScheduler.check_all_reminders()

        mock_due_today.assert_called_once()
        assert resultado == 3

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=True)
    def test_empresa_con_actividad_hoy_llama_send_periodic_digest_con_hoy(
            self, mock_send, empresa_activa, usuario_empresa, equipo_activo):
        """check_all_reminders() delega en send_periodic_digest con fecha_desde=fecha_hasta=hoy."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today,
            estado='Activo'
        )

        resultado = NotificationScheduler.check_all_reminders()

        mock_send.assert_called_once_with(
            empresa_activa, today, today, 'VENCE HOY', urgency_level='critical'
        )
        assert resultado >= 1

    @pytest.mark.django_db
    def test_empresa_sin_actividades_no_cuenta_como_enviado(self, empresa_activa, usuario_empresa):
        """Sin actividades que venzan hoy, no se manda correo y no cuenta en el total."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.check_all_reminders()

        # send_periodic_digest se evalúa igual (una vez por empresa activa), pero al no
        # haber nada que avisar retorna None, no True — así que no cuenta como enviado.
        assert resultado == 0


# ============================================================================
# check_calibration_reminders
# ============================================================================

class TestCheckCalibrationReminders:
    """Tests para NotificationScheduler.check_calibration_reminders() (obsoleto)."""

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.check_all_reminders', return_value=5)
    def test_delega_a_check_all_reminders(self, mock_check_all):
        """check_calibration_reminders() es un alias de check_all_reminders()."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.check_calibration_reminders()

        mock_check_all.assert_called_once()
        assert resultado == 5


# ============================================================================
# check_maintenance_reminders
# ============================================================================

class TestCheckMaintenanceReminders:
    """Tests para NotificationScheduler.check_maintenance_reminders()."""

    @pytest.mark.django_db
    def test_sin_equipos_retorna_cero(self):
        """Sin equipos con proximo_mantenimiento en los días de recordatorio, retorna 0."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.check_maintenance_reminders()

        assert resultado == 0

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService.send_maintenance_reminder', return_value=True)
    def test_equipo_con_mantenimiento_proximo_envia_reminder(self, mock_send,
                                                               empresa_activa, equipo_activo):
        """Con equipo con proximo_mantenimiento en días de recordatorio [1,3,7,15], envía reminder."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        # Usar día de recordatorio: 7 días
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proximo_mantenimiento=today + timedelta(days=7),
            estado='Activo'
        )

        resultado = NotificationScheduler.check_maintenance_reminders()

        assert mock_send.called
        assert resultado >= 1

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService.send_maintenance_reminder', return_value=False)
    def test_reminder_fallido_no_cuenta(self, mock_send, empresa_activa, equipo_activo):
        """Si send_maintenance_reminder retorna False, sent_count no aumenta."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proximo_mantenimiento=today + timedelta(days=3),
            estado='Activo'
        )

        resultado = NotificationScheduler.check_maintenance_reminders()

        assert resultado == 0


# ============================================================================
# send_weekly_summaries
# ============================================================================

class TestSendWeeklySummaries:
    """Tests para NotificationScheduler.send_weekly_summaries()."""

    @pytest.mark.django_db
    def test_sin_empresas_activas_retorna_cero(self):
        """Sin empresas con estado_suscripcion='Activo', retorna 0."""
        from core.notifications import NotificationScheduler

        Empresa.objects.filter(is_deleted=False).update(is_deleted=True)

        resultado = NotificationScheduler.send_weekly_summaries()

        assert resultado == 0

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService.send_weekly_summary', return_value=True)
    def test_empresa_activa_incrementa_contador(self, mock_send, empresa_activa):
        """Con una empresa activa, llama send_weekly_summary y retorna 1."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.send_weekly_summaries()

        mock_send.assert_called_once_with(empresa_activa)
        assert resultado == 1

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService.send_weekly_summary', return_value=False)
    def test_summary_fallido_no_cuenta(self, mock_send, empresa_activa):
        """Si send_weekly_summary retorna False, sent_count no aumenta."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.send_weekly_summaries()

        assert resultado == 0

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService.send_weekly_summary', return_value=True)
    def test_multiples_empresas_cuenta_todas(self, mock_send):
        """Con múltiples empresas activas, cuenta todas las exitosas."""
        from core.notifications import NotificationScheduler
        from tests.factories import EmpresaFactory

        EmpresaFactory.create_batch(3)  # 3 empresas activas

        resultado = NotificationScheduler.send_weekly_summaries()

        assert resultado >= 3


# ============================================================================
# send_weekly_overdue_reminders (líneas 518-613)
# ============================================================================

class TestSendWeeklyOverdueReminders:
    """Tests para NotificationScheduler.send_weekly_overdue_reminders()."""

    @pytest.mark.django_db
    def test_sin_empresas_activas_retorna_cero(self, db):
        """Sin empresas activas, retorna 0 sin enviar nada."""
        from core.notifications import NotificationScheduler

        # Asegurar que no hay empresas activas
        Empresa.objects.all().update(is_deleted=True)

        resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 0

    @pytest.mark.django_db
    def test_empresa_sin_equipos_vencidos_retorna_cero(self, empresa_activa, usuario_empresa):
        """Empresa activa sin equipos vencidos → retorna 0."""
        from core.notifications import NotificationScheduler

        # Sin equipos → total_vencidos == 0 → no envía email
        resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 0

    @pytest.mark.django_db
    def test_calibracion_vencida_sin_notificacion_previa_envio_exitoso(
        self, empresa_activa, usuario_empresa, equipo_activo
    ):
        """
        Equipo con calibración vencida y sin NotificacionVencimiento previa.
        puede_enviar=True → agrega al equipo y llama _send_weekly_overdue_email.
        Con mock de email exitoso → retorna 1.
        (Cubre líneas 538-556 y 596-610.)
        """
        from core.notifications import NotificationScheduler
        from datetime import date

        today = date.today()
        fecha_vencida = today - timedelta(days=5)

        # Fijar calibración vencida SIN triggear Equipo.save()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=fecha_vencida,
            estado='Activo',
        )
        equipo_activo.refresh_from_db()

        with patch(
            'core.notifications.NotificationScheduler._send_weekly_overdue_email',
            return_value=True
        ) as mock_email:
            resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 1
        assert mock_email.called
        # Verificar que se creó la NotificacionVencimiento
        from core.models import NotificacionVencimiento
        assert NotificacionVencimiento.objects.filter(
            equipo=equipo_activo,
            tipo_actividad='calibracion',
        ).exists()

    @pytest.mark.django_db
    def test_calibracion_vencida_con_max_recordatorios_no_envia(
        self, empresa_activa, usuario_empresa, equipo_activo
    ):
        """
        Equipo con calibración vencida pero ya tiene 3 recordatorios (max).
        puede_enviar=False → NO agrega equipo → total_vencidos=0 → no envía email.
        (Cubre la rama if puede_enviar dentro del bucle de calibraciones.)
        """
        from core.notifications import NotificationScheduler
        from core.models import NotificacionVencimiento
        from datetime import date

        today = date.today()
        fecha_vencida = today - timedelta(days=20)

        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=fecha_vencida,
            estado='Activo',
        )
        equipo_activo.refresh_from_db()

        # Simular que ya se enviaron 3 recordatorios
        NotificacionVencimiento.objects.create(
            equipo=equipo_activo,
            tipo_actividad='calibracion',
            fecha_vencimiento=fecha_vencida,
            numero_recordatorio=3,
            fecha_ultima_revision=fecha_vencida,
        )

        resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 0

    @pytest.mark.django_db
    def test_mantenimiento_vencido_envio_exitoso(
        self, empresa_activa, usuario_empresa, equipo_activo
    ):
        """
        Equipo con mantenimiento vencido → se envía email semanal de vencidos.
        (Cubre líneas 558-575.)
        """
        from core.notifications import NotificationScheduler
        from datetime import date

        today = date.today()
        fecha_vencida = today - timedelta(days=3)

        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proximo_mantenimiento=fecha_vencida,
            estado='Activo',
        )
        equipo_activo.refresh_from_db()

        with patch(
            'core.notifications.NotificationScheduler._send_weekly_overdue_email',
            return_value=True
        ):
            resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 1
        from core.models import NotificacionVencimiento
        assert NotificacionVencimiento.objects.filter(
            equipo=equipo_activo,
            tipo_actividad='mantenimiento',
        ).exists()

    @pytest.mark.django_db
    def test_comprobacion_vencida_envio_exitoso(
        self, empresa_activa, usuario_empresa, equipo_activo
    ):
        """
        Equipo con comprobación vencida → se envía email semanal de vencidos.
        (Cubre líneas 577-594.)
        """
        from core.notifications import NotificationScheduler
        from datetime import date

        today = date.today()
        fecha_vencida = today - timedelta(days=2)

        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_comprobacion=fecha_vencida,
            estado='Activo',
        )
        equipo_activo.refresh_from_db()

        with patch(
            'core.notifications.NotificationScheduler._send_weekly_overdue_email',
            return_value=True
        ):
            resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 1
        from core.models import NotificacionVencimiento
        assert NotificacionVencimiento.objects.filter(
            equipo=equipo_activo,
            tipo_actividad='comprobacion',
        ).exists()

    @pytest.mark.django_db
    def test_email_retorna_false_no_cuenta(
        self, empresa_activa, usuario_empresa, equipo_activo
    ):
        """
        Si _send_weekly_overdue_email retorna False, sent_count no aumenta.
        (Cubre la rama else implícita de if _send_weekly_overdue_email(...).)
        """
        from core.notifications import NotificationScheduler
        from datetime import date

        today = date.today()
        fecha_vencida = today - timedelta(days=1)

        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=fecha_vencida,
            estado='Activo',
        )

        with patch(
            'core.notifications.NotificationScheduler._send_weekly_overdue_email',
            return_value=False
        ):
            resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 0

    @pytest.mark.django_db
    def test_multiples_empresas_y_tipos_vencidos(self, db):
        """
        Múltiples empresas con distintos tipos de actividades vencidas.
        """
        from core.notifications import NotificationScheduler
        from tests.factories import EmpresaFactory, EquipoFactory, UserFactory
        from datetime import date

        today = date.today()
        fecha_vencida = today - timedelta(days=3)

        empresa1 = EmpresaFactory()
        empresa2 = EmpresaFactory()
        UserFactory(empresa=empresa1, email='e1@test.com', is_active=True)
        UserFactory(empresa=empresa2, email='e2@test.com', is_active=True)

        eq1 = EquipoFactory(empresa=empresa1)
        eq2 = EquipoFactory(empresa=empresa2)

        Equipo.objects.filter(pk=eq1.pk).update(
            proxima_calibracion=fecha_vencida, estado='Activo'
        )
        Equipo.objects.filter(pk=eq2.pk).update(
            proximo_mantenimiento=fecha_vencida, estado='Activo'
        )

        with patch(
            'core.notifications.NotificationScheduler._send_weekly_overdue_email',
            return_value=True
        ):
            resultado = NotificationScheduler.send_weekly_overdue_reminders()

        assert resultado == 2


# ============================================================================
# _send_weekly_overdue_email (líneas 621-667)
# ============================================================================

class TestSendWeeklyOverdueEmail:
    """Tests para NotificationScheduler._send_weekly_overdue_email()."""

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService._get_company_recipients', return_value=[])
    def test_sin_destinatarios_retorna_false(self, mock_recip, empresa_activa):
        """Sin destinatarios → retorna False (cubre líneas 621-624)."""
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler._send_weekly_overdue_email(
            empresa_activa, [], [], []
        )

        assert resultado is False

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=False)
    def test_fallo_configuracion_email_retorna_false(
        self, mock_config, empresa_activa, usuario_empresa
    ):
        """
        configure_email_settings retorna False → retorna False
        (cubre líneas 643-645).
        """
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler._send_weekly_overdue_email(
            empresa_activa, [], [], []
        )

        assert resultado is False

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='<p>email</p>')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_envio_exitoso_retorna_true(
        self, mock_email_cls, mock_render, mock_config, empresa_activa, usuario_empresa
    ):
        """
        Envío exitoso de email → retorna True (cubre líneas 648-663).
        """
        from core.notifications import NotificationScheduler

        mock_email_instance = MagicMock()
        mock_email_cls.return_value = mock_email_instance

        resultado = NotificationScheduler._send_weekly_overdue_email(
            empresa_activa, [], [], []
        )

        assert resultado is True
        assert mock_email_instance.send.called

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', side_effect=Exception("Error de render"))
    def test_excepcion_al_enviar_retorna_false(
        self, mock_render, mock_config, empresa_activa, usuario_empresa
    ):
        """
        Excepción durante el envío → retorna False (cubre líneas 665-667).
        """
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler._send_weekly_overdue_email(
            empresa_activa, [], [], []
        )

        assert resultado is False


# ============================================================================
# send_periodic_digest — base del nuevo esquema de 4 recordatorios
# ============================================================================

class TestSendPeriodicDigest:
    """Tests para NotificationScheduler.send_periodic_digest()."""

    @pytest.mark.django_db
    @patch('core.notifications.NotificationService._get_company_recipients', return_value=[])
    def test_sin_destinatarios_retorna_false(self, mock_recip, empresa_activa):
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        resultado = NotificationScheduler.send_periodic_digest(
            empresa_activa, today, today + timedelta(days=6), 'Recordatorio semanal'
        )

        assert resultado is False

    @pytest.mark.django_db
    def test_sin_actividades_en_la_ventana_retorna_none(self, empresa_activa, usuario_empresa):
        """Sin nada que avisar en la ventana, no manda correo (retorna None, no error)."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        resultado = NotificationScheduler.send_periodic_digest(
            empresa_activa, today, today + timedelta(days=6), 'Recordatorio semanal'
        )

        assert resultado is None

    @pytest.mark.django_db
    @patch('core.notifications.configure_email_settings', return_value=True)
    @patch('core.notifications.render_to_string', return_value='contenido')
    @patch('core.notifications.EmailMultiAlternatives')
    def test_actividad_dentro_de_la_ventana_envia_correo(
        self, mock_email_cls, mock_render, mock_config, empresa_activa, usuario_empresa, equipo_activo
    ):
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=3), estado='Activo'
        )
        mock_email_cls.return_value = MagicMock()

        resultado = NotificationScheduler.send_periodic_digest(
            empresa_activa, today, today + timedelta(days=6), 'Recordatorio semanal'
        )

        assert resultado is True
        context = mock_render.call_args[0][1]
        assert context['total_proximas'] == 1
        assert context['total_vencidas'] == 0  # este digest nunca incluye vencidas

    @pytest.mark.django_db
    def test_actividad_fuera_de_la_ventana_no_se_incluye(self, empresa_activa, usuario_empresa, equipo_activo):
        """Una actividad más allá de fecha_hasta no debe disparar el envío."""
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        Equipo.objects.filter(pk=equipo_activo.pk).update(
            proxima_calibracion=today + timedelta(days=20), estado='Activo'
        )

        resultado = NotificationScheduler.send_periodic_digest(
            empresa_activa, today, today + timedelta(days=6), 'Recordatorio semanal'
        )

        assert resultado is None  # 20 días > ventana de 6 días, no cuenta


# ============================================================================
# Los 4 recordatorios de calendario fijo (reemplazan 30/15/7/0)
# ============================================================================

class TestDigestsDeCalendarioFijo:

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=True)
    def test_weekly_upcoming_usa_ventana_de_7_dias(self, mock_send, empresa_activa):
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        resultado = NotificationScheduler.send_weekly_upcoming_digests()

        mock_send.assert_called_once_with(
            empresa_activa, today, today + timedelta(days=6),
            'Recordatorio semanal — actividades de esta semana'
        )
        assert resultado == 1

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=True)
    def test_biweekly_upcoming_usa_ventana_de_15_dias(self, mock_send, empresa_activa):
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        resultado = NotificationScheduler.send_biweekly_upcoming_digests()

        mock_send.assert_called_once_with(
            empresa_activa, today, today + timedelta(days=15),
            'Recordatorio quincenal — próximos 15 días'
        )
        assert resultado == 1

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=True)
    def test_monthly_ahead_usa_todo_el_mes_siguiente(self, mock_send, empresa_activa):
        """
        Enviado el día 1, debe cubrir TODO el mes siguiente (no el actual) —
        para garantizar al menos un mes completo de anticipación, incluso
        para algo que vence el día 2 o 3 del mes siguiente.
        """
        from core.notifications import NotificationScheduler

        resultado = NotificationScheduler.send_monthly_ahead_digests()

        assert mock_send.call_count == 1
        args, kwargs = mock_send.call_args
        empresa_arg, fecha_desde, fecha_hasta, label = args

        today = timezone.localdate()
        primer_dia_prox_mes = today.replace(day=1) + relativedelta(months=1)
        ultimo_dia_prox_mes = (primer_dia_prox_mes + relativedelta(months=1)) - timedelta(days=1)

        assert empresa_arg == empresa_activa
        assert fecha_desde == primer_dia_prox_mes
        assert fecha_hasta == ultimo_dia_prox_mes
        assert fecha_desde.day == 1  # siempre arranca en el primer día del mes siguiente
        assert resultado == 1

    @pytest.mark.django_db
    def test_monthly_ahead_da_al_menos_un_mes_de_anticipacion_para_inicio_de_mes(
        self, empresa_activa, usuario_empresa
    ):
        """
        El caso concreto que motivó este diseño: un equipo que vence el
        día 2 o 3 del mes siguiente debe aparecer en el digest mensual
        (mandado el día 1), dando al menos ~1 mes de anticipación real.
        """
        from core.notifications import NotificationScheduler
        from tests.factories import EquipoFactory

        today = timezone.localdate()
        primer_dia_prox_mes = today.replace(day=1) + relativedelta(months=1)
        vence_a_inicio_del_prox_mes = primer_dia_prox_mes + timedelta(days=2)

        equipo = EquipoFactory(empresa=empresa_activa)
        Equipo.objects.filter(pk=equipo.pk).update(
            proxima_calibracion=vence_a_inicio_del_prox_mes, estado='Activo'
        )

        with patch('core.notifications.configure_email_settings', return_value=True), \
             patch('core.notifications.render_to_string', return_value='contenido') as mock_render, \
             patch('core.notifications.EmailMultiAlternatives') as mock_email_cls:
            mock_email_cls.return_value = MagicMock()
            resultado = NotificationScheduler.send_monthly_ahead_digests()

        assert resultado == 1
        context = mock_render.call_args[0][1]
        assert context['total_proximas'] == 1

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=True)
    def test_due_today_usa_hoy_como_unica_fecha_y_urgencia_critica(self, mock_send, empresa_activa):
        from core.notifications import NotificationScheduler

        today = timezone.localdate()
        resultado = NotificationScheduler.send_due_today_alerts()

        mock_send.assert_called_once_with(
            empresa_activa, today, today, 'VENCE HOY', urgency_level='critical'
        )
        assert resultado == 1

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=None)
    def test_nada_que_avisar_no_cuenta_en_ningun_digest(self, mock_send, empresa_activa):
        """None (nada que avisar) nunca debe contarse como enviado, en ninguno de los 4."""
        from core.notifications import NotificationScheduler

        assert NotificationScheduler.send_weekly_upcoming_digests() == 0
        assert NotificationScheduler.send_biweekly_upcoming_digests() == 0
        assert NotificationScheduler.send_monthly_ahead_digests() == 0
        assert NotificationScheduler.send_due_today_alerts() == 0

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_periodic_digest', return_value=False)
    def test_fallo_de_envio_no_cuenta_en_ningun_digest(self, mock_send, empresa_activa):
        """False (falló el envío) tampoco debe contarse como enviado."""
        from core.notifications import NotificationScheduler

        assert NotificationScheduler.send_weekly_upcoming_digests() == 0
        assert NotificationScheduler.send_biweekly_upcoming_digests() == 0
        assert NotificationScheduler.send_monthly_ahead_digests() == 0
        assert NotificationScheduler.send_due_today_alerts() == 0

    @pytest.mark.django_db
    def test_no_incluye_empresas_eliminadas_ni_inactivas(self, empresa_activa):
        from core.notifications import NotificationScheduler
        from tests.factories import EmpresaFactory

        empresa_eliminada = EmpresaFactory(is_deleted=True)
        empresa_expirada = EmpresaFactory(estado_suscripcion='Expirado')

        empresas = list(NotificationScheduler._empresas_activas_para_digest())

        assert empresa_activa in empresas
        assert empresa_eliminada not in empresas
        assert empresa_expirada not in empresas
