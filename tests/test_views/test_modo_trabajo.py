# tests/test_views/test_modo_trabajo.py
"""
Tests para el sistema de Modo Trabajo (Impersonación).
"""

import pytest
from django.urls import reverse
from django.test import Client
from core.models import CustomUser, Empresa


@pytest.fixture
def superuser(db):
    """Crea un superusuario para tests."""
    return CustomUser.objects.create_superuser(
        username='superadmin',
        email='super@test.com',
        password='super123',
        first_name='Super',
        last_name='Admin'
    )


@pytest.fixture
def empresa_test(db):
    """Crea una empresa de prueba."""
    return Empresa.objects.create(
        nombre='Empresa Test',
        nit='123456789',
        direccion='Test Address',
        telefono='1234567',
        email='test@empresa.com'
    )


@pytest.fixture
def usuario_empresa(db, empresa_test):
    """Crea un usuario normal asociado a una empresa."""
    return CustomUser.objects.create_user(
        username='usuario_empresa',
        email='user@empresa.com',
        password='user123',
        first_name='Usuario',
        last_name='Empresa',
        empresa=empresa_test,
        rol_usuario='TECNICO'
    )


@pytest.fixture
def gerente_empresa(db, empresa_test):
    """Crea un gerente asociado a una empresa."""
    return CustomUser.objects.create_user(
        username='gerente_empresa',
        email='gerente@empresa.com',
        password='gerente123',
        first_name='Gerente',
        last_name='Empresa',
        empresa=empresa_test,
        rol_usuario='GERENCIA'
    )


class TestModoTrabajoAcceso:
    """Tests de control de acceso al modo trabajo."""

    def test_solo_superusuario_puede_iniciar_modo_trabajo(self, client, superuser, empresa_test, gerente_empresa):
        """Verifica que solo superusuarios pueden iniciar modo trabajo."""
        client.login(username='superadmin', password='super123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_usuario_normal_no_puede_iniciar_modo_trabajo(self, client, usuario_empresa, empresa_test):
        """Verifica que usuarios normales no pueden iniciar modo trabajo."""
        client.login(username='usuario_empresa', password='user123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )

        assert response.status_code == 403
        data = response.json()
        assert data['success'] is False

    def test_empresa_invalida_retorna_error(self, client, superuser):
        """Verifica que una empresa inválida retorna error."""
        client.login(username='superadmin', password='super123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': 99999}
        )

        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False


class TestModoTrabajoSesion:
    """Tests de manejo de sesión en modo trabajo."""

    def test_iniciar_modo_trabajo_guarda_en_sesion(self, client, superuser, empresa_test, gerente_empresa):
        """Verifica que iniciar modo trabajo guarda el estado en sesión."""
        client.login(username='superadmin', password='super123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )

        assert response.status_code == 200

        # Verificar estado del modo trabajo
        estado_response = client.get(reverse('core:estado_modo_trabajo'))
        estado_data = estado_response.json()

        assert estado_data['activo'] is True

    def test_salir_modo_trabajo_limpia_sesion(self, client, superuser, empresa_test, gerente_empresa):
        """Verifica que salir del modo trabajo limpia la sesión."""
        client.login(username='superadmin', password='super123')

        # Iniciar modo trabajo
        client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )

        # Salir del modo trabajo
        response = client.post(reverse('core:salir_modo_trabajo'))
        assert response.status_code == 200

        # Verificar estado
        estado_response = client.get(reverse('core:estado_modo_trabajo'))
        estado_data = estado_response.json()

        assert estado_data['activo'] is False


class TestModoTrabajoUsuarios:
    """Tests de selección de usuarios en modo trabajo."""

    def test_obtener_usuarios_empresa(self, client, superuser, empresa_test, gerente_empresa, usuario_empresa):
        """Verifica que se pueden obtener los usuarios de una empresa."""
        client.login(username='superadmin', password='super123')

        response = client.get(
            reverse('core:obtener_usuarios_empresa', args=[empresa_test.id])
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['usuarios']) == 2  # gerente y usuario
        assert data['tiene_usuarios'] is True

    def test_iniciar_modo_trabajo_con_usuario_especifico(self, client, superuser, empresa_test, usuario_empresa):
        """Verifica que se puede iniciar modo trabajo con un usuario específico."""
        client.login(username='superadmin', password='super123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {
                'empresa_id': empresa_test.id,
                'user_id': usuario_empresa.id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_gerente_es_usuario_por_defecto(self, client, superuser, empresa_test, gerente_empresa, usuario_empresa):
        """Verifica que el gerente es el usuario por defecto."""
        client.login(username='superadmin', password='super123')

        # Iniciar sin especificar usuario
        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )

        assert response.status_code == 200

        # Verificar estado
        estado_response = client.get(reverse('core:estado_modo_trabajo'))
        estado_data = estado_response.json()

        # El usuario actual debería ser el gerente
        assert estado_data['usuario_actual']['id'] == gerente_empresa.id

    def test_cambiar_usuario_mientras_impersona(self, client, superuser, empresa_test, gerente_empresa, usuario_empresa):
        """Verifica que se puede cambiar de usuario mientras ya se está impersonando."""
        client.login(username='superadmin', password='super123')

        # Iniciar como gerente
        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )
        assert response.status_code == 200

        # Verificar que estamos como gerente
        estado_response = client.get(reverse('core:estado_modo_trabajo'))
        estado_data = estado_response.json()
        assert estado_data['activo'] is True
        assert estado_data['usuario_actual']['id'] == gerente_empresa.id

        # Ahora cambiar a usuario (técnico) mientras ya estamos impersonando
        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {
                'empresa_id': empresa_test.id,
                'user_id': usuario_empresa.id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # Verificar que ahora estamos como el usuario técnico
        estado_response = client.get(reverse('core:estado_modo_trabajo'))
        estado_data = estado_response.json()
        assert estado_data['activo'] is True
        assert estado_data['usuario_actual']['id'] == usuario_empresa.id

        # Verificar que el superusuario original sigue siendo el mismo
        assert estado_data['superusuario_original']['id'] == superuser.id


class TestModoTrabajoContextProcessor:
    """Tests del context processor para modo trabajo."""

    def test_context_processor_sin_login(self, client):
        """Verifica que el context processor funciona sin login."""
        response = client.get(reverse('core:login'))
        assert response.status_code == 200

    def test_context_processor_superuser_ve_selector(self, client, superuser, empresa_test):
        """Verifica que superusuario ve el selector de empresas."""
        client.login(username='superadmin', password='super123')

        response = client.get(reverse('core:dashboard'))
        assert response.status_code == 200

        # Verificar que el context tiene las variables esperadas
        context = response.context
        assert 'puede_usar_modo_trabajo' in context
        assert context['puede_usar_modo_trabajo'] is True

    def test_context_processor_usuario_normal_no_ve_selector(self, client, usuario_empresa):
        """Verifica que usuario normal no ve el selector."""
        client.login(username='usuario_empresa', password='user123')

        response = client.get(reverse('core:dashboard'))
        assert response.status_code == 200

        context = response.context
        assert 'puede_usar_modo_trabajo' in context
        assert context['puede_usar_modo_trabajo'] is False


class TestModoTrabajoSeguridad:
    """Tests de seguridad del modo trabajo."""

    def test_no_puede_impersonar_superusuario(self, client, superuser, empresa_test):
        """Verifica que no se puede impersonar a otro superusuario."""
        # Crear otro superusuario con empresa
        otro_super = CustomUser.objects.create_superuser(
            username='otro_super',
            email='otro@test.com',
            password='otro123',
            empresa=empresa_test
        )

        client.login(username='superadmin', password='super123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {
                'empresa_id': empresa_test.id,
                'user_id': otro_super.id
            }
        )

        # Debería fallar porque no puede impersonar superusuario
        assert response.status_code == 404

    def test_empresa_eliminada_no_permite_modo_trabajo(self, client, superuser, empresa_test, gerente_empresa):
        """Verifica que empresa eliminada no permite modo trabajo."""
        # Marcar empresa como eliminada
        empresa_test.is_deleted = True
        empresa_test.save()

        client.login(username='superadmin', password='super123')

        response = client.post(
            reverse('core:iniciar_modo_trabajo'),
            {'empresa_id': empresa_test.id}
        )

        assert response.status_code == 404
        data = response.json()
        assert data['success'] is False


# =====================================================================
# Tests unitarios para core.utils.impersonation
# =====================================================================

@pytest.mark.django_db
class TestImpersonationUtils:
    """Tests unitarios de las funciones en core.utils.impersonation."""

    def _make_mock_request(self, session_data=None):
        """Crea un mock de request con sesión."""
        from unittest.mock import MagicMock
        request = MagicMock()
        request.session = dict(session_data or {})
        return request

    def test_is_impersonating_false_cuando_no_hay_clave(self):
        """is_impersonating retorna False si no hay clave de impersonación."""
        from core.utils.impersonation import is_impersonating
        request = self._make_mock_request()
        assert is_impersonating(request) is False

    def test_get_impersonator_retorna_none_si_no_impersona(self):
        """get_impersonator retorna None si no está impersonando (línea 33)."""
        from core.utils.impersonation import get_impersonator
        request = self._make_mock_request()
        result = get_impersonator(request)
        assert result is None

    def test_get_impersonator_retorna_none_si_user_no_existe(self, db):
        """get_impersonator retorna None si el ID de superusuario ya no existe (líneas 38-39)."""
        from core.utils.impersonation import get_impersonator, IMPERSONATOR_SESSION_KEY
        request = self._make_mock_request({IMPERSONATOR_SESSION_KEY: 999999})
        result = get_impersonator(request)
        assert result is None

    def test_start_impersonation_falla_con_superusuario_target(self, superuser, usuario_empresa):
        """start_impersonation retorna False si el target es superusuario (línea 57)."""
        from core.utils.impersonation import start_impersonation
        request = self._make_mock_request()
        request.user = superuser
        result = start_impersonation(request, superuser)  # target es superusuario
        assert result is False

    def test_start_impersonation_falla_si_usuario_normal_sin_sesion(self, usuario_empresa, empresa_test):
        """start_impersonation retorna False si usuario no es superusuario (línea 72)."""
        from core.utils.impersonation import start_impersonation
        request = self._make_mock_request()
        request.user = usuario_empresa  # NO es superusuario
        # Crear un target válido (no superusuario)
        target = CustomUser.objects.create_user(
            username='target_util',
            email='target@util.com',
            password='pass123',
            empresa=empresa_test,
        )
        result = start_impersonation(request, target)
        assert result is False

    def test_stop_impersonation_retorna_false_si_no_impersona(self):
        """stop_impersonation retorna False si no está impersonando (línea 98)."""
        from core.utils.impersonation import stop_impersonation
        request = self._make_mock_request()
        result = stop_impersonation(request)
        assert result is False

    def test_stop_impersonation_retorna_false_si_impersonator_no_existe(self, db):
        """stop_impersonation retorna False si el impersonator ya no existe en BD (líneas 114-117)."""
        from core.utils.impersonation import stop_impersonation, IMPERSONATOR_SESSION_KEY
        from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
        request = self._make_mock_request({
            IMPERSONATOR_SESSION_KEY: 999999,  # ID que no existe
        })
        result = stop_impersonation(request)
        assert result is False

    def test_get_default_user_sin_gerente_retorna_admin(self, empresa_test):
        """get_default_user_for_empresa retorna admin cuando no hay gerente (líneas 163-171)."""
        from core.utils.impersonation import get_default_user_for_empresa
        # Crear solo un admin (sin gerente)
        admin = CustomUser.objects.create_user(
            username='admin_default',
            email='admin_default@test.com',
            password='pass123',
            empresa=empresa_test,
            rol_usuario='ADMINISTRADOR',
        )
        result = get_default_user_for_empresa(empresa_test)
        assert result == admin

    def test_get_default_user_sin_gerente_ni_admin_retorna_cualquiera(self, empresa_test):
        """get_default_user_for_empresa retorna cualquier activo si no hay gerente ni admin (líneas 173-178)."""
        from core.utils.impersonation import get_default_user_for_empresa
        # Crear solo un técnico
        tecnico = CustomUser.objects.create_user(
            username='tecnico_default',
            email='tecnico_default@test.com',
            password='pass123',
            empresa=empresa_test,
            rol_usuario='TECNICO',
        )
        result = get_default_user_for_empresa(empresa_test)
        assert result == tecnico
