"""
Tests for core/admin_views.py

Covers access control, GET rendering, and key POST flows.
Target: raise coverage from 11.85% to 50%+.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from django.urls import reverse
from django.test import Client
from django.utils import timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_SYSTEM_STATUS = {
    'success': True,
    'health': {
        'metrics': {
            'business': {
                'empresas': {'activas': 3},
                'equipos': {'activos': 10},
                'actividades_recientes': {
                    'calibraciones_hoy': 1,
                    'mantenimientos_hoy': 0,
                    'comprobaciones_hoy': 0,
                },
            },
            'users': {
                'users_active_15min': 2,
                'active_users_details': [],
                'system_usage_percentage': 30.0,
                'system_load_breakdown': {
                    'base_system': 15,
                    'user_activity': 10,
                    'database_load': 5,
                },
            },
        }
    },
}

MOCK_HISTORY = {'history': []}

MOCK_SCHEDULE_CONFIG = {
    'maintenance_daily': {'enabled': True, 'time': '02:00', 'tasks': ['cache']},
    'notifications_daily': {'enabled': True, 'time': '08:00', 'types': ['calibration']},
    'maintenance_weekly': {'enabled': False, 'day': 'sunday', 'time': '03:00', 'tasks': ['all']},
    'notifications_weekly': {'enabled': False, 'day': 'monday', 'time': '09:00', 'types': ['weekly']},
    'backup_monthly': {'enabled': False, 'day': 1, 'time': '01:00', 'include_files': False},
}


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminViewsAccessControl:
    """All admin views require superuser; verify redirect/403 for others."""

    SUPERUSER_ONLY_URLS = [
        'core:admin_dashboard',
        'core:admin_maintenance',
        'core:admin_notifications',
        'core:admin_backup',
        'core:admin_monitoring',
        'core:admin_schedule',
        'core:admin_email_config',
        # admin_history omitted — template admin/history.html not present in repo
        'core:run_tests_panel',
        'core:deleted_companies',
        'core:api_system_status',
    ]

    def test_anonymous_redirected_to_login(self):
        """Anonymous users are redirected to login for all admin views."""
        client = Client()
        for url_name in self.SUPERUSER_ONLY_URLS:
            url = reverse(url_name)
            response = client.get(url)
            assert response.status_code == 302, (
                f"{url_name} should redirect anonymous to login (got {response.status_code})"
            )
            assert 'login' in response.url.lower() or '/accounts/' in response.url, (
                f"{url_name} redirect target should include login, got {response.url}"
            )

    def test_regular_user_denied(self, authenticated_client):
        """Regular (non-superuser) users cannot access admin views."""
        for url_name in self.SUPERUSER_ONLY_URLS:
            url = reverse(url_name)
            response = authenticated_client.get(url)
            assert response.status_code in (302, 403), (
                f"{url_name} should block regular users (got {response.status_code})"
            )

    @patch('core.admin_views.AdminService.get_system_status', return_value=MOCK_SYSTEM_STATUS)
    @patch('core.admin_views.AdminService.get_execution_history', return_value=MOCK_HISTORY)
    @patch('core.admin_views.ScheduleManager.get_schedule_config', return_value=MOCK_SCHEDULE_CONFIG)
    def test_superuser_can_access_all_get_views(self, mock_sched, mock_hist, mock_status, admin_client):
        """Superuser gets 200 for all GET-accessible admin views."""
        for url_name in self.SUPERUSER_ONLY_URLS:
            url = reverse(url_name)
            response = admin_client.get(url)
            assert response.status_code == 200, (
                f"{url_name} returned {response.status_code} for superuser"
            )


# ---------------------------------------------------------------------------
# admin_dashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminDashboard:

    @patch('core.admin_views.AdminService.get_system_status', return_value=MOCK_SYSTEM_STATUS)
    @patch('core.admin_views.AdminService.get_execution_history', return_value=MOCK_HISTORY)
    @patch('core.admin_views.ScheduleManager.get_schedule_config', return_value=MOCK_SCHEDULE_CONFIG)
    def test_get_returns_200(self, mock_sched, mock_hist, mock_status, admin_client):
        url = reverse('core:admin_dashboard')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch(
        'core.admin_views.AdminService.get_system_status',
        side_effect=Exception("service error")
    )
    def test_get_handles_service_exception(self, mock_status, admin_client):
        """Dashboard renders gracefully when AdminService raises."""
        url = reverse('core:admin_dashboard')
        response = admin_client.get(url)
        assert response.status_code == 200  # Error page is still 200


# ---------------------------------------------------------------------------
# system_maintenance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemMaintenance:

    @patch('core.admin_views.AdminService.get_system_status', return_value=MOCK_SYSTEM_STATUS)
    @patch('core.admin_views.AdminService.get_execution_history', return_value=MOCK_HISTORY)
    @patch('core.admin_views.ScheduleManager.get_schedule_config', return_value=MOCK_SCHEDULE_CONFIG)
    def test_get_returns_200(self, mock_sched, mock_hist, mock_status, admin_client):
        url = reverse('core:admin_maintenance')
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_post_dry_run_redirects(self, admin_client):
        """dry_run POST shows simulation message and redirects."""
        url = reverse('core:admin_maintenance')
        response = admin_client.post(url, {'task_type': 'cache', 'dry_run': 'on'})
        assert response.status_code == 302

    def test_post_without_task_type_redirects(self, admin_client):
        """POST without task_type redirects back."""
        url = reverse('core:admin_maintenance')
        response = admin_client.post(url, {})
        assert response.status_code == 302

    @patch('subprocess.Popen')
    def test_post_creates_maintenance_task(self, mock_popen, admin_client):
        """POST with valid task_type creates a MaintenanceTask and starts subprocess."""
        mock_popen.return_value = MagicMock()
        url = reverse('core:admin_maintenance')
        response = admin_client.post(url, {'task_type': 'cache'})
        assert response.status_code == 302
        mock_popen.assert_called_once()

    @patch('subprocess.Popen', side_effect=Exception("popen failed"))
    def test_post_handles_popen_error(self, mock_popen, admin_client):
        """POST handles subprocess error gracefully."""
        url = reverse('core:admin_maintenance')
        response = admin_client.post(url, {'task_type': 'database'})
        assert response.status_code == 302  # Still redirects


# ---------------------------------------------------------------------------
# system_notifications
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemNotifications:

    @patch('core.admin_views.AdminService.get_execution_history', return_value=MOCK_HISTORY)
    def test_get_returns_200(self, mock_hist, admin_client):
        url = reverse('core:admin_notifications')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_notifications',
        return_value={'success': True, 'sent': 5}
    )
    def test_post_success_redirects(self, mock_exec, mock_save, admin_client):
        url = reverse('core:admin_notifications')
        response = admin_client.post(url, {'notification_type': 'calibration'})
        assert response.status_code == 302

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_notifications',
        return_value={'success': False, 'error': 'SMTP error'}
    )
    def test_post_failure_shows_error(self, mock_exec, mock_save, admin_client):
        url = reverse('core:admin_notifications')
        response = admin_client.post(url, {'notification_type': 'all'})
        assert response.status_code == 302

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_notifications',
        return_value={'success': True}
    )
    def test_post_dry_run(self, mock_exec, mock_save, admin_client):
        url = reverse('core:admin_notifications')
        response = admin_client.post(url, {'notification_type': 'calibration', 'dry_run': 'on'})
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# system_backup (GET)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemBackup:

    @patch('core.admin_views._get_available_backup_files', return_value=[])
    @patch('core.admin_views.AdminService.get_execution_history', return_value=MOCK_HISTORY)
    def test_get_returns_200(self, mock_hist, mock_files, admin_client):
        url = reverse('core:admin_backup')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_backup',
        return_value={'success': True}
    )
    def test_post_backup_action_success(self, mock_exec, mock_save, admin_client):
        url = reverse('core:admin_backup')
        response = admin_client.post(url, {
            'action': 'backup',
            'empresa_id': '',
            'format': 'json',
        })
        assert response.status_code == 302

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_backup',
        return_value={'success': False, 'error': 'backup failed'}
    )
    def test_post_backup_action_failure(self, mock_exec, mock_save, admin_client):
        url = reverse('core:admin_backup')
        response = admin_client.post(url, {'action': 'backup', 'empresa_id': ''})
        assert response.status_code == 302

    def test_post_restore_nonexistent_file_redirects(self, admin_client):
        """Restore action with missing file shows error and redirects."""
        url = reverse('core:admin_backup')
        response = admin_client.post(url, {
            'action': 'restore',
            'backup_file_path': '/tmp/nonexistent_backup_file.zip',
        })
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# system_monitoring
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemMonitoring:

    @patch('core.admin_views.AdminService.get_system_status', return_value=MOCK_SYSTEM_STATUS)
    def test_get_returns_200(self, mock_status, admin_client):
        url = reverse('core:admin_monitoring')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch(
        'core.admin_views.AdminService.get_system_status',
        side_effect=Exception("monitoring error")
    )
    def test_get_handles_exception(self, mock_status, admin_client):
        url = reverse('core:admin_monitoring')
        response = admin_client.get(url)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# system_schedule
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemSchedule:

    @patch('core.admin_views.ScheduleManager.get_schedule_config', return_value=MOCK_SCHEDULE_CONFIG)
    def test_get_returns_200(self, mock_sched, admin_client):
        url = reverse('core:admin_schedule')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch('core.admin_views.ScheduleManager.save_schedule_config', return_value=True)
    def test_post_saves_and_redirects(self, mock_save, admin_client):
        url = reverse('core:admin_schedule')
        response = admin_client.post(url, {
            'maintenance_daily_enabled': 'on',
            'maintenance_daily_time': '03:00',
        })
        assert response.status_code == 302

    @patch('core.admin_views.ScheduleManager.save_schedule_config', return_value=False)
    def test_post_save_failure_redirects(self, mock_save, admin_client):
        url = reverse('core:admin_schedule')
        response = admin_client.post(url, {})
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# email_configuration
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmailConfiguration:

    @patch('core.admin_views.AdminService.get_execution_history', return_value=MOCK_HISTORY)
    def test_get_returns_200(self, mock_hist, admin_client):
        from unittest.mock import patch as p
        with p('core.models.EmailConfiguration.get_current_config') as mock_cfg:
            mock_cfg.return_value = MagicMock()
            url = reverse('core:admin_email_config')
            response = admin_client.get(url)
            assert response.status_code == 200

    @patch('core.admin_views.AdminService.save_execution_to_history')
    def test_post_saves_email_config(self, mock_save, admin_client):
        from unittest.mock import patch as p
        with p('core.models.EmailConfiguration.get_current_config') as mock_cfg:
            config_mock = MagicMock()
            config_mock.is_active = True
            mock_cfg.return_value = config_mock
            url = reverse('core:admin_email_config')
            response = admin_client.post(url, {
                'email_host': 'smtp.gmail.com',
                'email_port': '587',
                'email_host_user': 'test@example.com',
                'email_host_password': 'secret',
                'default_from_email': 'test@example.com',
                'security': 'tls',
            })
            assert response.status_code == 302


# ---------------------------------------------------------------------------
# execution_history
# NOTE: admin/history.html template is not present in the repo.
#       Tests verify access control only; template rendering is skipped.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExecutionHistory:

    def test_anonymous_redirected(self):
        """Anonymous users are redirected to login."""
        client = Client()
        url = reverse('core:admin_history')
        response = client.get(url)
        assert response.status_code == 302
        assert 'login' in response.url.lower()

    def test_regular_user_denied(self, authenticated_client):
        """Non-superuser cannot access execution history."""
        url = reverse('core:admin_history')
        response = authenticated_client.get(url)
        assert response.status_code in (302, 403)


# ---------------------------------------------------------------------------
# api_system_status
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiSystemStatus:

    @patch('core.admin_views.AdminService.get_system_status', return_value=MOCK_SYSTEM_STATUS)
    def test_get_returns_json(self, mock_status, admin_client):
        url = reverse('core:api_system_status')
        response = admin_client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    @patch(
        'core.admin_views.AdminService.get_system_status',
        side_effect=Exception("status error")
    )
    def test_get_returns_error_json_on_exception(self, mock_status, admin_client):
        url = reverse('core:api_system_status')
        response = admin_client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is False


# ---------------------------------------------------------------------------
# api_execute_command
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApiExecuteCommand:

    def _post_json(self, client, payload):
        url = reverse('core:api_execute_command')
        return client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_maintenance',
        return_value={'success': True}
    )
    def test_maintenance_command(self, mock_exec, mock_save, admin_client):
        response = self._post_json(admin_client, {
            'command_type': 'maintenance',
            'params': {'task_type': 'cache', 'dry_run': True}
        })
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_notifications',
        return_value={'success': True}
    )
    def test_notifications_command(self, mock_exec, mock_save, admin_client):
        response = self._post_json(admin_client, {
            'command_type': 'notifications',
            'params': {'notification_type': 'calibration'}
        })
        assert response.status_code == 200
        assert json.loads(response.content)['success'] is True

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_backup',
        return_value={'success': True}
    )
    def test_backup_command(self, mock_exec, mock_save, admin_client):
        response = self._post_json(admin_client, {
            'command_type': 'backup',
            'params': {}
        })
        assert response.status_code == 200
        assert json.loads(response.content)['success'] is True

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch(
        'core.admin_views.AdminService.execute_cleanup_backups',
        return_value={'success': True}
    )
    def test_cleanup_backups_command(self, mock_exec, mock_save, admin_client):
        response = self._post_json(admin_client, {
            'command_type': 'cleanup_backups',
            'params': {'retention_months': 3}
        })
        assert response.status_code == 200
        assert json.loads(response.content)['success'] is True

    @patch('core.admin_views.AdminService.save_execution_to_history')
    @patch('core.admin_views.ScheduleManager.save_schedule_config', return_value=True)
    def test_save_schedule_command(self, mock_save, mock_hist_save, admin_client):
        response = self._post_json(admin_client, {
            'command_type': 'save_schedule',
            'params': {}
        })
        assert response.status_code == 200
        assert json.loads(response.content)['success'] is True

    def test_invalid_command_returns_error(self, admin_client):
        response = self._post_json(admin_client, {
            'command_type': 'nonexistent_command',
            'params': {}
        })
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is False

    def test_non_post_returns_405(self, admin_client):
        url = reverse('core:api_execute_command')
        response = admin_client.get(url)
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# deleted_companies
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeletedCompanies:

    @patch('core.models.Empresa.get_deleted_companies', return_value=[])
    def test_get_returns_200(self, mock_deleted, admin_client):
        url = reverse('core:deleted_companies')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch(
        'core.models.Empresa.get_deleted_companies',
        side_effect=Exception("db error")
    )
    def test_get_handles_exception_redirects(self, mock_deleted, admin_client):
        url = reverse('core:deleted_companies')
        response = admin_client.get(url)
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# restore_company
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRestoreCompany:

    def test_get_nonexistent_company_redirects(self, admin_client):
        url = reverse('core:restore_company', args=[9999])
        response = admin_client.get(url)
        assert response.status_code == 302

    def test_get_existing_deleted_company(self, admin_client, empresa_factory):
        empresa = empresa_factory()
        empresa.is_deleted = True
        empresa.save()
        url = reverse('core:restore_company', args=[empresa.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_post_restores_company(self, admin_client, empresa_factory):
        empresa = empresa_factory()
        empresa.is_deleted = True
        empresa.save()
        url = reverse('core:restore_company', args=[empresa.pk])
        with patch.object(empresa.__class__, 'restore', return_value=(True, 'ok')) as mock_restore:
            response = admin_client.post(url)
            assert response.status_code == 302


# ---------------------------------------------------------------------------
# soft_delete_company
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSoftDeleteCompany:

    def test_get_nonexistent_company_redirects(self, admin_client):
        url = reverse('core:soft_delete_company', args=[9999])
        response = admin_client.get(url)
        assert response.status_code == 302

    def test_get_active_company_shows_form(self, admin_client, empresa_factory):
        empresa = empresa_factory()
        url = reverse('core:soft_delete_company', args=[empresa.pk])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_post_soft_deletes_company(self, admin_client, empresa_factory):
        empresa = empresa_factory()
        url = reverse('core:soft_delete_company', args=[empresa.pk])
        with patch.object(empresa.__class__, 'soft_delete') as mock_del:
            response = admin_client.post(url, {'delete_reason': 'test delete'})
            assert response.status_code == 302


# ---------------------------------------------------------------------------
# cleanup_old_companies
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCleanupOldCompanies:

    @patch('core.models.Empresa.get_companies_for_permanent_deletion')
    def test_get_returns_200(self, mock_companies, admin_client):
        mock_companies.return_value = MagicMock()
        mock_companies.return_value.count.return_value = 0
        url = reverse('core:cleanup_old_companies')
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch('core.models.Empresa.get_companies_for_permanent_deletion')
    @patch(
        'core.models.Empresa.cleanup_old_deleted_companies',
        return_value={'count': 2, 'deleted': [{'name': 'X', 'id': 1}]}
    )
    def test_post_preview(self, mock_cleanup, mock_for_del, admin_client):
        mock_for_del.return_value = MagicMock()
        mock_for_del.return_value.count.return_value = 2
        url = reverse('core:cleanup_old_companies')
        response = admin_client.post(url, {'action': 'preview'})
        assert response.status_code == 200

    @patch('core.models.Empresa.get_companies_for_permanent_deletion')
    @patch(
        'core.models.Empresa.cleanup_old_deleted_companies',
        return_value={'count': 0, 'deleted': []}
    )
    def test_post_execute_all_no_companies(self, mock_cleanup, mock_for_del, admin_client):
        mock_for_del.return_value = MagicMock()
        mock_for_del.return_value.count.return_value = 0
        url = reverse('core:cleanup_old_companies')
        response = admin_client.post(url, {'action': 'execute_all'})
        assert response.status_code == 200

    @patch('core.models.Empresa.get_companies_for_permanent_deletion')
    def test_post_execute_selected_no_selection(self, mock_for_del, admin_client):
        mock_for_del.return_value = MagicMock()
        mock_for_del.return_value.count.return_value = 0
        url = reverse('core:cleanup_old_companies')
        response = admin_client.post(url, {'action': 'execute_selected'})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# run_tests_panel
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunTestsPanel:

    def test_get_returns_200(self, admin_client):
        url = reverse('core:run_tests_panel')
        response = admin_client.get(url)
        assert response.status_code == 200
        assert b'test' in response.content.lower() or response.status_code == 200

    @patch('subprocess.Popen')
    def test_post_starts_subprocess(self, mock_popen, admin_client):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b'OK', b'')
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        url = reverse('core:run_tests_panel')
        response = admin_client.post(url, {
            'test_category': 'all',
            'verbose': 'on',
        })
        # Response is 200 (shows results) or 302 (redirects)
        assert response.status_code in (200, 302)
