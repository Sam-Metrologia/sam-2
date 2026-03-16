"""
Tests para core/views/scheduled_tasks_api.py

Cubre: verify_token, health_check y los 7 endpoints de tareas programadas.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import Client, RequestFactory
from django.urls import reverse

from core.views.scheduled_tasks_api import verify_token

VALID_TOKEN = 'test-secret-token-12345'
BEARER_VALID = f'Bearer {VALID_TOKEN}'


# ---------------------------------------------------------------------------
# verify_token — función helper
# ---------------------------------------------------------------------------

class TestVerifyToken:

    def _make_request(self, auth_header=None, remote_addr='127.0.0.1'):
        factory = RequestFactory()
        kwargs = {}
        if auth_header:
            kwargs['HTTP_AUTHORIZATION'] = auth_header
        return factory.post('/fake/', REMOTE_ADDR=remote_addr, **kwargs)

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', '')
    def test_empty_token_config_returns_false(self):
        request = self._make_request(auth_header=BEARER_VALID)
        assert verify_token(request) is False

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_auth_header_returns_false(self):
        request = self._make_request()
        assert verify_token(request) is False

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_wrong_token_returns_false(self):
        request = self._make_request(auth_header='Bearer wrong-token')
        assert verify_token(request) is False

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_missing_bearer_prefix_returns_false(self):
        request = self._make_request(auth_header=VALID_TOKEN)
        assert verify_token(request) is False

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_valid_token_returns_true(self):
        request = self._make_request(auth_header=BEARER_VALID)
        assert verify_token(request) is True


# ---------------------------------------------------------------------------
# health_check — sin autenticación
# ---------------------------------------------------------------------------

class TestHealthCheck:

    def test_get_returns_200_ok(self):
        client = Client()
        url = reverse('core:scheduled_health_check')
        response = client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['status'] == 'ok'
        assert 'service' in data

    def test_post_not_allowed(self):
        client = Client()
        url = reverse('core:scheduled_health_check')
        response = client.post(url)
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# Helpers de conveniencia para endpoints autenticados
# ---------------------------------------------------------------------------

def _post_with_token(url_name, token=VALID_TOKEN):
    client = Client()
    return client.post(
        reverse(f'core:{url_name}'),
        HTTP_AUTHORIZATION=f'Bearer {token}',
    )


def _get_with_token(url_name, token=VALID_TOKEN):
    client = Client()
    return client.get(
        reverse(f'core:{url_name}'),
        HTTP_AUTHORIZATION=f'Bearer {token}',
    )


# ---------------------------------------------------------------------------
# trigger_daily_notifications
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTriggerDailyNotifications:

    URL = 'trigger_daily_notifications'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('core.views.scheduled_tasks_api.NotificationScheduler.check_all_reminders', return_value=5)
    def test_valid_token_returns_200(self, mock_notif):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['sent_count'] == 5

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('core.views.scheduled_tasks_api.NotificationScheduler.check_all_reminders',
           side_effect=Exception('DB error'))
    def test_exception_returns_500(self, mock_notif):
        response = _post_with_token(self.URL)
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['success'] is False


# ---------------------------------------------------------------------------
# trigger_daily_maintenance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTriggerDailyMaintenance:

    URL = 'trigger_daily_maintenance'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('core.views.scheduled_tasks_api.AdminService.execute_maintenance',
           return_value={'success': True})
    def test_valid_token_calls_maintenance_twice(self, mock_maint):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        assert mock_maint.call_count == 2
        data = json.loads(response.content)
        assert data['success'] is True

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('core.views.scheduled_tasks_api.AdminService.execute_maintenance',
           side_effect=RuntimeError('maint failed'))
    def test_exception_returns_500(self, mock_maint):
        response = _post_with_token(self.URL)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# trigger_cleanup_zips
# ---------------------------------------------------------------------------

class TestTriggerCleanupZips:

    URL = 'trigger_cleanup_zips'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command')
    def test_valid_token_returns_200(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['task'] == 'cleanup_zips'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command', side_effect=Exception('cmd failed'))
    def test_exception_returns_500(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# trigger_weekly_overdue
# ---------------------------------------------------------------------------

class TestTriggerWeeklyOverdue:

    URL = 'trigger_weekly_overdue'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('core.views.scheduled_tasks_api.NotificationScheduler.send_weekly_overdue_reminders',
           return_value=3)
    def test_valid_token_returns_count(self, mock_notif):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['sent_count'] == 3

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('core.views.scheduled_tasks_api.NotificationScheduler.send_weekly_overdue_reminders',
           side_effect=ValueError('oops'))
    def test_exception_returns_500(self, mock_notif):
        response = _post_with_token(self.URL)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# trigger_check_trials
# ---------------------------------------------------------------------------

class TestTriggerCheckTrials:

    URL = 'trigger_check_trials'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command')
    def test_valid_token_returns_200(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['task'] == 'check_trials'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command', side_effect=Exception('err'))
    def test_exception_returns_500(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# trigger_cleanup_notifications
# ---------------------------------------------------------------------------

class TestTriggerCleanupNotifications:

    URL = 'trigger_cleanup_notifications'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command')
    def test_valid_token_returns_200(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['task'] == 'cleanup_notifications'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command', side_effect=Exception('err'))
    def test_exception_returns_500(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# trigger_cobrar_renovaciones
# ---------------------------------------------------------------------------

class TestTriggerCobrarRenovaciones:

    URL = 'trigger_cobrar_renovaciones'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    def test_no_token_returns_401(self):
        client = Client()
        response = client.post(reverse(f'core:{self.URL}'))
        assert response.status_code == 401

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command')
    def test_valid_token_returns_200(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['task'] == 'cobrar_renovaciones'

    @patch('core.views.scheduled_tasks_api.SCHEDULED_TASKS_TOKEN', VALID_TOKEN)
    @patch('django.core.management.call_command', side_effect=Exception('billing error'))
    def test_exception_returns_500(self, mock_cmd):
        response = _post_with_token(self.URL)
        assert response.status_code == 500
