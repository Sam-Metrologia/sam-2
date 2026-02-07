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
