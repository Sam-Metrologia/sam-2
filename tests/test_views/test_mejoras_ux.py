"""
Tests de Mejoras UX SAM
Verifica que las implementaciones de mejoras UX funcionan correctamente.

Nota: Este archivo fue corregido para usar assert en lugar de return (D3 — Apr 2026).
"""

import os

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.models import Empresa, Equipo

User = get_user_model()


@pytest.mark.django_db
def test_permissions():
    """Test 1: Verificar permisos de eliminación por rol de usuario."""
    assert hasattr(User, 'puede_eliminar_equipos'), \
        "El método puede_eliminar_equipos() debe existir en el modelo de usuario"

    empresa, _ = Empresa.objects.get_or_create(
        nombre='Empresa Test Permisos',
        defaults={'nit': '123456789-0'}
    )

    tecnico, _ = User.objects.get_or_create(
        username='tecnico_test_ux',
        defaults={
            'empresa': empresa,
            'rol_usuario': 'TECNICO',
            'email': 'tecnico_ux@test.com',
        }
    )
    assert not tecnico.puede_eliminar_equipos, \
        "Un TÉCNICO NO debe poder eliminar equipos"

    admin, _ = User.objects.get_or_create(
        username='admin_test_ux',
        defaults={
            'empresa': empresa,
            'rol_usuario': 'ADMINISTRADOR',
            'email': 'admin_ux@test.com',
        }
    )
    assert admin.puede_eliminar_equipos, \
        "Un ADMINISTRADOR SÍ debe poder eliminar equipos"

    gerente, _ = User.objects.get_or_create(
        username='gerente_test_ux',
        defaults={
            'empresa': empresa,
            'rol_usuario': 'GERENCIA',
            'email': 'gerente_ux@test.com',
        }
    )
    assert gerente.puede_eliminar_equipos, \
        "Un usuario de GERENCIA SÍ debe poder eliminar equipos"


def test_middleware():
    """Test 2: Verificar que el middleware de sesión está activo y en orden correcto."""
    from django.conf import settings

    middlewares = settings.MIDDLEWARE

    has_session_middleware = any('SessionActivityMiddleware' in m for m in middlewares)
    assert has_session_middleware, \
        "SessionActivityMiddleware debe estar registrado en MIDDLEWARE"

    auth_index = next(
        (i for i, m in enumerate(middlewares) if 'AuthenticationMiddleware' in m), -1
    )
    session_index = next(
        (i for i, m in enumerate(middlewares) if 'SessionActivityMiddleware' in m), -1
    )

    if auth_index != -1 and session_index != -1:
        assert session_index > auth_index, \
            "SessionActivityMiddleware debe ir después de AuthenticationMiddleware"


def test_heartbeat_endpoint():
    """Test 3: Verificar que el endpoint de heartbeat de sesión existe."""
    from core.views import base

    url = reverse('core:session_heartbeat')
    assert url, "La URL 'core:session_heartbeat' debe poder resolverse"

    assert hasattr(base, 'session_heartbeat'), \
        "La vista session_heartbeat debe existir en core.views.base"


def test_navigation_logic():
    """Test 4: Verificar que la lógica de navegación entre equipos está implementada."""
    import inspect

    from core.views import equipment

    source = inspect.getsource(equipment.editar_equipo)

    assert 'prev_equipo_id' in source, \
        "La vista editar_equipo debe tener lógica para equipo anterior (prev_equipo_id)"
    assert 'next_equipo_id' in source, \
        "La vista editar_equipo debe tener lógica para equipo siguiente (next_equipo_id)"
    assert 'current_position' in source, \
        "La vista editar_equipo debe incluir indicador de posición (current_position)"


def test_static_files():
    """Test 5: Verificar que el archivo JS de heartbeat de sesión existe y tiene el contenido esperado."""
    from django.conf import settings

    js_path = os.path.join(
        settings.BASE_DIR, 'core', 'static', 'core', 'js', 'session_keepalive.js'
    )
    assert os.path.exists(js_path), \
        f"El archivo session_keepalive.js debe existir en {js_path}"

    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert 'sendHeartbeat' in content, \
        "session_keepalive.js debe contener la función sendHeartbeat"
    assert 'lastActivityTime' in content, \
        "session_keepalive.js debe rastrear la actividad del usuario (lastActivityTime)"
    assert 'showWarning' in content, \
        "session_keepalive.js debe incluir el sistema de advertencias (showWarning)"


@pytest.mark.django_db
def test_database():
    """Test 6: Verificar que el modelo Equipo tiene el campo puntos_calibracion y responde a queries."""
    equipo_fields = [f.name for f in Equipo._meta.get_fields()]
    assert 'puntos_calibracion' in equipo_fields, \
        "El modelo Equipo debe tener el campo 'puntos_calibracion'"

    count = Equipo.objects.count()
    assert count >= 0, "La query a Equipo.objects.count() debe funcionar"
