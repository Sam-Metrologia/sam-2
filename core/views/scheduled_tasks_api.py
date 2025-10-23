# core/views/scheduled_tasks_api.py
# API endpoints para ejecutar tareas programadas desde GitHub Actions

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import logging

from core.notifications import NotificationScheduler
from core.admin_services import AdminService

logger = logging.getLogger('core')

# Token de seguridad - debe coincidir con el configurado en GitHub Secrets
SCHEDULED_TASKS_TOKEN = getattr(settings, 'SCHEDULED_TASKS_TOKEN', 'change-this-secret-token')


def verify_token(request):
    """Verifica que el token de autorización sea correcto."""
    auth_header = request.headers.get('Authorization', '')

    # Formato: "Bearer TOKEN"
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == SCHEDULED_TASKS_TOKEN

    # También permitir en query string para facilidad
    token = request.GET.get('token', '')
    return token == SCHEDULED_TASKS_TOKEN


@csrf_exempt
@require_http_methods(["POST", "GET"])
def trigger_daily_notifications(request):
    """
    Ejecuta notificaciones diarias consolidadas.
    Endpoint: /api/scheduled/notifications/daily/
    """
    if not verify_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        logger.info('🔔 GitHub Actions: Ejecutando notificaciones diarias')

        sent_count = NotificationScheduler.check_all_reminders()

        logger.info(f'✅ Notificaciones enviadas: {sent_count}')

        return JsonResponse({
            'success': True,
            'task': 'daily_notifications',
            'sent_count': sent_count,
            'message': f'Notificaciones diarias ejecutadas. Enviadas: {sent_count}'
        })

    except Exception as e:
        logger.error(f'❌ Error en notificaciones diarias: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def trigger_daily_maintenance(request):
    """
    Ejecuta mantenimiento diario (limpieza cache, optimización).
    Endpoint: /api/scheduled/maintenance/daily/
    """
    if not verify_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        logger.info('🔧 GitHub Actions: Ejecutando mantenimiento diario')

        # Ejecutar limpieza de cache
        result_cache = AdminService.execute_maintenance(task_type='cache')

        # Ejecutar limpieza de base de datos
        result_db = AdminService.execute_maintenance(task_type='database')

        logger.info('✅ Mantenimiento diario completado')

        return JsonResponse({
            'success': True,
            'task': 'daily_maintenance',
            'cache_result': result_cache.get('success', False),
            'db_result': result_db.get('success', False),
            'message': 'Mantenimiento diario ejecutado'
        })

    except Exception as e:
        logger.error(f'❌ Error en mantenimiento diario: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def trigger_cleanup_zips(request):
    """
    Limpia archivos ZIP antiguos.
    Endpoint: /api/scheduled/cleanup/zips/
    """
    if not verify_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        logger.info('🗑️ GitHub Actions: Limpiando archivos ZIP')

        from django.core.management import call_command
        from io import StringIO

        output = StringIO()
        call_command('cleanup_zip_files', '--older-than-hours', '6', stdout=output)

        result = output.getvalue()
        logger.info(f'✅ Limpieza ZIP completada: {result}')

        return JsonResponse({
            'success': True,
            'task': 'cleanup_zips',
            'message': 'Archivos ZIP limpiados',
            'output': result
        })

    except Exception as e:
        logger.error(f'❌ Error limpiando ZIPs: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def trigger_weekly_overdue(request):
    """
    Envía recordatorios semanales de actividades vencidas.
    Endpoint: /api/scheduled/notifications/weekly-overdue/
    """
    if not verify_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        logger.info('📧 GitHub Actions: Enviando notificaciones vencidas semanales')

        sent_count = NotificationScheduler.send_weekly_overdue_reminders()

        logger.info(f'✅ Notificaciones vencidas enviadas: {sent_count}')

        return JsonResponse({
            'success': True,
            'task': 'weekly_overdue_notifications',
            'sent_count': sent_count,
            'message': f'Notificaciones vencidas enviadas: {sent_count}'
        })

    except Exception as e:
        logger.error(f'❌ Error en notificaciones vencidas: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def trigger_check_trials(request):
    """
    Verifica y procesa empresas con periodo de prueba expirado.
    Endpoint: /api/scheduled/check-trials/
    """
    if not verify_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        logger.info('⏰ GitHub Actions: Verificando trials expirados')

        from django.core.management import call_command
        from io import StringIO

        output = StringIO()
        call_command('check_trial_expiration', stdout=output)

        result = output.getvalue()
        logger.info(f'✅ Verificación trials completada: {result}')

        return JsonResponse({
            'success': True,
            'task': 'check_trials',
            'message': 'Trials verificados',
            'output': result
        })

    except Exception as e:
        logger.error(f'❌ Error verificando trials: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def trigger_cleanup_notifications(request):
    """
    Limpia notificaciones antiguas (>30 días).
    Endpoint: /api/scheduled/cleanup/notifications/
    """
    if not verify_token(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        logger.info('🧹 GitHub Actions: Limpiando notificaciones antiguas')

        from django.core.management import call_command
        from io import StringIO

        output = StringIO()
        call_command('cleanup_notifications', '--days', '30', stdout=output)

        result = output.getvalue()
        logger.info(f'✅ Limpieza notificaciones completada: {result}')

        return JsonResponse({
            'success': True,
            'task': 'cleanup_notifications',
            'message': 'Notificaciones antiguas limpiadas',
            'output': result
        })

    except Exception as e:
        logger.error(f'❌ Error limpiando notificaciones: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check simple sin autenticación.
    Endpoint: /api/scheduled/health/
    """
    return JsonResponse({
        'status': 'ok',
        'service': 'SAM Metrología Scheduled Tasks API',
        'message': 'API funcionando correctamente'
    })
