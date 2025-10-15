# core/admin_views.py
# Vistas para el panel de administración del sistema

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from core.admin_services import AdminService, ScheduleManager
from core.models import Empresa
from core.monitoring import monitor_view
from core.views.base import superuser_required, access_check
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
    Página unificada para ejecutar tareas de mantenimiento.
    Combina sistema antiguo (AdminService) y nuevo (MaintenanceTask).
    """
    from core.models import MaintenanceTask, CommandLog, SystemHealthCheck
    import subprocess
    import sys

    if request.method == 'POST':
        task_type = request.POST.get('task_type')
        dry_run = request.POST.get('dry_run') == 'on'

        if not task_type:
            messages.error(request, 'Debe seleccionar un tipo de tarea')
            return redirect('core:admin_maintenance')

        # Mapeo de tareas antiguas a nuevas
        task_mapping = {
            'cache': 'clear_cache',
            'database': 'optimize_db',
            'zip': 'cleanup_files',
            'logs': 'cleanup_files',
            'backups': 'backup_db',
            'all': 'check_system'  # "All" ejecutará verificación completa
        }

        new_task_type = task_mapping.get(task_type, 'check_system')

        # Si es dry_run, solo mostrar mensaje
        if dry_run:
            messages.info(request, f'[SIMULACIÓN] Se ejecutaría: {task_type}. No se han hecho cambios.')
            return redirect('core:admin_maintenance')

        try:
            # Crear tarea en la base de datos
            task = MaintenanceTask.objects.create(
                task_type=new_task_type,
                created_by=request.user,
                status='pending'
            )

            logger.info(f"Tarea de mantenimiento creada: {task.id} - {new_task_type} por {request.user.username}")

            # Ejecutar tarea en segundo plano
            try:
                python_path = sys.executable
                subprocess.Popen(
                    [python_path, 'manage.py', 'run_maintenance_task', str(task.id)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                messages.success(request, f'Tarea "{task.get_task_type_display()}" iniciada (ID: {task.id})')

            except Exception as e:
                logger.error(f"Error al iniciar tarea {task.id}: {e}")
                task.status = 'failed'
                task.error_message = f'Error al iniciar: {str(e)}'
                task.save()
                messages.error(request, f'Error al iniciar tarea: {str(e)}')

        except Exception as e:
            logger.error(f'Error creating maintenance task: {e}')
            messages.error(request, f'Error creando tarea: {e}')

        return redirect('core:admin_maintenance')

    # Obtener historial desde base de datos (últimas 10 tareas)
    recent_tasks = MaintenanceTask.objects.select_related('created_by').order_by('-created_at')[:10]

    # Estadísticas
    total_tasks = MaintenanceTask.objects.count()
    completed_tasks = MaintenanceTask.objects.filter(status='completed').count()
    failed_tasks = MaintenanceTask.objects.filter(status='failed').count()
    running_tasks = MaintenanceTask.objects.filter(status='running').count()

    # Última verificación de salud
    last_health_check = SystemHealthCheck.objects.order_by('-checked_at').first()

    context = {
        'recent_tasks': recent_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'failed_tasks': failed_tasks,
        'running_tasks': running_tasks,
        'last_health_check': last_health_check,
        'task_options': [
            ('cache', 'Limpiar cache'),
            ('database', 'Optimizar base de datos'),
            ('zip', 'Limpiar archivos ZIP y temporales'),
            ('backups', 'Crear backup de base de datos'),
            ('all', 'Verificar estado del sistema'),
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
        'empresas_list': Empresa.objects.all().prefetch_related('equipos'),
        'notification_options': [
            ('consolidated', 'Consolidado (Recomendado) - UN email con todas las actividades'),
            ('weekly_overdue', 'Recordatorios Semanales Vencidos (máx 3 por actividad)'),
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
    Página para gestionar backups y restauraciones.
    """
    if request.method == 'POST':
        action = request.POST.get('action', 'backup')

        if action == 'backup':
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

        elif action == 'restore':
            backup_file_path = request.POST.get('backup_file_path')
            new_name = request.POST.get('new_name')
            overwrite = request.POST.get('overwrite') == 'on'
            restore_files = request.POST.get('restore_files') == 'on'
            dry_run = request.POST.get('dry_run') == 'on'

            try:
                import os
                # Verificar que el archivo existe
                if not os.path.exists(backup_file_path):
                    messages.error(request, f'❌ Archivo de backup no encontrado: {backup_file_path}')
                    return redirect('core:admin_backup')

                result = AdminService.execute_restore(
                    backup_file_path=backup_file_path,
                    new_name=new_name if new_name else None,
                    overwrite=overwrite,
                    restore_files=restore_files,
                    dry_run=dry_run
                )

                # Guardar en historial
                AdminService.save_execution_to_history(
                    f'restore_{"dry_run" if dry_run else "real"}',
                    result,
                    request.user
                )

                if result['success']:
                    if dry_run:
                        messages.success(request, '✅ Simulación de restauración completada')
                    else:
                        messages.success(request, '✅ Restauración completada exitosamente')
                else:
                    messages.error(request, f'❌ Error en restauración: {result.get("error", "Error desconocido")}')

            except Exception as e:
                logger.error(f'Error executing restore: {e}')
                messages.error(request, f'❌ Error ejecutando restauración: {e}')

        return redirect('core:admin_backup')

    # Obtener empresas para el selector
    empresas = Empresa.objects.all().order_by('nombre')

    # Obtener historial de backups y restauraciones
    history = AdminService.get_execution_history()
    backup_history = [
        h for h in history.get('history', [])
        if 'backup' in h.get('action', '') or 'restore' in h.get('action', '')
    ][-10:]

    # Obtener archivos de backup disponibles
    available_backups = _get_available_backup_files()

    context = {
        'empresas': empresas,
        'backup_history': backup_history,
        'available_backups': available_backups,
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

        # Calcular estadísticas específicas para el template
        stats = {}
        if system_status.get('success') and system_status.get('health'):
            health_data = system_status['health']
            business_metrics = health_data.get('metrics', {}).get('business', {})
            user_metrics = health_data.get('metrics', {}).get('users', {})

            # Extraer los valores específicos que el template necesita
            stats = {
                'active_companies': business_metrics.get('empresas', {}).get('activas', 0),
                'active_equipment': business_metrics.get('equipos', {}).get('activos', 0),
                'activities_today': (
                    business_metrics.get('actividades_recientes', {}).get('calibraciones_hoy', 0) +
                    business_metrics.get('actividades_recientes', {}).get('mantenimientos_hoy', 0) +
                    business_metrics.get('actividades_recientes', {}).get('comprobaciones_hoy', 0)
                ),
                'active_users': user_metrics.get('users_active_15min', 0),
                'active_users_details': user_metrics.get('active_users_details', []),
                'system_usage': user_metrics.get('system_usage_percentage', 25.0),
                'system_load_breakdown': user_metrics.get('system_load_breakdown', {
                    'base_system': 15,
                    'user_activity': 5,
                    'database_load': 5
                })
            }

        context = {
            'system_status': system_status,
            'stats': stats,
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
                dry_run=params.get('test_mode', params.get('dry_run', False)),
                empresa_id=params.get('empresa_id'),
                days_ahead=params.get('days_ahead', 15)
            )
        elif command_type == 'backup':
            result = AdminService.execute_backup(
                empresa_id=params.get('empresa_id'),
                include_files=params.get('include_files', False),
                backup_format=params.get('format', 'both')
            )
        elif command_type == 'cleanup_backups':
            result = AdminService.execute_cleanup_backups(
                retention_months=params.get('retention_months', 6),
                dry_run=params.get('dry_run', False)
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
            success, message = config.test_connection()
            result = {'success': success, 'message': message}
        elif command_type == 'send_test_email':
            # Enviar email de prueba
            from core.models import EmailConfiguration
            config = EmailConfiguration.get_current_config()
            recipient_email = params.get('recipient_email')
            if recipient_email:
                success, message = config.send_test_email(recipient_email)
                result = {'success': success, 'message': message}
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


def _get_available_backup_files():
    """
    Obtiene lista de archivos de backup disponibles.
    """
    try:
        import os
        import glob
        from datetime import datetime

        backup_files = []
        backup_dir = os.path.join(os.getcwd(), 'backups')

        if os.path.exists(backup_dir):
            # Buscar archivos JSON y ZIP
            json_files = glob.glob(os.path.join(backup_dir, '*.json'))
            zip_files = glob.glob(os.path.join(backup_dir, '*.zip'))

            all_files = json_files + zip_files

            for file_path in all_files:
                try:
                    stat = os.stat(file_path)
                    file_info = {
                        'name': os.path.basename(file_path),
                        'path': file_path,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'type': 'ZIP' if file_path.endswith('.zip') else 'JSON'
                    }

                    # Extraer nombre de empresa del nombre del archivo
                    filename = os.path.basename(file_path)
                    if filename.startswith('backup_'):
                        parts = filename.replace('backup_', '').split('_')
                        if len(parts) >= 2:
                            # Reconstruir nombre de empresa
                            empresa_name = '_'.join(parts[:-2])  # Todo excepto fecha y hora
                            file_info['empresa'] = empresa_name.replace('_', ' ')

                    backup_files.append(file_info)

                except Exception as e:
                    logger.warning(f'Error reading backup file {file_path}: {e}')
                    continue

            # Ordenar por fecha modificada (más recientes primero)
            backup_files.sort(key=lambda x: x['modified'], reverse=True)

        return backup_files

    except Exception as e:
        logger.error(f'Error getting available backup files: {e}')
        return []


@login_required
@user_passes_test(is_superuser)
def download_backup(request, filename):
    """
    Permite descargar archivos de backup de forma segura.
    """
    try:
        import os
        import mimetypes
        from django.http import FileResponse
        from urllib.parse import unquote

        # Decodificar el nombre del archivo
        filename = unquote(filename)

        # Validar que el archivo esté en el directorio de backups
        backup_dir = os.path.join(os.getcwd(), 'backups')
        file_path = os.path.join(backup_dir, filename)

        # Verificar que el archivo existe y está en el directorio correcto
        if not os.path.exists(file_path):
            raise Http404("Archivo de backup no encontrado")

        # Verificar que el archivo está dentro del directorio de backups (seguridad)
        if not os.path.abspath(file_path).startswith(os.path.abspath(backup_dir)):
            raise Http404("Acceso denegado")

        # Verificar que es un archivo de backup válido
        if not (filename.endswith('.json') or filename.endswith('.zip')):
            raise Http404("Tipo de archivo no válido")

        # Log de la descarga
        logger.info(f'Backup download requested: {filename} by {request.user.username}')

        # Detectar tipo de contenido
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # Crear respuesta de descarga
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=filename
        )

        # Agregar headers adicionales
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = os.path.getsize(file_path)

        return response

    except Http404:
        raise
    except Exception as e:
        logger.error(f'Error downloading backup {filename}: {e}')
        messages.error(request, f'Error descargando backup: {e}')


@login_required
@user_passes_test(is_superuser)
def deleted_companies(request):
    """
    Lista las empresas eliminadas (soft deleted) con opción de restaurar.
    """
    try:
        deleted_companies = Empresa.get_deleted_companies()

        context = {
            'deleted_companies': deleted_companies,
            'current_time': timezone.now(),
        }

        return render(request, 'admin/deleted_companies.html', context)

    except Exception as e:
        logger.error(f'Error listing deleted companies: {e}')
        messages.error(request, f'Error cargando empresas eliminadas: {e}')
        return redirect('core:admin_dashboard')


@login_required
@user_passes_test(is_superuser)
def restore_company(request, empresa_id):
    """
    Restaura una empresa previamente eliminada.
    """
    try:
        empresa = Empresa.objects.get(id=empresa_id, is_deleted=True)

        if request.method == 'POST':
            success, message = empresa.restore(user=request.user)

            if success:
                messages.success(request, f'Empresa {empresa.nombre} restaurada exitosamente')
                logger.info(f'Company {empresa.nombre} restored by {request.user.username}')
            else:
                messages.error(request, f'Error restaurando empresa: {message}')

            return redirect('core:deleted_companies')

        context = {
            'empresa': empresa,
            'delete_info': empresa.get_delete_info(),
        }

        return render(request, 'admin/restore_company.html', context)

    except Empresa.DoesNotExist:
        messages.error(request, 'Empresa no encontrada o no está eliminada')
        return redirect('core:deleted_companies')
    except Exception as e:
        logger.error(f'Error restoring company {empresa_id}: {e}')
        messages.error(request, f'Error restaurando empresa: {e}')
        return redirect('core:deleted_companies')


@login_required
@user_passes_test(is_superuser)
def soft_delete_company(request, empresa_id):
    """
    Elimina una empresa de forma suave (soft delete).
    """
    try:
        empresa = Empresa.objects.get(id=empresa_id, is_deleted=False)

        if request.method == 'POST':
            reason = request.POST.get('delete_reason', '')
            empresa.soft_delete(user=request.user, reason=reason)

            messages.success(request, f'Empresa {empresa.nombre} eliminada exitosamente')
            logger.info(f'Company {empresa.nombre} soft deleted by {request.user.username}')

            return redirect('core:listar_empresas')

        # Obtener estadísticas de la empresa
        total_equipos = empresa.equipos.count()
        equipos_activos = empresa.equipos.filter(estado='Activo').count()
        usuarios_empresa = empresa.usuarios_empresa.count()

        context = {
            'empresa': empresa,
            'total_equipos': total_equipos,
            'equipos_activos': equipos_activos,
            'usuarios_empresa': usuarios_empresa,
        }

        return render(request, 'admin/soft_delete_company.html', context)

    except Empresa.DoesNotExist:
        messages.error(request, 'Empresa no encontrada')
        return redirect('core:listar_empresas')
    except Exception as e:
        logger.error(f'Error soft deleting company {empresa_id}: {e}')
        messages.error(request, f'Error eliminando empresa: {e}')
        return redirect('core:listar_empresas')


@monitor_view
@login_required
@superuser_required
def cleanup_old_companies(request):
    """
    Vista para ejecutar limpieza de empresas eliminadas antiguas (más de 6 meses).
    Solo disponible para superusuarios.
    """
    context = {
        'titulo_pagina': 'Limpieza de Empresas Eliminadas'
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'preview':
            # Mostrar vista previa de qué se eliminaría
            result = Empresa.cleanup_old_deleted_companies(dry_run=True)
            context.update({
                'preview_result': result,
                'show_preview': True
            })
            messages.info(
                request,
                f'Encontradas {result["count"]} empresas para eliminación permanente.'
            )

        elif action == 'execute_all':
            # Ejecutar la limpieza de TODAS las empresas listas
            result = Empresa.cleanup_old_deleted_companies(dry_run=False)
            context.update({
                'execution_result': result,
                'show_result': True
            })

            if result['count'] > 0:
                messages.success(
                    request,
                    f'Eliminación completada. {len(result["deleted"])} empresas eliminadas permanentemente.'
                )
                logger.info(f'Limpieza manual de empresas ejecutada por {request.user.username}: {len(result["deleted"])} empresas eliminadas')
            else:
                messages.info(request, 'No hay empresas para eliminar permanentemente.')

        elif action == 'execute_selected':
            # Ejecutar limpieza de empresas seleccionadas
            company_ids = request.POST.getlist('company_ids')

            if not company_ids:
                messages.warning(request, 'No seleccionaste ninguna empresa para eliminar.')
            else:
                # Obtener las empresas seleccionadas que están listas para eliminación
                companies_for_deletion = Empresa.get_companies_for_permanent_deletion()
                selected_companies = companies_for_deletion.filter(id__in=company_ids)

                deleted_companies = []
                for company in selected_companies:
                    try:
                        company_name = company.nombre
                        company_id = company.id
                        company.delete()  # Eliminación física
                        deleted_companies.append({
                            'id': company_id,
                            'name': company_name,
                            'deleted_at': timezone.now(),
                            'days_since_deletion': 0
                        })
                        logger.info(f'Empresa {company_name} (ID: {company_id}) eliminada permanentemente por {request.user.username}')
                    except Exception as e:
                        logger.error(f'Error eliminando empresa {company.nombre}: {e}')
                        messages.error(request, f'Error al eliminar {company.nombre}: {str(e)}')

                result = {
                    'count': len(deleted_companies),
                    'deleted': deleted_companies
                }

                context.update({
                    'execution_result': result,
                    'show_result': True
                })

                if len(deleted_companies) > 0:
                    messages.success(
                        request,
                        f'Eliminación completada. {len(deleted_companies)} empresa(s) eliminadas permanentemente.'
                    )
                else:
                    messages.error(request, 'No se pudo eliminar ninguna empresa.')

    # Obtener estadísticas generales
    deleted_companies = Empresa.objects.filter(is_deleted=True)
    companies_for_deletion = Empresa.get_companies_for_permanent_deletion()

    context.update({
        'total_deleted_companies': deleted_companies.count(),
        'companies_ready_for_deletion': companies_for_deletion.count(),
        'retention_days': 180
    })

    return render(request, 'admin/cleanup_old_companies.html', context)


@login_required
@user_passes_test(is_superuser)
def run_tests_panel(request):
    """
    Panel para ejecutar tests desde la interfaz web.
    Solo accesible para superusuarios.
    """
    context = {
        'titulo_pagina': 'Verificación del Sistema',
        'test_categories': [
            ('all', 'Revisar Todo', 'Revisa completamente que el sistema funcione bien'),
            ('unit', 'Revisar Base de Datos', 'Verifica que la información se guarde correctamente'),
            ('integration', 'Revisar Procesos Completos', 'Prueba flujos de trabajo de principio a fin'),
            ('views', 'Revisar Pantallas', 'Verifica que todas las páginas funcionen bien'),
            ('services', 'Revisar Funciones del Sistema', 'Prueba las operaciones principales del sistema'),
        ]
    }

    if request.method == 'POST':
        test_category = request.POST.get('test_category', 'all')
        verbose = request.POST.get('verbose') == 'on'
        parallel = request.POST.get('parallel') == 'on'
        coverage = request.POST.get('coverage') == 'on'

        try:
            import subprocess
            import sys
            import os
            from datetime import datetime
            from django.conf import settings

            # Detectar si estamos en producción
            is_production = hasattr(settings, 'RENDER_EXTERNAL_HOSTNAME') and settings.RENDER_EXTERNAL_HOSTNAME

            # Obtener directorio raíz del proyecto
            current_file = os.path.abspath(__file__)
            core_dir = os.path.dirname(current_file)
            project_root = os.path.dirname(core_dir)

            # Ejecutar tests
            start_time = datetime.now()

            if is_production:
                # EN PRODUCCIÓN: Usar Django test runner (NO requiere pytest)
                cmd = [sys.executable, 'manage.py', 'test', 'core']

                # Agregar opciones de Django
                if verbose:
                    cmd.append('--verbosity=2')
                else:
                    cmd.append('--verbosity=1')

                # Agregar parallel si está disponible
                if parallel:
                    cmd.extend(['--parallel', 'auto'])

                # Filtros por categoría (convertir a formato Django)
                if test_category != 'all':
                    # Django usa etiquetas con --tag
                    category_mapping = {
                        'unit': 'unit',
                        'integration': 'integration',
                        'views': 'views',
                        'services': 'services'
                    }
                    tag = category_mapping.get(test_category, test_category)
                    cmd.extend(['--tag', tag])

                logger.info(f'[PRODUCCIÓN] Ejecutando tests con Django runner: {" ".join(cmd)}')

            else:
                # EN DESARROLLO: Intentar usar pytest si está disponible
                try:
                    import pytest
                    use_pytest = True
                except ImportError:
                    use_pytest = False
                    logger.info('[DESARROLLO] pytest no disponible, usando Django test runner')

                if use_pytest:
                    # Usar pytest en desarrollo
                    cmd = [sys.executable, '-m', 'pytest', 'tests/']

                    # Agregar filtros por categoría
                    if test_category != 'all':
                        cmd.extend(['-m', test_category])

                    # Agregar opciones
                    if verbose:
                        cmd.append('-v')
                    else:
                        cmd.append('-q')

                    if parallel:
                        cmd.extend(['-n', 'auto'])

                    if coverage:
                        cmd.extend(['--cov=core', '--cov-report=html', '--cov-report=term'])

                    cmd.extend(['--tb=short'])

                    logger.info(f'[DESARROLLO] Ejecutando tests con pytest: {" ".join(cmd)}')
                else:
                    # Fallback a Django test runner
                    cmd = [sys.executable, 'manage.py', 'test', 'core']
                    if verbose:
                        cmd.append('--verbosity=2')
                    logger.info(f'[DESARROLLO] Ejecutando tests con Django runner: {" ".join(cmd)}')

            logger.info(f'[TEST] Directorio del proyecto: {project_root}')
            logger.info(f'[TEST] Existe manage.py?: {os.path.exists(os.path.join(project_root, "manage.py"))}')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutos timeout
                cwd=project_root
            )
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Procesar resultados - manejar valores None
            stdout_text = result.stdout if result.stdout else ""
            stderr_text = result.stderr if result.stderr else ""
            output = stdout_text + stderr_text
            success = result.returncode == 0

            # DEBUG: Log del output para diagnóstico
            logger.info(f'[DEBUG TEST] Return code: {result.returncode}')
            logger.info(f'[DEBUG TEST] Stdout length: {len(stdout_text)} caracteres')
            logger.info(f'[DEBUG TEST] Stderr length: {len(stderr_text)} caracteres')
            logger.info(f'[DEBUG TEST] Output primeros 500 chars: {output[:500]}')
            logger.info(f'[DEBUG TEST] Comando ejecutado: {" ".join(cmd)}')

            # Extraer estadísticas del output (compatible con pytest y Django)
            import re

            # Intentar formato pytest primero
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)
            skipped_match = re.search(r'(\d+) skipped', output)
            warnings_match = re.search(r'(\d+) warnings', output)

            # Si no encuentra formato pytest, intentar formato Django
            if not passed_match:
                # Formato Django: "Ran X tests in Y.Ys" y "OK" o "FAILED (failures=X)"
                ran_match = re.search(r'Ran (\d+) test', output)
                ok_match = re.search(r'\nOK\n', output)
                django_failed = re.search(r'FAILED \((?:failures=(\d+)|errors=(\d+))', output)

                if ran_match:
                    total = int(ran_match.group(1))
                    if ok_match:
                        passed = total
                        failed = 0
                    elif django_failed:
                        failed = int(django_failed.group(1) or django_failed.group(2) or 0)
                        passed = total - failed
                    else:
                        passed = 0
                        failed = total

                    stats = {
                        'passed': passed,
                        'failed': failed,
                        'skipped': 0,
                        'warnings': 0,
                        'total': total,
                        'duration': round(duration, 2),
                        'success_rate': 0
                    }
                else:
                    # Fallback: si no hay resultados
                    stats = {
                        'passed': 0,
                        'failed': 0,
                        'skipped': 0,
                        'warnings': 0,
                        'total': 0,
                        'duration': round(duration, 2),
                        'success_rate': 0
                    }
            else:
                # Formato pytest
                stats = {
                    'passed': int(passed_match.group(1)) if passed_match else 0,
                    'failed': int(failed_match.group(1)) if failed_match else 0,
                    'skipped': int(skipped_match.group(1)) if skipped_match else 0,
                    'warnings': int(warnings_match.group(1)) if warnings_match else 0,
                    'total': 0,
                    'duration': round(duration, 2),
                    'success_rate': 0
                }
                stats['total'] = stats['passed'] + stats['failed'] + stats['skipped']

            if stats['total'] > 0:
                stats['success_rate'] = round((stats['passed'] / stats['total']) * 100, 1)

            # Guardar resultado en contexto
            context.update({
                'test_executed': True,
                'test_success': success,
                'test_output': output,
                'test_stats': stats,
                'test_command': ' '.join(cmd),
                'test_category': test_category,
            })

            # Mensaje de éxito o error
            if success:
                messages.success(
                    request,
                    f'✅ Tests completados exitosamente: {stats["passed"]}/{stats["total"]} pasaron ({stats["success_rate"]}%)'
                )
            else:
                messages.warning(
                    request,
                    f'⚠️ Tests completados con fallos: {stats["failed"]} tests fallaron de {stats["total"]} ejecutados'
                )

            # Guardar en historial de admin
            AdminService.save_execution_to_history(
                f'run_tests_{test_category}',
                {
                    'success': success,
                    'stats': stats,
                    'category': test_category,
                    'duration': duration
                },
                request.user
            )

            logger.info(f'Tests ejecutados por {request.user.username}: {test_category}, {stats["passed"]}/{stats["total"]} pasaron')

        except subprocess.TimeoutExpired:
            messages.error(request, '❌ Tests excedieron el tiempo límite de 10 minutos')
            context['test_executed'] = True
            context['test_success'] = False
            context['test_output'] = 'ERROR: Tests excedieron el tiempo límite de ejecución'

        except Exception as e:
            logger.error(f'Error ejecutando tests: {e}')
            messages.error(request, f'❌ Error ejecutando tests: {str(e)}')
            context['test_executed'] = True
            context['test_success'] = False
            context['test_output'] = f'ERROR: {str(e)}'

    return render(request, 'admin/run_tests.html', context)