"""
Tests HTTP para core/views/maintenance.py

Cubre: maintenance_dashboard, create_maintenance_task,
       maintenance_task_detail/list, run_system_health_check,
       system_health_detail/history, task_status_api, task_logs_api.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import Client
from django.urls import reverse

from core.models import (
    Empresa, CustomUser, MaintenanceTask, CommandLog, SystemHealthCheck
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def superuser(db):
    return CustomUser.objects.create_superuser(
        username='maint_superuser',
        password='testpass123',
        email='super@maint.com',
    )


@pytest.fixture
def regular_user(db):
    empresa = Empresa.objects.create(
        nombre='Empresa Maint', nit='900222001-1', email='maint@test.com'
    )
    return CustomUser.objects.create_user(
        username='maint_regular',
        password='testpass123',
        empresa=empresa,
    )


@pytest.fixture
def super_client(db, superuser):
    client = Client()
    client.force_login(superuser)
    return client


@pytest.fixture
def maintenance_task(db, superuser):
    return MaintenanceTask.objects.create(
        task_type='clear_cache',
        status='completed',
        created_by=superuser,
        output='Cache limpiado OK',
    )


@pytest.fixture
def health_check_obj(db, superuser):
    return SystemHealthCheck.objects.create(
        checked_by=superuser,
        overall_status='healthy',
        database_status='healthy',
        cache_status='healthy',
        storage_status='healthy',
        total_empresas=1,
        total_equipos=5,
        total_usuarios=3,
    )


# ---------------------------------------------------------------------------
# Access control — solo superusuarios
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaintenanceAccessControl:

    URLS = [
        'core:maintenance_dashboard',
        'core:maintenance_task_list',
        'core:system_health_history',
    ]

    def test_anonymous_redirected(self):
        client = Client()
        for url_name in self.URLS:
            response = client.get(reverse(url_name))
            assert response.status_code == 302, f'Expected 302 for {url_name}'

    def test_regular_user_redirected(self, db, regular_user):
        client = Client()
        client.force_login(regular_user)
        for url_name in self.URLS:
            response = client.get(reverse(url_name))
            assert response.status_code == 302, f'Expected redirect for {url_name}'

    def test_superuser_can_access_dashboard(self, super_client):
        response = super_client.get(reverse('core:maintenance_dashboard'))
        assert response.status_code == 200

    def test_superuser_can_access_task_list(self, super_client):
        response = super_client.get(reverse('core:maintenance_task_list'))
        assert response.status_code == 200

    def test_superuser_can_access_health_history(self, super_client):
        response = super_client.get(reverse('core:system_health_history'))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# maintenance_dashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaintenanceDashboard:

    def test_get_returns_200(self, super_client):
        response = super_client.get(reverse('core:maintenance_dashboard'))
        assert response.status_code == 200

    def test_context_has_stats(self, super_client):
        response = super_client.get(reverse('core:maintenance_dashboard'))
        ctx = response.context
        for key in ('total_tasks', 'pending_tasks', 'running_tasks', 'system_stats', 'available_tasks'):
            assert key in ctx

    def test_context_system_stats_keys(self, super_client):
        response = super_client.get(reverse('core:maintenance_dashboard'))
        stats = response.context['system_stats']
        assert 'total_empresas' in stats
        assert 'total_equipos' in stats
        assert 'total_usuarios' in stats


# ---------------------------------------------------------------------------
# create_maintenance_task
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCreateMaintenanceTask:

    URL = 'core:create_maintenance_task'

    def test_anonymous_redirected(self):
        client = Client()
        response = client.post(reverse(self.URL), {'task_type': 'clear_cache'})
        assert response.status_code == 302

    def test_get_redirects_to_dashboard(self, super_client):
        response = super_client.get(reverse(self.URL))
        assert response.status_code == 302

    def test_post_without_task_type_redirects(self, super_client):
        response = super_client.post(reverse(self.URL), {})
        assert response.status_code == 302

    @patch('subprocess.Popen')
    def test_post_creates_task_and_redirects(self, mock_popen, super_client, superuser):
        mock_popen.return_value = MagicMock()
        response = super_client.post(reverse(self.URL), {'task_type': 'clear_cache'})
        assert response.status_code == 302
        assert MaintenanceTask.objects.filter(task_type='clear_cache').exists()

    @patch('subprocess.Popen')
    def test_post_existing_pending_task_redirects_with_warning(self, mock_popen, super_client, superuser):
        MaintenanceTask.objects.create(
            task_type='backup_db', status='pending', created_by=superuser
        )
        response = super_client.post(reverse(self.URL), {'task_type': 'backup_db'})
        assert response.status_code == 302

    @patch('subprocess.Popen', side_effect=OSError('no python'))
    def test_post_popen_error_marks_task_failed(self, mock_popen, super_client, superuser):
        response = super_client.post(reverse(self.URL), {'task_type': 'collect_static'})
        assert response.status_code == 302
        task = MaintenanceTask.objects.filter(task_type='collect_static').first()
        if task:
            assert task.status == 'failed'


# ---------------------------------------------------------------------------
# maintenance_task_detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaintenanceTaskDetail:

    def test_get_existing_task_returns_200(self, super_client, maintenance_task):
        url = reverse('core:maintenance_task_detail', args=[maintenance_task.id])
        response = super_client.get(url)
        assert response.status_code == 200

    def test_get_nonexistent_task_returns_404(self, super_client):
        url = reverse('core:maintenance_task_detail', args=[99999])
        response = super_client.get(url)
        assert response.status_code == 404

    def test_context_has_task(self, super_client, maintenance_task):
        url = reverse('core:maintenance_task_detail', args=[maintenance_task.id])
        response = super_client.get(url)
        assert response.context['task'] == maintenance_task


# ---------------------------------------------------------------------------
# maintenance_task_list — filtros
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMaintenanceTaskList:

    def test_get_empty_list_returns_200(self, super_client):
        response = super_client.get(reverse('core:maintenance_task_list'))
        assert response.status_code == 200

    def test_filter_by_status(self, super_client, maintenance_task):
        response = super_client.get(
            reverse('core:maintenance_task_list'), {'status': 'completed'}
        )
        assert response.status_code == 200

    def test_filter_by_task_type(self, super_client, maintenance_task):
        response = super_client.get(
            reverse('core:maintenance_task_list'), {'task_type': 'clear_cache'}
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# run_system_health_check
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunSystemHealthCheck:

    URL = 'core:run_system_health_check'

    MOCK_HEALTH_DATA = {
        'metrics': {
            'business': {'total_empresas': 2, 'total_equipos': 10},
            'users': {'total_usuarios': 5},
        }
    }

    def test_get_redirects_to_dashboard(self, super_client):
        response = super_client.get(reverse(self.URL))
        assert response.status_code == 302

    @patch('core.views.maintenance.SystemMonitor.get_system_health')
    def test_post_creates_health_check_and_redirects(self, mock_health, super_client):
        mock_health.return_value = self.MOCK_HEALTH_DATA
        response = super_client.post(reverse(self.URL))
        assert response.status_code == 302
        assert SystemHealthCheck.objects.count() == 1

    @patch('core.views.maintenance.SystemMonitor.get_system_health',
           side_effect=Exception('monitor failed'))
    def test_post_exception_redirects_to_dashboard(self, mock_health, super_client):
        response = super_client.post(reverse(self.URL))
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# system_health_detail
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemHealthDetail:

    def test_existing_check_returns_200(self, super_client, health_check_obj):
        url = reverse('core:system_health_detail', args=[health_check_obj.id])
        response = super_client.get(url)
        assert response.status_code == 200

    def test_nonexistent_check_returns_404(self, super_client):
        url = reverse('core:system_health_detail', args=[99999])
        response = super_client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# system_health_history
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSystemHealthHistory:

    def test_get_returns_200(self, super_client):
        response = super_client.get(reverse('core:system_health_history'))
        assert response.status_code == 200

    def test_with_checks_paginates(self, super_client, superuser):
        for i in range(25):
            SystemHealthCheck.objects.create(
                checked_by=superuser,
                overall_status='healthy',
                database_status='healthy',
                cache_status='healthy',
                storage_status='healthy',
            )
        response = super_client.get(reverse('core:system_health_history'))
        assert response.status_code == 200
        assert 'page_obj' in response.context


# ---------------------------------------------------------------------------
# task_status_api
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskStatusApi:

    def test_existing_task_returns_json(self, super_client, maintenance_task):
        url = reverse('core:task_status_api', args=[maintenance_task.id])
        response = super_client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['task']['id'] == maintenance_task.id
        assert data['task']['status'] == 'completed'

    def test_nonexistent_task_returns_404(self, super_client):
        url = reverse('core:task_status_api', args=[99999])
        response = super_client.get(url)
        assert response.status_code == 404
        data = json.loads(response.content)
        assert data['success'] is False

    def test_completed_task_has_100_progress(self, super_client, maintenance_task):
        url = reverse('core:task_status_api', args=[maintenance_task.id])
        data = json.loads(super_client.get(url).content)
        assert data['task']['progress'] == 100


# ---------------------------------------------------------------------------
# task_logs_api
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaskLogsApi:

    def test_existing_task_no_logs_returns_empty_list(self, super_client, maintenance_task):
        url = reverse('core:task_logs_api', args=[maintenance_task.id])
        response = super_client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['logs'] == []
        assert data['total'] == 0

    def test_existing_task_with_logs(self, super_client, maintenance_task):
        CommandLog.objects.create(
            task=maintenance_task,
            level='INFO',
            message='Tarea iniciada',
        )
        url = reverse('core:task_logs_api', args=[maintenance_task.id])
        data = json.loads(super_client.get(url).content)
        assert data['total'] == 1
        assert data['logs'][0]['message'] == 'Tarea iniciada'

    def test_nonexistent_task_returns_404(self, super_client):
        url = reverse('core:task_logs_api', args=[99999])
        response = super_client.get(url)
        assert response.status_code == 404
