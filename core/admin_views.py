# core/admin_views.py
# Vistas para el panel de administración del sistema

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from core.admin_services import AdminService, ScheduleManager
from core.models import Empresa
import json
import logging

logger = logging.getLogger('core')

def is_superuser(user):
    """Verifica que el usuario sea superusuario."""
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def admin_dashboard(request):
    """
    Dashboard principal de administración del sistema.
    """
    try:
        # Obtener estado del sistema
        system_status = AdminService.get_system_status()

        # Obtener historial reciente
        execution_history = AdminService.get_execution_history()

        # Obtener configuración de programación
        schedule_config = ScheduleManager.get_schedule_config()

        context = {
            'system_status': system_status,
            'execution_history': execution_history.get('history', [])[-5:],  # Últimos 5
            'schedule_config': schedule_config,
            'current_time': timezone.now(),
        }

        return render(request, 'admin/dashboard.html', context)

    except Exception as e:
        logger.error(f'Error in admin dashboard: {e}')
        messages.error(request, f'Error cargando dashboard: {e}')
        return render(request, 'admin/dashboard.html', {'error': str(e)})

@login_required
@user_passes_test(is_superuser)
def system_maintenance(request):
    """
    Página para ejecutar tareas de mantenimiento.
    """
    if request.method == 'POST':
        task_type = request.POST.get('task_type', 'all')
        dry_run = request.POST.get('dry_run') == 'on'

        try:
            result = AdminService.execute_maintenance(task_type, dry_run)

            # Guardar en historial
            AdminService.save_execution_to_history(
                f'maintenance_{task_type}',
                result,
                request.user
            )

            if result['success']:
                if dry_run:
                    messages.success(request, '✅ Simulación de mantenimiento completada')
                else:
                    messages.success(request, '✅ Mantenimiento ejecutado correctamente')
            else:
                messages.error(request, f'❌ Error en mantenimiento: {result.get("error", "Error desconocido")}')

        except Exception as e:
            logger.error(f'Error executing maintenance: {e}')
            messages.error(request, f'❌ Error ejecutando mantenimiento: {e}')

        return redirect('core:admin_maintenance')

    # Obtener historial de mantenimientos
    history = AdminService.get_execution_history()
    maintenance_history = [
        h for h in history.get('history', [])
        if 'maintenance' in h.get('action', '')
    ][-10:]  # Últimos 10

    context = {
        'maintenance_history': maintenance_history,
        'task_options': [
            ('all', 'Todas las tareas'),
            ('cache', 'Limpiar cache'),
            ('logs', 'Limpiar logs'),
            ('database', 'Optimizar base de datos'),
            ('zip', 'Limpiar archivos ZIP')
        ]
    }

    return render(request, 'admin/maintenance.html', context)

@login_required
@user_passes_test(is_superuser)
def system_notifications(request):
    """
    Página para gestionar notificaciones.
    """
    if request.method == 'POST':
        notification_type = request.POST.get('notification_type', 'all')
        dry_run = request.POST.get('dry_run') == 'on'

        try:
            result = AdminService.execute_notifications(notification_type, dry_run)

            # Guardar en historial
            AdminService.save_execution_to_history(
                f'notifications_{notification_type}',
                result,
                request.user
            )

            if result['success']:
                if dry_run:
                    messages.success(request, '✅ Simulación de notificaciones completada')
                else:
                    messages.success(request, '✅ Notificaciones enviadas correctamente')
            else:
                messages.error(request, f'❌ Error en notificaciones: {result.get("error", "Error desconocido")}')

        except Exception as e:
            logger.error(f'Error executing notifications: {e}')
            messages.error(request, f'❌ Error enviando notificaciones: {e}')

        return redirect('core:admin_notifications')

    # Obtener historial de notificaciones
    history = AdminService.get_execution_history()
    notification_history = [
        h for h in history.get('history', [])
        if 'notification' in h.get('action', '')
    ][-10:]

    context = {
        'notification_history': notification_history,
        'notification_options': [
            ('consolidated', 'Consolidado (Recomendado) - UN email con todas las actividades'),
            ('all', 'Todas las notificaciones'),
            ('calibration', 'Solo recordatorios de calibración'),
            ('maintenance', 'Solo recordatorios de mantenimiento'),
            ('comprobacion', 'Solo recordatorios de comprobación'),
            ('weekly', 'Solo resúmenes semanales')
        ]
    }

    return render(request, 'admin/notifications.html', context)

@login_required
@user_passes_test(is_superuser)
def system_backup(request):
    """
    Página para gestionar backups.
    """
    if request.method == 'POST':
        empresa_id = request.POST.get('empresa_id')
        include_files = request.POST.get('include_files') == 'on'
        backup_format = request.POST.get('format', 'both')

        try:
            empresa_id = int(empresa_id) if empresa_id and empresa_id != 'all' else None

            result = AdminService.execute_backup(
                empresa_id=empresa_id,
                include_files=include_files,
                backup_format=backup_format
            )

            # Guardar en historial
            AdminService.save_execution_to_history(
                f'backup_{backup_format}',
                result,
                request.user
            )

            if result['success']:
                messages.success(request, '✅ Backup creado correctamente')
            else:
                messages.error(request, f'❌ Error en backup: {result.get("error", "Error desconocido")}')

        except Exception as e:
            logger.error(f'Error executing backup: {e}')
            messages.error(request, f'❌ Error creando backup: {e}')

        return redirect('core:admin_backup')

    # Obtener empresas para el selector
    empresas = Empresa.objects.all().order_by('nombre')

    # Obtener historial de backups
    history = AdminService.get_execution_history()
    backup_history = [
        h for h in history.get('history', [])
        if 'backup' in h.get('action', '')
    ][-10:]

    context = {
        'empresas': empresas,
        'backup_history': backup_history,
        'format_options': [
            ('both', 'JSON + ZIP con archivos'),
            ('json', 'Solo JSON'),
            ('zip', 'Solo ZIP con archivos')
        ]
    }

    return render(request, 'admin/backup.html', context)

@login_required
@user_passes_test(is_superuser)
def system_monitoring(request):
    """
    Página de monitoreo en tiempo real.
    """
    try:
        system_status = AdminService.get_system_status()
        context = {
            'system_status': system_status,
            'refresh_interval': 30,  # segundos
        }

        return render(request, 'admin/monitoring.html', context)

    except Exception as e:
        logger.error(f'Error in monitoring page: {e}')
        messages.error(request, f'Error cargando monitoreo: {e}')
        return render(request, 'admin/monitoring.html', {'error': str(e)})

@login_required
@user_passes_test(is_superuser)
def system_schedule(request):
    """
    Página para configurar programación automática.
    """
    if request.method == 'POST':
        try:
            # Construir configuración desde el formulario
            schedule_config = {
                'maintenance_daily': {
                    'enabled': request.POST.get('maintenance_daily_enabled') == 'on',
                    'time': request.POST.get('maintenance_daily_time', '02:00'),
                    'tasks': request.POST.getlist('maintenance_daily_tasks') or ['cache', 'database']
                },
                'notifications_daily': {
                    'enabled': request.POST.get('notifications_daily_enabled') == 'on',
                    'time': request.POST.get('notifications_daily_time', '08:00'),
                    'types': request.POST.getlist('notifications_daily_types') or ['calibration', 'maintenance']
                },
                'maintenance_weekly': {
                    'enabled': request.POST.get('maintenance_weekly_enabled') == 'on',
                    'day': request.POST.get('maintenance_weekly_day', 'sunday'),
                    'time': request.POST.get('maintenance_weekly_time', '03:00'),
                    'tasks': ['all']
                },
                'notifications_weekly': {
                    'enabled': request.POST.get('notifications_weekly_enabled') == 'on',
                    'day': request.POST.get('notifications_weekly_day', 'monday'),
                    'time': request.POST.get('notifications_weekly_time', '09:00'),
                    'types': ['weekly']
                },
                'backup_monthly': {
                    'enabled': request.POST.get('backup_monthly_enabled') == 'on',
                    'day': int(request.POST.get('backup_monthly_day', 1)),
                    'time': request.POST.get('backup_monthly_time', '01:00'),
                    'include_files': request.POST.get('backup_monthly_include_files') == 'on'
                }
            }

            if ScheduleManager.save_schedule_config(schedule_config):
                messages.success(request, '✅ Configuración de programación guardada')
                logger.info(f'Schedule configuration updated by {request.user.username}')
            else:
                messages.error(request, '❌ Error guardando configuración')

        except Exception as e:
            logger.error(f'Error saving schedule config: {e}')
            messages.error(request, f'❌ Error en configuración: {e}')

        return redirect('core:admin_schedule')

    # Obtener configuración actual
    schedule_config = ScheduleManager.get_schedule_config()

    context = {
        'schedule_config': schedule_config,
        'days_of_week': [
            ('monday', 'Lunes'),
            ('tuesday', 'Martes'),
            ('wednesday', 'Miércoles'),
            ('thursday', 'Jueves'),
            ('friday', 'Viernes'),
            ('saturday', 'Sábado'),
            ('sunday', 'Domingo')
        ],
        'task_types': [
            ('cache', 'Limpiar cache'),
            ('logs', 'Limpiar logs'),
            ('database', 'Optimizar BD'),
            ('zip', 'Limpiar ZIP'),
            ('all', 'Todas')
        ],
        'notification_types': [
            ('calibration', 'Calibraciones'),
            ('maintenance', 'Mantenimientos'),
            ('weekly', 'Resúmenes semanales')
        ]
    }

    return render(request, 'admin/schedule.html', context)

@login_required
@user_passes_test(is_superuser)
def email_configuration(request):
    """
    Página para configurar email desde la interfaz web.
    """
    from core.models import EmailConfiguration

    # Obtener o crear configuración
    email_config = EmailConfiguration.get_current_config()

    if request.method == 'POST':
        try:
            # Procesar configuración del servidor
            email_host = request.POST.get('email_host')
            if email_host == 'custom':
                email_host = request.POST.get('email_host_custom', 'smtp.gmail.com')

            # Actualizar configuración
            email_config.email_host = email_host
            email_config.email_port = int(request.POST.get('email_port', 587))
            email_config.email_host_user = request.POST.get('email_host_user', '')
            email_config.email_host_password = request.POST.get('email_host_password', '')
            email_config.default_from_email = request.POST.get('default_from_email', '')
            email_config.default_from_name = request.POST.get('default_from_name', 'SAM Metrología')
            email_config.notification_emails = request.POST.get('notification_emails', '')

            # Seguridad
            security = request.POST.get('security', 'tls')
            email_config.email_use_tls = security == 'tls'
            email_config.email_use_ssl = security == 'ssl'

            # Estado
            email_config.is_active = request.POST.get('is_active') == 'on'
            email_config.updated_by = request.user

            # Limpiar errores previos
            email_config.last_error = ''

            email_config.save()

            # Aplicar configuración a Django settings si está activa
            if email_config.is_active:
                email_config.apply_to_django_settings()

            messages.success(request, '✅ Configuración de email guardada correctamente')

            # Guardar en historial
            AdminService.save_execution_to_history(
                'email_config_update',
                {
                    'success': True,
                    'message': 'Configuración de email actualizada',
                    'active': email_config.is_active
                },
                request.user
            )

        except Exception as e:
            logger.error(f'Error saving email configuration: {e}')
            messages.error(request, f'❌ Error guardando configuración: {e}')

        return redirect('core:admin_email_config')

    context = {
        'email_config': email_config,
    }

    return render(request, 'admin/email_config.html', context)

@login_required
@user_passes_test(is_superuser)
def execution_history(request):
    """
    Página con historial completo de ejecuciones.
    """
    history_data = AdminService.get_execution_history()
    history_list = history_data.get('history', [])

    # Paginación
    paginator = Paginator(history_list[::-1], 25)  # Invertir para mostrar más recientes primero
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_executions': len(history_list)
    }

    return render(request, 'admin/history.html', context)

# API endpoints para AJAX
@login_required
@user_passes_test(is_superuser)
def api_system_status(request):
    """
    API endpoint para obtener estado del sistema (para actualizaciones AJAX).
    """
    try:
        status = AdminService.get_system_status()
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser)
@require_POST
def api_execute_command(request):
    """
    API endpoint para ejecutar comandos via AJAX.
    """
    try:
        data = json.loads(request.body)
        command_type = data.get('command_type')
        params = data.get('params', {})

        if command_type == 'maintenance':
            result = AdminService.execute_maintenance(
                task_type=params.get('task_type', 'all'),
                dry_run=params.get('dry_run', False)
            )
        elif command_type == 'notifications':
            result = AdminService.execute_notifications(
                notification_type=params.get('notification_type', 'all'),
                dry_run=params.get('dry_run', False)
            )
        elif command_type == 'backup':
            result = AdminService.execute_backup(
                empresa_id=params.get('empresa_id'),
                include_files=params.get('include_files', False),
                backup_format=params.get('format', 'both')
            )
        elif command_type == 'save_schedule':
            # Guardar configuración de programación
            success = ScheduleManager.save_schedule_config(params)
            result = {
                'success': success,
                'message': 'Configuración guardada correctamente' if success else 'Error guardando configuración',
                'timestamp': timezone.now().isoformat()
            }
        elif command_type == 'test_email_connection':
            # Probar conexión de email
            from core.models import EmailConfiguration
            config = EmailConfiguration.get_current_config()
            result = config.test_connection()
        elif command_type == 'send_test_email':
            # Enviar email de prueba
            from core.models import EmailConfiguration
            config = EmailConfiguration.get_current_config()
            recipient_email = params.get('recipient_email')
            if recipient_email:
                result = config.send_test_email(recipient_email)
            else:
                result = {'success': False, 'error': 'Email destinatario requerido'}
        else:
            return JsonResponse({'success': False, 'error': 'Comando no válido'})

        # Guardar en historial
        AdminService.save_execution_to_history(
            f'{command_type}_{params.get("task_type", params.get("notification_type", ""))}',
            result,
            request.user
        )

        return JsonResponse(result)

    except Exception as e:
        logger.error(f'Error in API command execution: {e}')
        return JsonResponse({'success': False, 'error': str(e)})