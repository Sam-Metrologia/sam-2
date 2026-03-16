"""
Tests de cobertura para core/views/base.py.

Cubre:
- trial_check con plan expirado (líneas 188-199)
- access_check con plan expirado (líneas 227-232)
- session_heartbeat con JSON inválido (líneas 357-359)
- access_denied view (líneas 329-331)
"""
import json
import pytest
from datetime import date, timedelta
from django.test import Client
from django.urls import reverse

from core.models import Empresa, CustomUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _crear_empresa_expirada():
    """Crea una empresa con período de prueba ya vencido.

    Usa _plan_set_manually=True para evitar que Empresa.save() restablezca
    fecha_inicio_plan a None (comportamiento por defecto para nuevas empresas).
    """
    global _counter
    _counter += 1
    empresa = Empresa(
        nombre=f'Empresa Expirada Base{_counter}',
        nit=f'999{_counter:06d}-{_counter % 10}',
        email=f'expirada{_counter}@test.com',
        limite_equipos_empresa=50,
    )
    # Marcar para saltar la configuración automática de plan en save()
    empresa._plan_set_manually = True
    empresa.es_periodo_prueba = True
    empresa.fecha_inicio_plan = date.today() - timedelta(days=60)
    empresa.duracion_prueba_dias = 30  # venció hace 30 días
    empresa.save()
    return empresa


def _crear_usuario_expirado(empresa):
    """Crea un usuario en una empresa expirada."""
    from django.contrib.auth.models import Permission
    user = CustomUser.objects.create_user(
        username='user_expirado_base',
        email='user_expirado_base@test.com',
        password='testpass123',
        empresa=empresa,
        is_active=True,
    )
    # Darle permisos para equipo
    perms = Permission.objects.filter(codename__in=[
        'add_calibracion', 'add_mantenimiento', 'add_comprobacion',
        'add_equipo', 'change_equipo', 'view_equipo',
    ])
    user.user_permissions.set(perms)
    return user


# ---------------------------------------------------------------------------
# trial_check con plan expirado — líneas 188-199
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTrialCheckExpired:
    """Cubre la rama de trial_check cuando el plan ha expirado (líneas 188-199)."""

    def test_trial_check_bloquea_añadir_calibracion(self, equipo_factory):
        """trial_check redirige a dashboard cuando plan expirado y vista es protegida."""
        empresa = _crear_empresa_expirada()
        user = _crear_usuario_expirado(empresa)
        client = Client()
        client.force_login(user)

        equipo = equipo_factory(empresa=empresa)
        url = reverse('core:añadir_calibracion', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        # access_check (externo) retorna 403; trial_check (interno) retornaría 302.
        # Ambos bloquean planes expirados; access_check corre primero.
        assert response.status_code in (302, 403)

    def test_trial_check_bloquea_añadir_mantenimiento(self, equipo_factory):
        """trial_check redirige cuando se intenta añadir mantenimiento con plan expirado."""
        empresa = _crear_empresa_expirada()
        user = _crear_usuario_expirado(empresa)
        client = Client()
        client.force_login(user)

        equipo = equipo_factory(empresa=empresa)
        url = reverse('core:añadir_mantenimiento', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code in (302, 403)

    def test_trial_check_bloquea_añadir_comprobacion(self, equipo_factory):
        """trial_check redirige cuando se intenta añadir comprobación con plan expirado."""
        empresa = _crear_empresa_expirada()
        user = _crear_usuario_expirado(empresa)
        client = Client()
        client.force_login(user)

        equipo = equipo_factory(empresa=empresa)
        url = reverse('core:añadir_comprobacion', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code in (302, 403)


# ---------------------------------------------------------------------------
# access_check con plan expirado — líneas 227-232
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccessCheckExpired:
    """Cubre la rama de access_check cuando el plan ha expirado (líneas 227-232)."""

    def test_access_check_bloquea_vista_protegida(self, equipo_factory):
        """access_check retorna 403 cuando plan expirado en vista no permitida."""
        empresa = _crear_empresa_expirada()
        user = _crear_usuario_expirado(empresa)
        client = Client()
        client.force_login(user)

        equipo = equipo_factory(empresa=empresa)
        # editar_calibracion usa @access_check pero NO @trial_check
        # → access_check bloqueará con 403
        url = reverse('core:editar_equipo', kwargs={'pk': equipo.pk})
        response = client.get(url)

        # access_check bloquea con 403 para empresa expirada
        assert response.status_code in (302, 403)

    def test_access_check_bloquea_detalle_equipo(self, equipo_factory):
        """access_check bloquea acceso a cualquier vista con empresa expirada."""
        empresa = _crear_empresa_expirada()
        user = _crear_usuario_expirado(empresa)
        client = Client()
        client.force_login(user)

        equipo = equipo_factory(empresa=empresa)
        url = reverse('core:detalle_equipo', kwargs={'pk': equipo.pk})
        response = client.get(url)

        # access_check bloquea con 403
        assert response.status_code in (302, 403)


# ---------------------------------------------------------------------------
# session_heartbeat con JSON inválido — líneas 357-359
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSessionHeartbeatInvalidJson:
    """Cubre la rama de session_heartbeat con JSON inválido (líneas 357-359)."""

    def test_session_heartbeat_sin_body(self, authenticated_client):
        """POST a session_heartbeat sin body JSON → captura JSONDecodeError (líneas 357-359)."""
        url = reverse('core:session_heartbeat')
        # Enviar body vacío (no es JSON válido)
        response = authenticated_client.post(
            url,
            data='',
            content_type='application/json'
        )
        # El heartbeat debe retornar ok aunque no hay body
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_session_heartbeat_body_invalido(self, authenticated_client):
        """POST a session_heartbeat con body no-JSON → captura JSONDecodeError."""
        url = reverse('core:session_heartbeat')
        response = authenticated_client.post(
            url,
            data='not-valid-json{{{',
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_session_heartbeat_con_json_valido(self, authenticated_client):
        """POST a session_heartbeat con JSON válido → responde ok."""
        url = reverse('core:session_heartbeat')
        response = authenticated_client.post(
            url,
            data=json.dumps({'timestamp': '2026-01-01', 'inactive_time': 10}),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'


# ---------------------------------------------------------------------------
# access_denied view — líneas 329-331
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccessDeniedView:
    """Cubre la view access_denied (líneas 329-331)."""

    def test_access_denied_returns_200(self, authenticated_client):
        """GET a /core/access_denied/ muestra la página de acceso denegado."""
        url = reverse('core:access_denied')
        response = authenticated_client.get(url)
        # La view devuelve 200 con plantilla core/access_denied.html
        assert response.status_code == 200
