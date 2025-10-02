# core/streaming_zip_views.py
# Vistas para implementar el nuevo sistema de ZIP asíncrono

from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.files.storage import default_storage
from .async_zip_system import zip_processor
from .models import Empresa, NotificacionZip
import json
import logging

logger = logging.getLogger('core')

@login_required
@require_POST
def request_async_zip(request):
    """
    Nueva vista para solicitar ZIP asíncrono.
    Retorna inmediatamente con job_id, no bloquea la aplicación.
    """
    try:
        empresa_id = request.POST.get('empresa_id')
        formatos = request.POST.getlist('formatos[]')

        if not empresa_id or not formatos:
            return JsonResponse({
                'success': False,
                'error': 'Empresa y formatos son requeridos'
            })

        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Verificar permisos
        if not request.user.is_superuser and request.user.empresa != empresa:
            return JsonResponse({
                'success': False,
                'error': 'Sin permisos para esta empresa'
            })

        # Iniciar procesador si no está corriendo
        zip_processor.start_processor()

        # Solicitar ZIP (retorna inmediatamente)
        result = zip_processor.request_zip(
            empresa=empresa,
            formatos=formatos,
            user=request.user
        )

        return JsonResponse({
            'success': True,
            'job_id': result['job_id'],
            'status': result['status'],
            'estimated_time': result['estimated_time'],
            'message': result['message'],
            'equipos_count': empresa.equipos.count()
        })

    except Exception as e:
        logger.error(f"❌ Error en request_async_zip: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        })


@login_required
def check_zip_status(request, job_id):
    """
    Verifica el estado de un trabajo ZIP.
    Para uso con AJAX polling o WebSockets.
    """
    try:
        status = zip_processor.get_job_status(job_id)

        if status.get('status') == 'not_found':
            return JsonResponse({
                'success': False,
                'error': 'Trabajo no encontrado'
            })

        # Calcular tiempo transcurrido si está procesando
        elapsed_time = None
        if status.get('started_at'):
            elapsed_time = (timezone.now() - status['started_at']).total_seconds()

        return JsonResponse({
            'success': True,
            'job_id': job_id,
            'status': status['status'],
            'elapsed_time': elapsed_time,
            'download_url': status.get('download_url'),
            'expires_at': status.get('expires_at'),
            'error': status.get('error')
        })

    except Exception as e:
        logger.error(f"❌ Error en check_zip_status: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error verificando estado'
        })


@login_required
def download_completed_zip(request, job_id):
    """
    Descarga un ZIP completado.
    Con streaming para archivos grandes.
    """
    try:
        # Verificar notificación en BD
        notification = get_object_or_404(
            NotificacionZip,
            job_id=job_id,
            user=request.user,
            status='ready'
        )

        # Verificar si no ha expirado
        if notification.expires_at < timezone.now():
            return JsonResponse({
                'success': False,
                'error': 'El archivo ha expirado'
            })

        # Obtener archivo desde storage
        file_path = notification.download_url

        if not default_storage.exists(file_path):
            return JsonResponse({
                'success': False,
                'error': 'Archivo no encontrado'
            })

        # Streaming response para archivos grandes
        def file_iterator():
            with default_storage.open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk

        # Obtener tamaño del archivo
        file_size = default_storage.size(file_path)

        response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/zip'
        )

        # Headers para descarga
        filename = f"SAM_Export_{notification.empresa.nombre}_{notification.created_at.strftime('%Y%m%d_%H%M')}.zip"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = str(file_size)

        # Marcar como descargado
        notification.downloaded_at = timezone.now()
        notification.save()

        logger.info(f"📥 ZIP descargado: {filename} por {request.user.username}")

        return response

    except Exception as e:
        logger.error(f"❌ Error en download_completed_zip: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error descargando archivo'
        })


@login_required
def get_user_zip_notifications(request):
    """
    Obtiene las notificaciones ZIP del usuario.
    Para mostrar en dashboard/notificaciones.
    """
    try:
        notifications = NotificacionZip.objects.filter(
            user=request.user,
            status='ready',
            expires_at__gt=timezone.now()
        ).order_by('-created_at')

        data = []
        for notif in notifications:
            data.append({
                'job_id': notif.job_id,
                'empresa_nombre': notif.empresa.nombre,
                'created_at': notif.created_at.isoformat(),
                'expires_at': notif.expires_at.isoformat(),
                'downloaded': notif.downloaded_at is not None,
                'download_url': f'/core/download-zip/{notif.job_id}/'
            })

        return JsonResponse({
            'success': True,
            'notifications': data
        })

    except Exception as e:
        logger.error(f"❌ Error en get_user_zip_notifications: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error obteniendo notificaciones'
        })


@login_required
def cancel_zip_job(request, job_id):
    """
    Cancela un trabajo ZIP si está en cola.
    """
    try:
        status = zip_processor.get_job_status(job_id)

        if status.get('status') == 'queued':
            # Marcar como cancelado
            status['status'] = 'cancelled'
            status['cancelled_at'] = timezone.now()

            return JsonResponse({
                'success': True,
                'message': 'Trabajo cancelado exitosamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No se puede cancelar. El trabajo ya está procesando o completado.'
            })

    except Exception as e:
        logger.error(f"❌ Error en cancel_zip_job: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error cancelando trabajo'
        })


# Vista para inicializar el procesador automáticamente
def initialize_zip_processor():
    """
    Inicializa el procesador ZIP al arrancar la aplicación.
    Llamar desde apps.py o signals.
    """
    try:
        zip_processor.start_processor()
        logger.info("🚀 Sistema ZIP asíncrono inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando ZIP processor: {e}")