"""
Decorators personalizados para generación de PDFs
Aseguran que SIEMPRE se devuelva JSON, incluso en errores fatales
"""

import logging
import traceback
from functools import wraps
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def safe_pdf_response(func):
    """
    Decorator que envuelve vistas de generación de PDF para garantizar
    que SIEMPRE devuelvan JSON, incluso si hay errores fatales.

    Esto previene el error "Unexpected token '<'" en el cliente JavaScript
    cuando Django devuelve HTML de error en lugar de JSON.

    Usage:
        @safe_pdf_response
        def generar_pdf_comprobacion(request, equipo_id):
            ...
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            # Intentar ejecutar la función normalmente
            response = func(request, *args, **kwargs)

            # Si la función ya devuelve un JsonResponse, retornarlo
            if isinstance(response, JsonResponse):
                return response

            # Si devuelve otro tipo de respuesta (HttpResponse, etc.), retornarla
            return response

        except Exception as e:
            # Capturar CUALQUIER error y devolver JSON
            error_traceback = traceback.format_exc()

            # Log detallado del error
            logger.error(
                f"Error fatal en generación de PDF ({func.__name__}): {str(e)}\n"
                f"Traceback:\n{error_traceback}"
            )

            # Devolver JSON con error detallado
            error_response = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'function': func.__name__,
            }

            # Solo incluir traceback para superusuarios
            if hasattr(request, 'user') and request.user.is_superuser:
                error_response['traceback'] = error_traceback

            return JsonResponse(error_response, status=500)

    return wrapper


def validate_pdf_data(required_fields=None):
    """
    Decorator que valida que los datos necesarios estén presentes
    antes de intentar generar el PDF.

    Args:
        required_fields (list): Lista de campos requeridos en el POST

    Usage:
        @validate_pdf_data(required_fields=['datos_comprobacion'])
        def generar_pdf_comprobacion(request, equipo_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.method != 'POST':
                return JsonResponse({
                    'success': False,
                    'error': 'Método no permitido. Use POST.'
                }, status=405)

            # Validar campos requeridos si se especificaron
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in request.POST and field not in request.GET:
                        missing_fields.append(field)

                if missing_fields:
                    return JsonResponse({
                        'success': False,
                        'error': f'Campos requeridos faltantes: {", ".join(missing_fields)}',
                        'missing_fields': missing_fields
                    }, status=400)

            # Si todo está bien, ejecutar la función
            return func(request, *args, **kwargs)

        return wrapper
    return decorator
