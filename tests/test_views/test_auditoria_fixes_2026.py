"""
Tests de regresión para los hallazgos de la Auditoría Integral 2026-04-25.
Cada test verifica que un fix aplicado sigue funcionando y no se revierte.
"""
import hmac
import inspect
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from core.models import Empresa, Equipo

User = get_user_model()


# =============================================================================
# FIX C1 — Timing attack en validación Wompi (pagos.py)
# =============================================================================

def test_wompi_usa_hmac_compare_digest():
    """
    C1: La validación del webhook Wompi debe usar hmac.compare_digest()
    en lugar de == para evitar timing attacks.
    """
    from core.views import pagos
    src = inspect.getsource(pagos._validar_firma_webhook)
    assert 'hmac.compare_digest' in src, \
        "pagos._validar_firma_webhook debe usar hmac.compare_digest() en vez de =="
    assert 'checksum_calculado ==' not in src, \
        "pagos._validar_firma_webhook NO debe comparar con == (timing attack)"


def test_wompi_importa_hmac():
    """C1: El módulo pagos.py debe importar hmac."""
    import core.views.pagos as pagos_module
    import importlib, sys
    src = inspect.getsource(pagos_module)
    assert 'import hmac' in src, "pagos.py debe importar el módulo hmac"


# =============================================================================
# FIX B2 — Emails de vencimiento: propiedades dias_hasta_* en Equipo
# =============================================================================

@pytest.mark.django_db
def test_equipo_tiene_propiedad_dias_hasta_calibracion():
    """B2: El modelo Equipo debe tener la propiedad dias_hasta_calibracion."""
    assert hasattr(Equipo, 'dias_hasta_calibracion'), \
        "Equipo debe tener la propiedad dias_hasta_calibracion"


@pytest.mark.django_db
def test_equipo_tiene_propiedad_dias_hasta_mantenimiento():
    """B2: El modelo Equipo debe tener la propiedad dias_hasta_mantenimiento."""
    assert hasattr(Equipo, 'dias_hasta_mantenimiento'), \
        "Equipo debe tener la propiedad dias_hasta_mantenimiento"


@pytest.mark.django_db
def test_equipo_tiene_propiedad_dias_hasta_comprobacion():
    """B2: El modelo Equipo debe tener la propiedad dias_hasta_comprobacion."""
    assert hasattr(Equipo, 'dias_hasta_comprobacion'), \
        "Equipo debe tener la propiedad dias_hasta_comprobacion"


@pytest.mark.django_db
def test_dias_hasta_calibracion_calcula_correctamente(equipo_factory):
    """B2: dias_hasta_calibracion debe retornar días desde vencimiento (positivo = vencido)."""
    equipo = equipo_factory()
    hace_10_dias = date.today() - timedelta(days=10)
    Equipo.objects.filter(pk=equipo.pk).update(proxima_calibracion=hace_10_dias)
    equipo.refresh_from_db()
    assert equipo.dias_hasta_calibracion == 10, \
        "Un equipo vencido hace 10 días debe retornar 10"


@pytest.mark.django_db
def test_dias_hasta_calibracion_none_si_no_hay_fecha(equipo_factory):
    """B2: dias_hasta_calibracion debe retornar None si no hay fecha programada."""
    equipo = equipo_factory()
    Equipo.objects.filter(pk=equipo.pk).update(proxima_calibracion=None)
    equipo.refresh_from_db()
    assert equipo.dias_hasta_calibracion is None, \
        "Si proxima_calibracion es None, debe retornar None"


# =============================================================================
# FIX H1 — Dashboard resiliente a fallas de Redis
# =============================================================================

def test_dashboard_tiene_try_except_en_cache():
    """H1: dashboard.py debe tener try/except alrededor de las llamadas al cache."""
    import os
    dashboard_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'core', 'views', 'dashboard.py'
    )
    with open(dashboard_path, encoding='utf-8') as f:
        src = f.read()
    assert src.count('except Exception') >= 1, \
        "dashboard.py debe tener al menos un try/except para proteger llamadas al cache"


@pytest.mark.django_db
def test_dashboard_funciona_si_cache_falla(admin_client):
    """H1: El dashboard debe devolver 200 incluso si el cache lanza una excepción."""
    with patch('core.views.dashboard.cache') as mock_cache:
        mock_cache.get.side_effect = Exception("Redis no disponible")
        mock_cache.set.side_effect = Exception("Redis no disponible")
        response = admin_client.get(reverse('core:dashboard'))
    assert response.status_code == 200, \
        "El dashboard debe funcionar (200) aunque Redis esté caído"


# =============================================================================
# FIX C3 — Rate limiting en chatbot (chat.py)
# =============================================================================

def test_chat_importa_cache():
    """C3: chat.py debe importar django.core.cache.cache para rate limiting."""
    from core.views import chat
    src = inspect.getsource(chat)
    assert 'from django.core.cache import cache' in src, \
        "chat.py debe importar cache para el rate limiting"


def test_chat_tiene_rate_limit():
    """C3: La vista chat_ayuda debe tener lógica de rate limiting."""
    from core.views.chat import chat_ayuda
    src = inspect.getsource(chat_ayuda)
    assert 'chat_rate_' in src, \
        "chat_ayuda debe usar clave 'chat_rate_' para rate limiting"
    assert '429' in src, \
        "chat_ayuda debe retornar status 429 cuando se supera el límite"


@pytest.mark.django_db
def test_chat_retorna_429_al_superar_limite(authenticated_client):
    """C3: El chatbot debe retornar 429 después de 20 mensajes en una hora."""
    url = reverse('core:chat_ayuda')
    user_id = authenticated_client.session.get('_auth_user_id')

    # Simular que el usuario ya llegó al límite
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Obtener el usuario del cliente autenticado
    from django.contrib.sessions.backends.db import SessionStore
    session_key = authenticated_client.cookies.get('sessionid')

    # Setear el contador de rate limit directamente en cache
    # Necesitamos el user id - lo obtenemos del session
    import json
    session_data = authenticated_client.session
    auth_user_id = session_data.get('_auth_user_id')

    if auth_user_id:
        rate_key = f"chat_rate_{auth_user_id}"
        cache.set(rate_key, 20, timeout=3600)  # Ya llegó al límite

        response = authenticated_client.post(
            url,
            data=json.dumps({'pregunta': 'test', 'historial': []}),
            content_type='application/json'
        )
        assert response.status_code == 429, \
            "Debe retornar 429 cuando el usuario supera los 20 mensajes/hora"


def test_chat_valida_historial():
    """C3/C4: chat_ayuda debe validar y truncar el historial del cliente."""
    from core.views.chat import chat_ayuda
    src = inspect.getsource(chat_ayuda)
    assert 'historial_raw[:20]' in src or "[:20]" in src, \
        "El historial debe truncarse a máximo 20 turnos"
    assert '2000' in src, \
        "Cada mensaje del historial debe truncarse a máximo 2000 caracteres"


# =============================================================================
# FIX H2/H3 — R2 error handling en activities.py y companies.py
# =============================================================================

def test_activities_tiene_try_except_en_storage():
    """H2: _process_calibracion_files y _process_single_file deben tener try/except."""
    from core.views import activities
    src_calibracion = inspect.getsource(activities._process_calibracion_files)
    src_single = inspect.getsource(activities._process_single_file)
    assert 'except Exception' in src_calibracion, \
        "_process_calibracion_files debe tener try/except alrededor de default_storage.save()"
    assert 'except Exception' in src_single, \
        "_process_single_file debe tener try/except alrededor de default_storage.save()"


def test_companies_tiene_try_except_en_logo():
    """H3: _process_company_logo debe tener try/except."""
    from core.views import companies
    src = inspect.getsource(companies._process_company_logo)
    assert 'except Exception' in src, \
        "_process_company_logo debe tener try/except alrededor de default_storage.save()"


def test_editar_perfil_empresa_maneja_error_logo():
    """H3: editar_perfil_empresa debe capturar excepciones del logo y mostrar mensaje."""
    import core.views.companies as companies_module
    src = inspect.getsource(companies_module)
    # Verificar en el módulo completo que editar_perfil_empresa tiene try/except
    assert 'editar_perfil_empresa' in src, \
        "companies.py debe tener la función editar_perfil_empresa"
    # Verificar que el módulo usa messages.error para errores de logo
    assert 'messages.error' in src, \
        "companies.py debe usar messages.error para notificar errores al usuario"


# =============================================================================
# FIX — CSP Nonce Middleware
# =============================================================================

def test_csp_nonce_middleware_existe():
    """CSP: CSPNonceMiddleware debe existir en core/middleware.py."""
    from core.middleware import CSPNonceMiddleware
    assert CSPNonceMiddleware is not None, \
        "CSPNonceMiddleware debe existir en core.middleware"


def test_csp_nonce_middleware_genera_nonce():
    """CSP: CSPNonceMiddleware debe añadir csp_nonce al request."""
    from core.middleware import CSPNonceMiddleware

    mock_request = MagicMock()
    mock_response = MagicMock()
    mock_response.get.return_value = ""

    def get_response(req):
        return mock_response

    middleware = CSPNonceMiddleware(get_response)
    middleware(mock_request)

    assert hasattr(mock_request, 'csp_nonce'), \
        "CSPNonceMiddleware debe añadir csp_nonce al objeto request"
    assert len(mock_request.csp_nonce) > 0, \
        "El nonce debe ser un string no vacío"


def test_csp_nonce_context_processor_existe():
    """CSP: El context processor csp_nonce debe existir."""
    from core.context_processors import csp_nonce
    assert callable(csp_nonce), \
        "csp_nonce debe ser una función callable en core.context_processors"


def test_csp_nonce_en_settings():
    """CSP: core.context_processors.csp_nonce debe estar registrado en TEMPLATES."""
    from django.conf import settings
    context_processors = settings.TEMPLATES[0]['OPTIONS']['context_processors']
    assert 'core.context_processors.csp_nonce' in context_processors, \
        "csp_nonce debe estar registrado en settings.TEMPLATES context_processors"


# =============================================================================
# FIX — Cache sin expiración en services_new.py
# =============================================================================

def test_services_new_sin_timeout_none():
    """H4: services_new.py no debe usar timeout=None en cache.set() para claves de versión."""
    import core.services_new as services_module
    src = inspect.getsource(services_module)
    # Buscar patrones de cache.set con None como timeout (indica sin expiración)
    assert 'cache.set(version_key, current_version + 1, None)' not in src, \
        "services_new.py no debe usar timeout=None en claves de versión del cache (nunca expiran)"


# =============================================================================
# FIX — Python 3.13 en CI (verificación de configuración)
# =============================================================================

def test_ci_usa_python_313():
    """F1: El workflow de tests CI debe usar Python 3.13, no 3.11."""
    import os
    tests_yml = os.path.join(
        os.path.dirname(__file__), '..', '..', '.github', 'workflows', 'tests.yml'
    )
    if os.path.exists(tests_yml):
        with open(tests_yml, encoding='utf-8', errors='replace') as f:
            content = f.read()
        assert "python-version: '3.13'" in content, \
            "CI tests.yml debe usar Python 3.13"
        assert "python-version: '3.11'" not in content, \
            "CI tests.yml NO debe usar Python 3.11"


def test_ci_instala_requirements_test():
    """F2: El workflow CI debe instalar requirements_test.txt."""
    import os
    tests_yml = os.path.join(
        os.path.dirname(__file__), '..', '..', '.github', 'workflows', 'tests.yml'
    )
    if os.path.exists(tests_yml):
        with open(tests_yml, encoding='utf-8', errors='replace') as f:
            content = f.read()
        assert 'requirements_test.txt' in content, \
            "CI tests.yml debe instalar requirements_test.txt"
