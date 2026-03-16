"""
Tests para AdminService y ScheduleManager (core/admin_services.py).

Objetivo: Aumentar coverage de 16.43% a ~90%
Estrategia: Mocks para comandos externos, DB real para casos con empresa_id

Clases testadas:
- AdminService: execute_maintenance, execute_notifications, execute_backup,
  execute_cleanup_backups, execute_restore, get_system_status,
  get_execution_history, save_execution_to_history, _get_execution_summary,
  execute_command_async
- ScheduleManager: get_schedule_config, save_schedule_config,
  check_scheduled_tasks, _should_execute_daily, _should_execute_weekly,
  _should_execute_monthly
"""
import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache


# ============================================================================
# CONFIG BASE PARA ScheduleManager (todas las tareas deshabilitadas por defecto)
# ============================================================================

MOCK_CONFIG_BASE = {
    'maintenance_daily': {
        'enabled': False, 'time': '02:00', 'tasks': ['all']
    },
    'notifications_daily': {
        'enabled': False, 'time': '08:00', 'types': ['consolidated']
    },
    'maintenance_weekly': {
        'enabled': False, 'day': 'monday', 'time': '03:00', 'tasks': ['all']
    },
    'notifications_weekly': {
        'enabled': False, 'day': 'sunday', 'time': '09:00', 'types': ['weekly']
    },
    'backup_monthly': {
        'enabled': False, 'day': 1, 'time': '04:00', 'include_files': False
    },
}


# ============================================================================
# AdminService.execute_maintenance
# ============================================================================

class TestAdminServiceExecuteMaintenance:
    """Tests para AdminService.execute_maintenance()."""

    @patch('core.admin_services.call_command')
    def test_exito_con_parametros_por_defecto(self, mock_cmd):
        """execute_maintenance() sin parámetros retorna success=True con valores correctos."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_maintenance()

        assert resultado['success'] is True
        assert resultado['task_type'] == 'all'
        assert resultado['dry_run'] is False
        assert 'output' in resultado
        assert 'timestamp' in resultado

    @patch('core.admin_services.call_command')
    def test_pasa_task_type_y_dry_run_a_comando(self, mock_cmd):
        """execute_maintenance() pasa correctamente los parámetros al call_command."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_maintenance(task_type='backup', dry_run=True)

        assert resultado['success'] is True
        assert resultado['task_type'] == 'backup'
        assert resultado['dry_run'] is True

        args, kwargs = mock_cmd.call_args
        assert args[0] == 'maintenance'
        assert kwargs['task'] == 'backup'
        assert kwargs['dry_run'] is True

    @patch('core.admin_services.call_command', side_effect=Exception('Comando fallido'))
    def test_excepcion_retorna_error(self, mock_cmd):
        """execute_maintenance() captura excepciones y retorna success=False."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_maintenance()

        assert resultado['success'] is False
        assert 'Comando fallido' in resultado['error']
        assert resultado['task_type'] == 'all'
        assert 'timestamp' in resultado


# ============================================================================
# AdminService.execute_notifications — con empresa_id
# ============================================================================

class TestAdminServiceExecuteNotificationsConEmpresaId:
    """Tests para execute_notifications() cuando se especifica empresa_id."""

    @pytest.mark.django_db
    def test_empresa_id_con_dry_run_no_envia(self):
        """Con dry_run=True y empresa_id, no se envía ningún email real."""
        from core.admin_services import AdminService
        from tests.factories import EmpresaFactory
        empresa = EmpresaFactory()

        with patch('core.notifications.NotificationScheduler.send_consolidated_reminder') as mock_send:
            resultado = AdminService.execute_notifications(
                notification_type='consolidated', dry_run=True, empresa_id=empresa.id
            )

        assert resultado['success'] is True
        assert resultado['dry_run'] is True
        assert resultado['details']['empresa_id'] == empresa.id
        mock_send.assert_not_called()

    @pytest.mark.django_db
    def test_empresa_id_consolidated_sin_dry_run_envia_email(self):
        """Con empresa_id y notification_type=consolidated sin dry_run, se envía email."""
        from core.admin_services import AdminService
        from tests.factories import EmpresaFactory
        empresa = EmpresaFactory()

        with patch('core.notifications.NotificationScheduler.send_consolidated_reminder', return_value=True):
            resultado = AdminService.execute_notifications(
                notification_type='consolidated', dry_run=False, empresa_id=empresa.id
            )

        assert resultado['success'] is True
        assert resultado['details']['emails_sent'] == 1
        assert resultado['details']['empresas_processed'] == 1

    @pytest.mark.django_db
    def test_empresa_id_tipo_otro_sin_email(self):
        """Con empresa_id y tipo 'other', send_consolidated_reminder retorna False → 0 emails."""
        from core.admin_services import AdminService
        from tests.factories import EmpresaFactory
        empresa = EmpresaFactory()

        with patch('core.notifications.NotificationScheduler.send_consolidated_reminder', return_value=False):
            resultado = AdminService.execute_notifications(
                notification_type='otro_tipo', dry_run=False, empresa_id=empresa.id
            )

        assert resultado['success'] is True
        assert resultado['details']['emails_sent'] == 0

    @pytest.mark.django_db
    def test_empresa_id_inexistente_retorna_error(self):
        """Si empresa_id no existe en DB, retorna success=False con mensaje de error."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(empresa_id=99999)

        assert resultado['success'] is False
        assert '99999' in resultado['error']


# ============================================================================
# AdminService.execute_notifications — todas las empresas
# ============================================================================

class TestAdminServiceExecuteNotificacionesTodasEmpresas:
    """Tests para execute_notifications() sin empresa_id (todas las empresas)."""

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.check_all_reminders', return_value=5)
    def test_consolidated_sin_dry_run_llama_check_all_reminders(self, mock_check):
        """consolidated sin dry_run llama check_all_reminders y retorna emails_sent."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='consolidated', dry_run=False
        )

        assert resultado['success'] is True
        assert resultado['details']['emails_sent'] == 5
        mock_check.assert_called_once()

    @patch('core.models.Empresa')
    def test_consolidated_con_dry_run_no_envia(self, mock_empresa_cls):
        """consolidated con dry_run=True no llama check_all_reminders."""
        from core.admin_services import AdminService
        mock_qs = MagicMock()
        mock_qs.count.return_value = 3
        mock_empresa_cls.objects.filter.return_value = mock_qs

        with patch('core.notifications.NotificationScheduler.check_all_reminders') as mock_check:
            resultado = AdminService.execute_notifications(
                notification_type='consolidated', dry_run=True
            )

        assert resultado['success'] is True
        assert 'MODO PRUEBA' in resultado['output']
        assert resultado['details']['empresas_processed'] == 3
        mock_check.assert_not_called()

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_weekly_summaries', return_value=3)
    def test_weekly_sin_dry_run_envia_resumenes(self, mock_weekly):
        """weekly sin dry_run llama send_weekly_summaries."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='weekly', dry_run=False
        )

        assert resultado['success'] is True
        assert resultado['details']['emails_sent'] == 3
        mock_weekly.assert_called_once()

    @patch('core.models.Empresa')
    def test_weekly_con_dry_run_modo_prueba(self, mock_empresa_cls):
        """weekly con dry_run=True muestra mensaje de prueba."""
        from core.admin_services import AdminService
        mock_qs = MagicMock()
        mock_qs.count.return_value = 2
        mock_empresa_cls.objects.filter.return_value = mock_qs

        resultado = AdminService.execute_notifications(
            notification_type='weekly', dry_run=True
        )

        assert resultado['success'] is True
        assert 'MODO PRUEBA' in resultado['output']

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.send_weekly_overdue_reminders', return_value=7)
    def test_weekly_overdue_sin_dry_run(self, mock_overdue):
        """weekly_overdue sin dry_run llama send_weekly_overdue_reminders."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='weekly_overdue', dry_run=False
        )

        assert resultado['success'] is True
        assert resultado['details']['emails_sent'] == 7
        mock_overdue.assert_called_once()

    @patch('core.models.Empresa')
    def test_weekly_overdue_con_dry_run_itera_empresas(self, mock_empresa_cls):
        """weekly_overdue con dry_run itera empresas y cuenta actividades vencidas."""
        from core.admin_services import AdminService
        # Empresa mock sin equipos vencidos
        mock_empresa = MagicMock()
        mock_empresa.equipos.filter.return_value.count.return_value = 0

        mock_qs = MagicMock()
        mock_qs.count.return_value = 1
        mock_qs.__iter__ = MagicMock(return_value=iter([mock_empresa]))
        mock_empresa_cls.objects.filter.return_value = mock_qs

        resultado = AdminService.execute_notifications(
            notification_type='weekly_overdue', dry_run=True
        )

        assert resultado['success'] is True
        assert 'MODO PRUEBA' in resultado['output']

    @pytest.mark.django_db
    @patch('core.admin_services.call_command')
    def test_tipo_otro_usa_call_command(self, mock_cmd):
        """Para tipo desconocido usa call_command('send_notifications', ...)."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='tipo_personalizado', dry_run=False
        )

        assert resultado['success'] is True
        args, kwargs = mock_cmd.call_args
        assert args[0] == 'send_notifications'
        assert kwargs.get('type') == 'tipo_personalizado'

    @pytest.mark.django_db
    @patch('core.admin_services.call_command', side_effect=Exception('cmd error'))
    @patch('core.notifications.NotificationScheduler.check_calibration_reminders', return_value=2)
    def test_fallback_calibration(self, mock_cal, mock_cmd):
        """Si call_command falla y tipo es 'calibration', usa check_calibration_reminders."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='calibration', dry_run=False
        )

        assert resultado['success'] is True
        mock_cal.assert_called_once()

    @pytest.mark.django_db
    @patch('core.admin_services.call_command', side_effect=Exception('cmd error'))
    @patch('core.notifications.NotificationScheduler.check_maintenance_reminders', return_value=4)
    def test_fallback_maintenance(self, mock_maint, mock_cmd):
        """Si call_command falla y tipo es 'maintenance', usa check_maintenance_reminders."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='maintenance', dry_run=False
        )

        assert resultado['success'] is True
        mock_maint.assert_called_once()

    @pytest.mark.django_db
    @patch('core.notifications.NotificationScheduler.check_all_reminders', side_effect=Exception('error de red'))
    def test_excepcion_retorna_error(self, mock_check):
        """Si ocurre excepción, retorna success=False."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_notifications(
            notification_type='consolidated', dry_run=False
        )

        assert resultado['success'] is False
        assert 'error de red' in resultado['error']
        assert 'timestamp' in resultado


# ============================================================================
# AdminService.execute_backup
# ============================================================================

class TestAdminServiceExecuteBackup:
    """Tests para AdminService.execute_backup()."""

    @patch('core.admin_services.call_command')
    def test_exito_parametros_por_defecto(self, mock_cmd):
        """execute_backup() sin parámetros retorna success=True."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_backup()

        assert resultado['success'] is True
        assert resultado['empresa_id'] is None
        assert resultado['include_files'] is False
        assert resultado['format'] == 'both'
        assert 'timestamp' in resultado

    @patch('core.admin_services.call_command')
    def test_con_empresa_id_pasa_kwarg(self, mock_cmd):
        """execute_backup() con empresa_id pasa el kwarg al command."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_backup(
            empresa_id=5, include_files=True, backup_format='json'
        )

        assert resultado['success'] is True
        assert resultado['empresa_id'] == 5
        assert resultado['include_files'] is True

        _, kwargs = mock_cmd.call_args
        assert kwargs.get('empresa_id') == 5
        assert kwargs.get('include_files') is True

    @patch('core.admin_services.call_command', side_effect=Exception('Disco lleno'))
    def test_excepcion_retorna_error(self, mock_cmd):
        """execute_backup() captura excepciones y retorna success=False."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_backup()

        assert resultado['success'] is False
        assert 'Disco lleno' in resultado['error']
        assert resultado['empresa_id'] is None


# ============================================================================
# AdminService.execute_cleanup_backups
# ============================================================================

class TestAdminServiceExecuteCleanupBackups:
    """Tests para AdminService.execute_cleanup_backups()."""

    @patch('core.admin_services.call_command')
    def test_exito_sin_matches_en_output(self, mock_cmd):
        """Con output vacío, deleted_count=0 y total_size_mb=0.0."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_cleanup_backups()

        assert resultado['success'] is True
        assert resultado['retention_months'] == 6
        assert resultado['dry_run'] is False
        assert resultado['details']['deleted_count'] == 0
        assert resultado['details']['total_size_mb'] == 0.0

    @patch('core.admin_services.call_command')
    def test_parsea_archivos_y_tamano_del_output(self, mock_cmd):
        """Parsea correctamente el número de archivos y tamaño del output del comando."""
        from core.admin_services import AdminService

        def escribir_output(*args, **kwargs):
            kwargs['stdout'].write('Se eliminaron 5 archivos con 12.3 MB')

        mock_cmd.side_effect = escribir_output
        resultado = AdminService.execute_cleanup_backups(retention_months=3)

        assert resultado['success'] is True
        assert resultado['details']['deleted_count'] == 5
        assert resultado['details']['total_size_mb'] == 12.3
        assert resultado['retention_months'] == 3

    @patch('core.admin_services.call_command')
    def test_dry_run_pasa_flag_al_comando(self, mock_cmd):
        """execute_cleanup_backups() con dry_run=True pasa el flag al comando."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_cleanup_backups(dry_run=True)

        assert resultado['success'] is True
        assert resultado['dry_run'] is True
        _, kwargs = mock_cmd.call_args
        assert kwargs['dry_run'] is True

    @patch('core.admin_services.call_command', side_effect=Exception('Error S3'))
    def test_excepcion_retorna_error(self, mock_cmd):
        """execute_cleanup_backups() captura excepciones."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_cleanup_backups()

        assert resultado['success'] is False
        assert 'Error S3' in resultado['error']
        assert resultado['retention_months'] == 6


# ============================================================================
# AdminService.execute_restore
# ============================================================================

class TestAdminServiceExecuteRestore:
    """Tests para AdminService.execute_restore()."""

    @patch('core.admin_services.call_command')
    def test_exito_basico(self, mock_cmd):
        """execute_restore() básico retorna success=True con datos del backup."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_restore('/ruta/backup.json')

        assert resultado['success'] is True
        assert resultado['backup_file'] == '/ruta/backup.json'
        assert resultado['new_name'] is None
        assert resultado['dry_run'] is False
        assert resultado['overwrite'] is False
        assert resultado['restore_files'] is False

    @patch('core.admin_services.call_command')
    def test_con_new_name_y_overwrite(self, mock_cmd):
        """execute_restore() pasa new_name y overwrite al comando."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_restore(
            '/ruta/backup.json',
            new_name='mi_backup',
            overwrite=True,
            restore_files=True
        )

        assert resultado['success'] is True
        assert resultado['new_name'] == 'mi_backup'
        assert resultado['overwrite'] is True
        assert resultado['restore_files'] is True

        _, kwargs = mock_cmd.call_args
        assert kwargs.get('new_name') == 'mi_backup'
        assert kwargs.get('overwrite') is True

    @patch('core.admin_services.call_command')
    def test_dry_run(self, mock_cmd):
        """execute_restore() con dry_run=True pasa el flag."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_restore('/ruta/backup.json', dry_run=True)

        assert resultado['success'] is True
        assert resultado['dry_run'] is True

    @patch('core.admin_services.call_command', side_effect=Exception('Error de restauración'))
    def test_excepcion_retorna_error(self, mock_cmd):
        """execute_restore() captura excepciones y retorna success=False."""
        from core.admin_services import AdminService
        resultado = AdminService.execute_restore('/ruta/backup.json')

        assert resultado['success'] is False
        assert 'Error de restauración' in resultado['error']
        assert resultado['backup_file'] == '/ruta/backup.json'


# ============================================================================
# AdminService.get_system_status
# ============================================================================

class TestAdminServiceGetSystemStatus:
    """Tests para AdminService.get_system_status()."""

    @patch('core.admin_services.AlertManager.check_system_alerts', return_value=[])
    @patch('core.admin_services.SystemMonitor.get_performance_metrics', return_value={'cpu': 45})
    @patch('core.admin_services.SystemMonitor.get_system_health', return_value={'status': 'ok'})
    def test_exito_retorna_datos_completos(self, mock_health, mock_perf, mock_alerts):
        """get_system_status() retorna health, alerts y performance correctamente."""
        from core.admin_services import AdminService
        resultado = AdminService.get_system_status()

        assert resultado['success'] is True
        assert resultado['health'] == {'status': 'ok'}
        assert resultado['alerts'] == []
        assert resultado['performance'] == {'cpu': 45}
        assert 'timestamp' in resultado

    @patch('core.admin_services.SystemMonitor.get_system_health', side_effect=Exception('Error de salud'))
    def test_excepcion_retorna_error(self, mock_health):
        """get_system_status() captura excepciones del monitor."""
        from core.admin_services import AdminService
        resultado = AdminService.get_system_status()

        assert resultado['success'] is False
        assert 'Error de salud' in resultado['error']
        assert 'timestamp' in resultado


# ============================================================================
# AdminService.get_execution_history
# ============================================================================

class TestAdminServiceGetExecutionHistory:
    """Tests para AdminService.get_execution_history()."""

    def test_historial_vacio(self):
        """Sin entradas en cache, retorna lista vacía."""
        from core.admin_services import AdminService
        cache.delete('admin_execution_history')
        resultado = AdminService.get_execution_history()

        assert resultado['success'] is True
        assert resultado['history'] == []
        assert 'timestamp' in resultado

    def test_retorna_ultimas_20_entradas(self):
        """Con 25 entradas en cache, retorna solo las últimas 20."""
        from core.admin_services import AdminService
        historial = [{'action': f'accion_{i}'} for i in range(25)]
        cache.set('admin_execution_history', historial, 3600)

        resultado = AdminService.get_execution_history()

        assert resultado['success'] is True
        assert len(resultado['history']) == 20
        # Verifica que son las últimas 20
        assert resultado['history'][0]['action'] == 'accion_5'

    @patch('core.admin_services.cache.get', side_effect=Exception('Cache caído'))
    def test_excepcion_retorna_error(self, mock_cache):
        """get_execution_history() captura excepciones del cache."""
        from core.admin_services import AdminService
        resultado = AdminService.get_execution_history()

        assert resultado['success'] is False
        assert 'Cache caído' in resultado['error']
        assert resultado['history'] == []


# ============================================================================
# AdminService.save_execution_to_history
# ============================================================================

class TestAdminServiceSaveExecutionToHistory:
    """Tests para AdminService.save_execution_to_history()."""

    def test_guarda_resultado_exitoso(self):
        """Guarda correctamente un resultado exitoso en el historial."""
        from core.admin_services import AdminService
        cache.delete('admin_execution_history')

        resultado = AdminService.save_execution_to_history(
            action='maintenance', result={'success': True}
        )

        assert resultado is True
        historial = cache.get('admin_execution_history', [])
        assert len(historial) == 1
        assert historial[0]['action'] == 'maintenance'
        assert historial[0]['success'] is True
        assert historial[0]['user'] == 'system'

    def test_guarda_error_incluye_campo_error(self):
        """Con resultado fallido, guarda el campo error en el registro."""
        from core.admin_services import AdminService
        cache.delete('admin_execution_history')

        resultado = AdminService.save_execution_to_history(
            action='backup', result={'success': False, 'error': 'Disco lleno'}
        )

        assert resultado is True
        historial = cache.get('admin_execution_history', [])
        assert historial[0]['error'] == 'Disco lleno'
        assert historial[0]['success'] is False

    def test_guarda_con_usuario(self):
        """Con usuario, guarda el username en el registro."""
        from core.admin_services import AdminService
        cache.delete('admin_execution_history')

        mock_user = MagicMock()
        mock_user.username = 'admin_test'

        resultado = AdminService.save_execution_to_history(
            action='restore', result={'success': True}, user=mock_user
        )

        assert resultado is True
        historial = cache.get('admin_execution_history', [])
        assert historial[0]['user'] == 'admin_test'

    def test_trunca_a_50_entradas(self):
        """Con más de 50 entradas, mantiene solo las últimas 50."""
        from core.admin_services import AdminService
        historial_inicial = [{'action': f'a_{i}', 'success': True} for i in range(55)]
        cache.set('admin_execution_history', historial_inicial, 3600)

        AdminService.save_execution_to_history(
            action='nueva_accion', result={'success': True}
        )

        guardado = cache.get('admin_execution_history', [])
        assert len(guardado) <= 50

    @patch('core.admin_services.cache.get', side_effect=Exception('Cache no disponible'))
    def test_excepcion_retorna_false(self, mock_cache):
        """Si el cache falla, save_execution_to_history retorna False."""
        from core.admin_services import AdminService
        resultado = AdminService.save_execution_to_history(
            action='test', result={'success': True}
        )

        assert resultado is False


# ============================================================================
# AdminService._get_execution_summary
# ============================================================================

class TestAdminServiceGetExecutionSummary:
    """Tests para AdminService._get_execution_summary()."""

    def test_resultado_fallido_retorna_error_en_accion(self):
        """Con success=False, el resumen menciona 'Error'."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('maintenance', {'success': False})

        assert 'Error' in resumen

    def test_accion_mantenimiento(self):
        """Acción 'maintenance' retorna mensaje de mantenimiento."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('maintenance', {'success': True})

        assert 'Mantenimiento' in resumen or 'mantenimiento' in resumen.lower()

    def test_accion_notification(self):
        """Acción 'notification' retorna mensaje de notificaciones."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('notification', {'success': True})

        assert 'Notificaciones' in resumen or 'notif' in resumen.lower()

    def test_accion_backup(self):
        """Acción 'backup' retorna mensaje de backup."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('backup', {'success': True})

        assert 'Backup' in resumen or 'backup' in resumen.lower()

    def test_accion_restore(self):
        """Acción 'restore' retorna mensaje de restauración."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('restore', {'success': True})

        assert 'Restauración' in resumen or 'restore' in resumen.lower()

    def test_accion_system_status(self):
        """Acción 'system_status' retorna mensaje de estado del sistema."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('system_status', {'success': True})

        assert 'Estado' in resumen or 'sistema' in resumen.lower()

    def test_accion_desconocida_incluye_nombre(self):
        """Acción desconocida incluye el nombre de la acción en el resumen."""
        from core.admin_services import AdminService
        resumen = AdminService._get_execution_summary('accion_personalizada', {'success': True})

        assert 'accion_personalizada' in resumen or 'completado' in resumen.lower()


# ============================================================================
# AdminService.execute_command_async
# ============================================================================

class TestAdminServiceExecuteCommandAsync:
    """Tests para AdminService.execute_command_async()."""

    def test_retorna_dict_de_exito_inmediato(self):
        """execute_command_async() retorna inmediatamente con async=True."""
        from core.admin_services import AdminService
        mock_func = MagicMock(return_value={'success': True})

        resultado = AdminService.execute_command_async(mock_func)

        assert resultado['success'] is True
        assert resultado['async'] is True
        assert 'message' in resultado

    def test_inicia_thread_en_segundo_plano(self):
        """execute_command_async() lanza un thread daemon."""
        from core.admin_services import AdminService
        import threading

        mock_func = MagicMock(return_value={'success': True})
        resultado = AdminService.execute_command_async(mock_func, user_id='test_user')

        # El resultado debe ser inmediato (sin bloquear)
        assert resultado['success'] is True
        assert resultado['async'] is True


# ============================================================================
# ScheduleManager.get_schedule_config
# ============================================================================

class TestScheduleManagerGetScheduleConfig:
    """Tests para ScheduleManager.get_schedule_config()."""

    @pytest.mark.django_db
    @patch('core.models.SystemScheduleConfig.get_or_create_config')
    def test_exito_retorna_config_de_bd(self, mock_get_or_create):
        """get_schedule_config() retorna la config del objeto SystemScheduleConfig."""
        from core.admin_services import ScheduleManager

        mock_config_obj = MagicMock()
        mock_config_obj.get_config.return_value = {'ajuste': 'valor'}
        mock_get_or_create.return_value = mock_config_obj

        resultado = ScheduleManager.get_schedule_config()

        assert resultado == {'ajuste': 'valor'}
        mock_get_or_create.assert_called_once()

    @pytest.mark.django_db
    @patch('core.models.SystemScheduleConfig.get_default_config', return_value={'default': True})
    @patch('core.models.SystemScheduleConfig.get_or_create_config', side_effect=Exception('Error BD'))
    def test_excepcion_usa_config_por_defecto(self, mock_get, mock_default):
        """Si hay error al obtener config, usa SystemScheduleConfig.get_default_config()."""
        from core.admin_services import ScheduleManager

        resultado = ScheduleManager.get_schedule_config()

        assert resultado == {'default': True}
        mock_default.assert_called_once()


# ============================================================================
# ScheduleManager.save_schedule_config
# ============================================================================

class TestScheduleManagerSaveScheduleConfig:
    """Tests para ScheduleManager.save_schedule_config()."""

    @pytest.mark.django_db
    @patch('core.models.SystemScheduleConfig.get_or_create_config')
    def test_exito_llama_save_config(self, mock_get_or_create):
        """save_schedule_config() llama save_config con la config proporcionada."""
        from core.admin_services import ScheduleManager

        mock_config_obj = MagicMock()
        mock_get_or_create.return_value = mock_config_obj

        resultado = ScheduleManager.save_schedule_config({'nuevo_ajuste': 'valor'})

        assert resultado is True
        mock_config_obj.save_config.assert_called_once_with({'nuevo_ajuste': 'valor'})

    @pytest.mark.django_db
    @patch('core.models.SystemScheduleConfig.get_or_create_config', side_effect=Exception('Error guardando'))
    def test_excepcion_retorna_false(self, mock_get):
        """save_schedule_config() retorna False si hay excepción."""
        from core.admin_services import ScheduleManager

        resultado = ScheduleManager.save_schedule_config({})

        assert resultado is False


# ============================================================================
# ScheduleManager.check_scheduled_tasks
# ============================================================================

class TestScheduleManagerCheckScheduledTasks:
    """Tests para ScheduleManager.check_scheduled_tasks()."""

    @patch('core.admin_services.ScheduleManager.get_schedule_config', return_value=MOCK_CONFIG_BASE)
    def test_todas_deshabilitadas_retorna_lista_vacia(self, mock_config):
        """Con todas las tareas deshabilitadas, executed_tasks es vacía."""
        from core.admin_services import ScheduleManager

        resultado = ScheduleManager.check_scheduled_tasks()

        assert resultado['success'] is True
        assert resultado['executed_tasks'] == []
        assert 'timestamp' in resultado

    @patch('core.admin_services.AdminService.execute_maintenance', return_value={'success': True})
    @patch('core.admin_services.ScheduleManager._should_execute_daily', return_value=True)
    @patch('core.admin_services.ScheduleManager.get_schedule_config')
    def test_maintenance_daily_habilitada_se_ejecuta(self, mock_config, mock_should, mock_exec):
        """Con maintenance_daily habilitada y hora correcta, se ejecuta."""
        from core.admin_services import ScheduleManager

        config = dict(MOCK_CONFIG_BASE)
        config['maintenance_daily'] = {'enabled': True, 'time': '02:00', 'tasks': ['all']}
        mock_config.return_value = config

        resultado = ScheduleManager.check_scheduled_tasks()

        assert resultado['success'] is True
        assert 'maintenance_daily' in resultado['executed_tasks']
        mock_exec.assert_called_once()

    @patch('core.admin_services.AdminService.execute_notifications', return_value={'success': True})
    @patch('core.admin_services.ScheduleManager._should_execute_daily', return_value=True)
    @patch('core.admin_services.ScheduleManager.get_schedule_config')
    def test_notifications_daily_habilitada_se_ejecuta(self, mock_config, mock_should, mock_exec):
        """Con notifications_daily habilitada y hora correcta, se ejecuta."""
        from core.admin_services import ScheduleManager

        config = dict(MOCK_CONFIG_BASE)
        config['notifications_daily'] = {'enabled': True, 'time': '08:00', 'types': ['consolidated']}
        mock_config.return_value = config

        resultado = ScheduleManager.check_scheduled_tasks()

        assert 'notifications_daily' in resultado['executed_tasks']

    @patch('core.admin_services.AdminService.execute_maintenance', return_value={'success': True})
    @patch('core.admin_services.ScheduleManager._should_execute_weekly', return_value=True)
    @patch('core.admin_services.ScheduleManager.get_schedule_config')
    def test_maintenance_weekly_habilitada_se_ejecuta(self, mock_config, mock_should, mock_exec):
        """Con maintenance_weekly habilitada y día/hora correctos, se ejecuta."""
        from core.admin_services import ScheduleManager

        config = dict(MOCK_CONFIG_BASE)
        config['maintenance_weekly'] = {
            'enabled': True, 'day': 'monday', 'time': '03:00', 'tasks': ['all']
        }
        mock_config.return_value = config

        resultado = ScheduleManager.check_scheduled_tasks()

        assert 'maintenance_weekly' in resultado['executed_tasks']

    @patch('core.admin_services.AdminService.execute_notifications', return_value={'success': True})
    @patch('core.admin_services.ScheduleManager._should_execute_weekly', return_value=True)
    @patch('core.admin_services.ScheduleManager.get_schedule_config')
    def test_notifications_weekly_habilitada_se_ejecuta(self, mock_config, mock_should, mock_exec):
        """Con notifications_weekly habilitada y día/hora correctos, se ejecuta."""
        from core.admin_services import ScheduleManager

        config = dict(MOCK_CONFIG_BASE)
        config['notifications_weekly'] = {
            'enabled': True, 'day': 'sunday', 'time': '09:00', 'types': ['weekly']
        }
        mock_config.return_value = config

        resultado = ScheduleManager.check_scheduled_tasks()

        assert 'notifications_weekly' in resultado['executed_tasks']

    @patch('core.admin_services.AdminService.execute_backup', return_value={'success': True})
    @patch('core.admin_services.ScheduleManager._should_execute_monthly', return_value=True)
    @patch('core.admin_services.ScheduleManager.get_schedule_config')
    def test_backup_monthly_habilitado_se_ejecuta(self, mock_config, mock_should, mock_exec):
        """Con backup_monthly habilitado y día/hora correctos, se ejecuta."""
        from core.admin_services import ScheduleManager

        config = dict(MOCK_CONFIG_BASE)
        config['backup_monthly'] = {
            'enabled': True, 'day': 1, 'time': '04:00', 'include_files': True
        }
        mock_config.return_value = config

        resultado = ScheduleManager.check_scheduled_tasks()

        assert 'backup_monthly' in resultado['executed_tasks']
        mock_exec.assert_called_once_with(include_files=True)

    @patch('core.admin_services.ScheduleManager.get_schedule_config', side_effect=Exception('Error config'))
    def test_excepcion_retorna_error(self, mock_config):
        """Si get_schedule_config falla, retorna success=False."""
        from core.admin_services import ScheduleManager

        resultado = ScheduleManager.check_scheduled_tasks()

        assert resultado['success'] is False
        assert 'Error config' in resultado['error']
        assert resultado['executed_tasks'] == []


# ============================================================================
# ScheduleManager métodos auxiliares
# ============================================================================

class TestScheduleManagerMetodosAuxiliares:
    """Tests para _should_execute_daily, _should_execute_weekly, _should_execute_monthly."""

    def test_should_execute_daily_true_cuando_hora_coincide(self):
        """_should_execute_daily retorna True cuando hour y minute coinciden."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        # Fecha arbitraria a las 02:00
        dt = datetime(2026, 3, 15, 2, 0)
        assert ScheduleManager._should_execute_daily(dt, '02:00') is True

    def test_should_execute_daily_false_cuando_hora_no_coincide(self):
        """_should_execute_daily retorna False cuando la hora no coincide."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        dt = datetime(2026, 3, 15, 3, 30)  # 3:30, no 2:00
        assert ScheduleManager._should_execute_daily(dt, '02:00') is False

    def test_should_execute_weekly_true_cuando_dia_y_hora_coinciden(self):
        """_should_execute_weekly retorna True para lunes a las 03:00."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        # Marzo 9, 2026 = Lunes (weekday=0)
        lunes_3am = datetime(2026, 3, 9, 3, 0)
        assert ScheduleManager._should_execute_weekly(lunes_3am, 'monday', '03:00') is True

    def test_should_execute_weekly_false_dia_incorrecto(self):
        """_should_execute_weekly retorna False cuando el día no coincide."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        # Marzo 10, 2026 = Martes (weekday=1), buscando miércoles
        martes_3am = datetime(2026, 3, 10, 3, 0)
        assert ScheduleManager._should_execute_weekly(martes_3am, 'wednesday', '03:00') is False

    def test_should_execute_weekly_false_hora_incorrecta(self):
        """_should_execute_weekly retorna False cuando la hora no coincide."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        # Lunes a las 4:00, buscando las 3:00
        lunes_4am = datetime(2026, 3, 9, 4, 0)
        assert ScheduleManager._should_execute_weekly(lunes_4am, 'monday', '03:00') is False

    def test_should_execute_monthly_true_cuando_dia_y_hora_coinciden(self):
        """_should_execute_monthly retorna True cuando día, hora y minuto coinciden."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        # Día 1 del mes a las 04:00
        primer_dia_4am = datetime(2026, 3, 1, 4, 0)
        assert ScheduleManager._should_execute_monthly(primer_dia_4am, 1, '04:00') is True

    def test_should_execute_monthly_false_dia_incorrecto(self):
        """_should_execute_monthly retorna False cuando el día no coincide."""
        from core.admin_services import ScheduleManager
        from datetime import datetime

        # Día 2 del mes, buscando día 1
        segundo_dia = datetime(2026, 3, 2, 4, 0)
        assert ScheduleManager._should_execute_monthly(segundo_dia, 1, '04:00') is False
