# core/views/maintenance.py
"""
Vistas para el sistema de mantenimiento y administración web.
Permite ejecutar comandos sin acceso SSH.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from core.models import MaintenanceTask, CommandLog, SystemHealthCheck, Empresa, Equipo, CustomUser
from core.monitoring import SystemMonitor
import subprocess
import sys
import logging

logger = logging.getLogger('core')


def is_superuser(user):
    """Verificar que el usuario sea superusuario"""
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def maintenance_dashboard(request):
    """
    Dashboard principal de mantenimiento.
    Solo accesible para superusuarios.
    """
    # Estadísticas de tareas
    total_tasks = MaintenanceTask.objects.count()
    pending_tasks = MaintenanceTask.objects.filter(status='pending').count()
    running_tasks = MaintenanceTask.objects.filter(status='running').count()
    completed_tasks = MaintenanceTask.objects.filter(status='completed').count()
    failed_tasks = MaintenanceTask.objects.filter(status='failed').count()

    # Tareas recientes
    recent_tasks = MaintenanceTask.objects.select_related('created_by').order_by('-created_at')[:10]

    # Última verificación de salud
    last_health_check = SystemHealthCheck.objects.order_by('-checked_at').first()

    # Estadísticas del sistema
    system_stats = {
        'total_empresas': Empresa.objects.filter(is_deleted=False).count(),
        'total_equipos': Equipo.objects.count(),
        'total_usuarios': CustomUser.objects.count(),
    }

    # Tipos de tareas disponibles
    available_tasks = [
        {
            'type': 'backup_db',
            'name': 'Backup de Base de Datos',
            'description': 'Crea una copia de seguridad de la base de datos',
            'icon': 'database',
            'color': 'primary'
        },
        {
            'type': 'clear_cache',
            'name': 'Limpiar Cache',
            'description': 'Limpia el cache del sistema para liberar memoria',
            'icon': 'trash',
            'color': 'warning'
        },
        {
            'type': 'cleanup_files',
            'name': 'Limpiar Archivos Temporales',
            'description': 'Elimina ZIPs antiguos y archivos temporales',
            'icon': 'file-earmark-x',
            'color': 'info'
        },
        {
            'type': 'check_system',
            'name': 'Verificar Sistema',
            'description': 'Verifica el estado de salud del sistema',
            'icon': 'heart-pulse',
            'color': 'success'
        },
        {
            'type': 'run_tests',
            'name': 'Ejecutar Tests',
            'description': 'Ejecuta suite de tests del sistema',
            'icon': 'check-circle',
            'color': 'secondary'
        },
        {
            'type': 'collect_static',
            'name': 'Recolectar Estáticos',
            'description': 'Recopila archivos CSS/JS/imágenes',
            'icon': 'file-code',
            'color': 'dark'
        },
        {
            'type': 'migrate_db',
            'name': 'Aplicar Migraciones',
            'description': 'Aplica migraciones pendientes de la base de datos',
            'icon': 'arrow-repeat',
            'color': 'danger'
        },
    ]

    context = {
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'running_tasks': running_tasks,
        'completed_tasks': completed_tasks,
        'failed_tasks': failed_tasks,
        'recent_tasks': recent_tasks,
        'last_health_check': last_health_check,
        'system_stats': system_stats,
        'available_tasks': available_tasks,
    }

    return render(request, 'core/maintenance/dashboard.html', context)


@login_required
@user_passes_test(is_superuser)
def create_maintenance_task(request):
    """
    Crea una nueva tarea de mantenimiento.
    """
    if request.method == 'POST':
        task_type = request.POST.get('task_type')

        if not task_type:
            messages.error(request, 'Debe seleccionar un tipo de tarea')
            return redirect('core:maintenance_dashboard')

        # Verificar que no haya tareas pendientes o en ejecución del mismo tipo
        existing = MaintenanceTask.objects.filter(
            task_type=task_type,
            status__in=['pending', 'running']
        ).exists()

        if existing:
            messages.warning(request, f'Ya hay una tarea de este tipo en ejecución o pendiente')
            return redirect('core:maintenance_dashboard')

        # Crear tarea
        task = MaintenanceTask.objects.create(
            task_type=task_type,
            created_by=request.user,
            status='pending'
        )

        logger.info(f"Tarea de mantenimiento creada: {task.id} - {task_type} por {request.user.username}")

        # Ejecutar tarea inmediatamente en segundo plano
        try:
            # Obtener ruta de Python
            python_path = sys.executable

            # Ejecutar comando en background
            subprocess.Popen(
                [python_path, 'manage.py', 'run_maintenance_task', str(task.id)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(sys.path[0])  # Directorio del proyecto
            )

            messages.success(request, f'Tarea "{task.get_task_type_display()}" iniciada (ID: {task.id})')

        except Exception as e:
            logger.error(f"Error al iniciar tarea {task.id}: {e}")
            task.status = 'failed'
            task.error_message = f'Error al iniciar: {str(e)}'
            task.save()
            messages.error(request, f'Error al iniciar tarea: {str(e)}')

        return redirect('core:maintenance_task_detail', task_id=task.id)

    return redirect('core:maintenance_dashboard')


@login_required
@user_passes_test(is_superuser)
def maintenance_task_detail(request, task_id):
    """
    Detalle de una tarea de mantenimiento.
    """
    task = get_object_or_404(MaintenanceTask, id=task_id)
    logs = CommandLog.objects.filter(task=task).order_by('timestamp')

    context = {
        'task': task,
        'logs': logs,
    }

    return render(request, 'core/maintenance/task_detail.html', context)


@login_required
@user_passes_test(is_superuser)
def maintenance_task_list(request):
    """
    Lista todas las tareas de mantenimiento con filtros.
    """
    tasks = MaintenanceTask.objects.select_related('created_by').order_by('-created_at')

    # Filtros
    status_filter = request.GET.get('status')
    task_type_filter = request.GET.get('task_type')

    if status_filter:
        tasks = tasks.filter(status=status_filter)

    if task_type_filter:
        tasks = tasks.filter(task_type=task_type_filter)

    # Paginación
    paginator = Paginator(tasks, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'task_type_filter': task_type_filter,
        'task_types': MaintenanceTask.TASK_TYPE_CHOICES,
        'statuses': MaintenanceTask.TASK_STATUS_CHOICES,
    }

    return render(request, 'core/maintenance/task_list.html', context)


@login_required
@user_passes_test(is_superuser)
def run_system_health_check(request):
    """
    Ejecuta una verificación de salud del sistema.
    """
    if request.method == 'POST':
        try:
            # Obtener métricas del sistema
            health_data = SystemMonitor.get_system_health()

            # Crear registro de health check
            health_check = SystemHealthCheck.objects.create(
                checked_by=request.user,
                overall_status='healthy',  # TODO: Determinar basado en métricas
                database_status='healthy',
                cache_status='healthy',
                storage_status='healthy',
                total_empresas=health_data['metrics']['business']['total_empresas'],
                total_equipos=health_data['metrics']['business']['total_equipos'],
                total_usuarios=health_data['metrics']['users']['total_usuarios'],
                details=health_data
            )

            messages.success(request, 'Verificación de salud completada')
            logger.info(f"Health check ejecutado por {request.user.username}")

            return redirect('core:system_health_detail', check_id=health_check.id)

        except Exception as e:
            logger.error(f"Error en health check: {e}")
            messages.error(request, f'Error al ejecutar verificación: {str(e)}')

    return redirect('core:maintenance_dashboard')


@login_required
@user_passes_test(is_superuser)
def system_health_detail(request, check_id):
    """
    Detalle de una verificación de salud.
    """
    health_check = get_object_or_404(SystemHealthCheck, id=check_id)

    context = {
        'health_check': health_check,
    }

    return render(request, 'core/maintenance/health_detail.html', context)


@login_required
@user_passes_test(is_superuser)
def system_health_history(request):
    """
    Historial de verificaciones de salud.
    """
    checks = SystemHealthCheck.objects.order_by('-checked_at')

    # Paginación
    paginator = Paginator(checks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }

    return render(request, 'core/maintenance/health_history.html', context)


# ==============================================================================
# APIs AJAX para actualización en tiempo real
# ==============================================================================

@login_required
@user_passes_test(is_superuser)
def task_status_api(request, task_id):
    """
    API para obtener estado de una tarea (para auto-refresh).
    """
    try:
        task = MaintenanceTask.objects.get(id=task_id)

        data = {
            'success': True,
            'task': {
                'id': task.id,
                'status': task.status,
                'status_display': task.get_status_display(),
                'progress': 100 if task.status in ['completed', 'failed'] else 50,
                'duration': task.get_duration_display(),
                'output_length': len(task.output) if task.output else 0,
                'has_error': bool(task.error_message),
            }
        }

        return JsonResponse(data)

    except MaintenanceTask.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Tarea no encontrada'}, status=404)


@login_required
@user_passes_test(is_superuser)
def task_logs_api(request, task_id):
    """
    API para obtener logs de una tarea en tiempo real.
    """
    try:
        task = MaintenanceTask.objects.get(id=task_id)
        logs = CommandLog.objects.filter(task=task).order_by('timestamp')

        logs_data = [
            {
                'timestamp': log.timestamp.strftime('%H:%M:%S'),
                'level': log.level,
                'message': log.message
            }
            for log in logs
        ]

        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'total': logs.count()
        })

    except MaintenanceTask.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Tarea no encontrada'}, status=404)
