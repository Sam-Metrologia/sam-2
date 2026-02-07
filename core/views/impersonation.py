# core/views/impersonation.py
"""
Vistas para el sistema de impersonación (Modo Trabajo SAM).
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import logging

from ..models import Empresa, CustomUser
from ..utils.impersonation import (
    start_impersonation,
    stop_impersonation,
    is_impersonating,
    get_users_for_empresa,
    get_default_user_for_empresa,
    get_impersonator
)

logger = logging.getLogger(__name__)


@login_required
@require_POST
def iniciar_modo_trabajo(request):
    """
    Inicia el modo trabajo impersonando a un usuario de una empresa.

    POST params:
        empresa_id: ID de la empresa
        user_id (opcional): ID del usuario específico a impersonar
    """
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Solo superusuarios pueden usar el modo trabajo'
        }, status=403)

    empresa_id = request.POST.get('empresa_id')
    user_id = request.POST.get('user_id')

    if not empresa_id:
        return JsonResponse({
            'success': False,
            'error': 'Debe seleccionar una empresa'
        }, status=400)

    try:
        empresa = Empresa.objects.get(id=empresa_id, is_deleted=False)
    except Empresa.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Empresa no encontrada'
        }, status=404)

    # Si se especificó un usuario, usarlo
    if user_id:
        try:
            target_user = CustomUser.objects.get(
                id=user_id,
                empresa=empresa,
                is_active=True,
                is_superuser=False
            )
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no encontrado en esta empresa'
            }, status=404)
    else:
        # Buscar usuario por defecto (gerente)
        target_user = get_default_user_for_empresa(empresa)

        if not target_user:
            return JsonResponse({
                'success': False,
                'error': f'No hay usuarios activos en {empresa.nombre}',
                'need_user_selection': True,
                'users': []
            }, status=400)

    # Iniciar impersonación
    if start_impersonation(request, target_user):
        logger.info(
            f"Superusuario {get_impersonator(request)} inició modo trabajo como {target_user} en {empresa.nombre}"
        )

        messages.success(
            request,
            f"Modo trabajo activado. Ahora estás viendo como {target_user.get_full_name() or target_user.username} ({empresa.nombre})"
        )

        return JsonResponse({
            'success': True,
            'message': f'Modo trabajo activado como {target_user.get_full_name() or target_user.username}',
            'redirect': '/core/dashboard/'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'No se pudo iniciar el modo trabajo'
        }, status=500)


@login_required
@require_POST
def salir_modo_trabajo(request):
    """
    Sale del modo trabajo y vuelve al superusuario original.
    """
    if not is_impersonating(request):
        return JsonResponse({
            'success': False,
            'error': 'No estás en modo trabajo'
        }, status=400)

    # Obtener info antes de salir para el log
    impersonator = get_impersonator(request)
    impersonated_user = request.user

    if stop_impersonation(request):
        logger.info(
            f"Superusuario {impersonator} salió del modo trabajo (era {impersonated_user})"
        )

        messages.info(request, "Has salido del modo trabajo")

        return JsonResponse({
            'success': True,
            'message': 'Has salido del modo trabajo',
            'redirect': '/core/dashboard/'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'No se pudo salir del modo trabajo'
        }, status=500)


@login_required
@require_GET
def obtener_usuarios_empresa(request, empresa_id):
    """
    Obtiene la lista de usuarios de una empresa para el selector.
    """
    if not request.user.is_superuser and not is_impersonating(request):
        return JsonResponse({
            'success': False,
            'error': 'No tienes permiso para ver esta información'
        }, status=403)

    try:
        empresa = Empresa.objects.get(id=empresa_id, is_deleted=False)
    except Empresa.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Empresa no encontrada'
        }, status=404)

    usuarios = get_users_for_empresa(empresa)
    default_user = get_default_user_for_empresa(empresa)

    usuarios_list = [{
        'id': u.id,
        'nombre': u.get_full_name() or u.username,
        'username': u.username,
        'rol': u.get_rol_usuario_display() if hasattr(u, 'get_rol_usuario_display') else u.rol_usuario,
        'es_default': u.id == default_user.id if default_user else False
    } for u in usuarios]

    return JsonResponse({
        'success': True,
        'empresa': {
            'id': empresa.id,
            'nombre': empresa.nombre
        },
        'usuarios': usuarios_list,
        'tiene_usuarios': len(usuarios_list) > 0
    })


@login_required
@require_GET
def estado_modo_trabajo(request):
    """
    Retorna el estado actual del modo trabajo.
    """
    impersonating = is_impersonating(request)
    impersonator = get_impersonator(request) if impersonating else None

    return JsonResponse({
        'activo': impersonating,
        'usuario_actual': {
            'id': request.user.id,
            'nombre': request.user.get_full_name() or request.user.username,
            'empresa': request.user.empresa.nombre if request.user.empresa else None,
            'rol': request.user.rol_usuario if hasattr(request.user, 'rol_usuario') else None
        } if impersonating else None,
        'superusuario_original': {
            'id': impersonator.id,
            'nombre': impersonator.get_full_name() or impersonator.username
        } if impersonator else None
    })
