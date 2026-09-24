"""
Tests para NotificationScheduler.send_trial_inactivity_reminders()
(core/notifications.py) — recordatorio de reenganche día 3 / día 7 para
trials que no volvieron a entrar por su cuenta.
"""
import pytest
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone

from core.notifications import NotificationScheduler
from core.models import CustomUser, Empresa
from tests.factories import EmpresaFactory, UserFactory


def _crear_empresa_trial(dias_desde_creacion, empresa_kwargs=None):
    """
    Empresa.save() fuerza es_periodo_prueba=False/fecha_inicio_plan=None en
    empresas nuevas salvo que se marque `_plan_set_manually` en la instancia
    ANTES del primer save() (ver core/models/empresa.py) — la factory no
    conoce ese atributo, así que hay que fijar los campos con un update()
    posterior al insert inicial.
    """
    hoy = timezone.localdate()
    empresa = EmpresaFactory(**(empresa_kwargs or {}))
    Empresa.objects.filter(pk=empresa.pk).update(
        es_periodo_prueba=True,
        fecha_inicio_plan=hoy - timedelta(days=dias_desde_creacion),
    )
    empresa.refresh_from_db()
    return empresa


def _crear_admin(empresa, volvio_a_entrar, dias_desde_creacion):
    admin = UserFactory(empresa=empresa, rol_usuario='ADMINISTRADOR', email='admin@empresa.com')
    creacion = timezone.now() - timedelta(days=dias_desde_creacion)
    if volvio_a_entrar:
        ultimo_login = creacion + timedelta(days=1)  # entró de nuevo otro día
    else:
        ultimo_login = creacion  # el auto-login del momento de creación, nunca volvió
    CustomUser.objects.filter(pk=admin.pk).update(date_joined=creacion, last_login=ultimo_login)
    admin.refresh_from_db()
    return admin


@pytest.mark.django_db
class TestSendTrialInactivityReminders:

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_envia_recordatorio_dia_3_si_nunca_volvio(self, mock_config):
        empresa = _crear_empresa_trial(3)
        admin = _crear_admin(empresa, volvio_a_entrar=False, dias_desde_creacion=3)

        sent = NotificationScheduler.send_trial_inactivity_reminders()

        assert sent == 1

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_envia_recordatorio_dia_7_si_nunca_volvio(self, mock_config):
        empresa = _crear_empresa_trial(7)
        admin = _crear_admin(empresa, volvio_a_entrar=False, dias_desde_creacion=7)

        sent = NotificationScheduler.send_trial_inactivity_reminders()

        assert sent == 1

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_no_envia_si_ya_volvio_a_entrar(self, mock_config):
        empresa = _crear_empresa_trial(3)
        _crear_admin(empresa, volvio_a_entrar=True, dias_desde_creacion=3)

        sent = NotificationScheduler.send_trial_inactivity_reminders()

        assert sent == 0

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_no_envia_en_dia_que_no_es_3_ni_7(self, mock_config):
        empresa = _crear_empresa_trial(4)
        _crear_admin(empresa, volvio_a_entrar=False, dias_desde_creacion=4)

        sent = NotificationScheduler.send_trial_inactivity_reminders()

        assert sent == 0

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_no_envia_si_ya_no_esta_en_periodo_de_prueba(self, mock_config):
        empresa = _crear_empresa_trial(3)
        empresa.es_periodo_prueba = False
        empresa.save(update_fields=['es_periodo_prueba'])
        _crear_admin(empresa, volvio_a_entrar=False, dias_desde_creacion=3)

        sent = NotificationScheduler.send_trial_inactivity_reminders()

        assert sent == 0

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_no_envia_si_empresa_eliminada(self, mock_config):
        empresa = _crear_empresa_trial(3)
        empresa.is_deleted = True
        empresa.save(update_fields=['is_deleted'])
        _crear_admin(empresa, volvio_a_entrar=False, dias_desde_creacion=3)

        sent = NotificationScheduler.send_trial_inactivity_reminders()

        assert sent == 0

    @patch('core.notifications.configure_email_settings', return_value=True)
    def test_lo_manda_solo_al_administrador(self, mock_config, mailoutbox):
        empresa = _crear_empresa_trial(3)
        admin = _crear_admin(empresa, volvio_a_entrar=False, dias_desde_creacion=3)
        UserFactory(empresa=empresa, rol_usuario='GERENCIA', email='gerencia@empresa.trial.sam')
        UserFactory(empresa=empresa, rol_usuario='TECNICO', email='tecnico@empresa.trial.sam')

        NotificationScheduler.send_trial_inactivity_reminders()

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ['admin@empresa.com']
