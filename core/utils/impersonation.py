# core/utils/impersonation.py
"""
Sistema de Impersonación para Superusuarios SAM.
Permite a superusuarios "entrar" como usuarios de empresas específicas.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

# Clave de sesión para guardar el ID del superusuario original
IMPERSONATOR_SESSION_KEY = '_impersonator_user_id'


def is_impersonating(request):
    """
    Verifica si el usuario actual está impersonando a otro.

    Returns:
        bool: True si está impersonando, False si no
    """
    return IMPERSONATOR_SESSION_KEY in request.session


def get_impersonator(request):
    """
    Obtiene el usuario original (superusuario) que está impersonando.

    Returns:
        User or None: El superusuario original, o None si no está impersonando
    """
    if not is_impersonating(request):
        return None

    try:
        impersonator_id = request.session.get(IMPERSONATOR_SESSION_KEY)
        return User.objects.get(id=impersonator_id)
    except User.DoesNotExist:
        return None


def start_impersonation(request, target_user):
    """
    Inicia la impersonación de un usuario.
    Solo superusuarios pueden impersonar.
    Si ya está impersonando, cambia al nuevo usuario manteniendo el superusuario original.

    Args:
        request: HttpRequest
        target_user: Usuario a impersonar

    Returns:
        bool: True si se inició correctamente, False si no
    """
    # No puede impersonar a otro superusuario
    if target_user.is_superuser:
        return False

    # Verificar permisos: debe ser superusuario O estar ya impersonando
    already_impersonating = is_impersonating(request)

    if already_impersonating:
        # Ya está impersonando, verificar que el superusuario original existe
        impersonator = get_impersonator(request)
        if not impersonator or not impersonator.is_superuser:
            return False
        # Mantener el ID del superusuario original (no sobrescribir)
        original_superuser_id = request.session.get(IMPERSONATOR_SESSION_KEY)
    else:
        # No está impersonando, verificar que el usuario actual es superusuario
        if not request.user.is_superuser:
            return False
        # Guardar el ID del superusuario original
        original_superuser_id = request.user.id

    # Guardar/mantener el ID del superusuario original
    request.session[IMPERSONATOR_SESSION_KEY] = original_superuser_id

    # Cambiar la sesión al usuario objetivo
    from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY

    # Guardar datos del usuario objetivo en la sesión
    request.session[SESSION_KEY] = target_user.pk
    request.session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    request.session[HASH_SESSION_KEY] = target_user.get_session_auth_hash()

    return True


def stop_impersonation(request):
    """
    Detiene la impersonación y vuelve al superusuario original.

    Returns:
        bool: True si se detuvo correctamente, False si no estaba impersonando
    """
    if not is_impersonating(request):
        return False

    impersonator_id = request.session.pop(IMPERSONATOR_SESSION_KEY, None)

    if impersonator_id:
        try:
            impersonator = User.objects.get(id=impersonator_id)

            # Restaurar sesión al superusuario original
            from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY

            request.session[SESSION_KEY] = impersonator.pk
            request.session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
            request.session[HASH_SESSION_KEY] = impersonator.get_session_auth_hash()

            return True
        except User.DoesNotExist:
            return False

    return False


def get_users_for_empresa(empresa):
    """
    Obtiene los usuarios de una empresa, ordenados por rol (Gerentes primero).

    Args:
        empresa: Objeto Empresa

    Returns:
        QuerySet de usuarios
    """
    return User.objects.filter(
        empresa=empresa,
        is_active=True,
        is_superuser=False
    ).order_by(
        # Gerentes primero, luego admin, luego técnicos
        '-rol_usuario'
    )


def get_default_user_for_empresa(empresa):
    """
    Obtiene el usuario por defecto para impersonar en una empresa.
    Prioridad: GERENCIA > ADMINISTRADOR > cualquier otro

    Args:
        empresa: Objeto Empresa

    Returns:
        User or None
    """
    # Primero buscar gerente
    gerente = User.objects.filter(
        empresa=empresa,
        rol_usuario='GERENCIA',
        is_active=True,
        is_superuser=False
    ).first()

    if gerente:
        return gerente

    # Si no hay gerente, buscar administrador
    admin = User.objects.filter(
        empresa=empresa,
        rol_usuario='ADMINISTRADOR',
        is_active=True,
        is_superuser=False
    ).first()

    if admin:
        return admin

    # Si no hay admin, cualquier usuario activo
    return User.objects.filter(
        empresa=empresa,
        is_active=True,
        is_superuser=False
    ).first()
