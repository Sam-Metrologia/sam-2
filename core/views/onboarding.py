# core/views/onboarding.py
# Vistas y helpers para el onboarding guiado de usuarios trial.

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST

from ..models import OnboardingProgress

logger = logging.getLogger(__name__)


def _marcar_paso_onboarding(user, paso):
    """Marca un paso de onboarding si el usuario tiene progreso activo."""
    progress = getattr(user, 'onboarding_progress', None)
    if progress:
        try:
            progress = OnboardingProgress.objects.get(usuario=user)
            progress.marcar_paso(paso)
        except OnboardingProgress.DoesNotExist:
            pass


@login_required
@require_http_methods(["GET"])
def onboarding_progreso(request):
    """API: retorna progreso del onboarding como JSON."""
    progress = getattr(request.user, 'onboarding_progress', None)
    if not progress:
        return JsonResponse({'has_onboarding': False})
    return JsonResponse({
        'has_onboarding': True,
        'tour_completado': progress.tour_completado,
        'pasos': {
            'crear_equipo': progress.paso_crear_equipo,
            'registrar_calibracion': progress.paso_registrar_calibracion,
            'generar_reporte': progress.paso_generar_reporte,
        },
        'pasos_completados': progress.pasos_completados,
        'total_pasos': progress.total_pasos,
        'porcentaje': progress.porcentaje,
    })


@login_required
@require_POST
def onboarding_completar_tour(request):
    """API: marca el tour de Shepherd.js como completado."""
    progress = getattr(request.user, 'onboarding_progress', None)
    if progress and not progress.tour_completado:
        progress.tour_completado = True
        progress.save(update_fields=['tour_completado'])
    return JsonResponse({'ok': True})
