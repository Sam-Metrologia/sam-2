"""
Test de regresión: al cambiar su propia contraseña en el modal de
"Configurar Usuarios" post-compra, el usuario no debe quedar desconectado
de su sesión actual (bug real: faltaba update_session_auth_hash).
"""
import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import EmpresaFactory, UserFactory


@pytest.mark.django_db
class TestConfigurarUsuariosSetupSesion:

    def test_admin_no_pierde_sesion_al_cambiar_su_propia_clave(self):
        empresa = EmpresaFactory(configurar_usuarios_plan_pendiente=True)
        admin = UserFactory(
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            username='admin_original',
            password='claveVieja123',
        )

        client = Client()
        assert client.login(username='admin_original', password='claveVieja123')

        resp = client.post(reverse('core:configurar_usuarios_setup'), data={
            f'usuario_{admin.id}_username': 'admin_original',
            f'usuario_{admin.id}_first_name': 'Admin',
            f'usuario_{admin.id}_last_name': 'Prueba',
            f'usuario_{admin.id}_email': 'admin@empresa-real.com',
            f'usuario_{admin.id}_password': 'claveNuevaSegura2026!',
        })
        assert resp.status_code == 302
        assert resp.url == reverse('core:dashboard')

        # La sesión debe seguir autenticada como el mismo admin, sin necesidad
        # de volver a loguearse.
        dashboard_resp = client.get(reverse('core:dashboard'))
        assert dashboard_resp.status_code == 200
        assert dashboard_resp.wsgi_request.user.is_authenticated
        assert dashboard_resp.wsgi_request.user.pk == admin.pk

        # Y la clave sí quedó actualizada de verdad.
        admin.refresh_from_db()
        assert admin.check_password('claveNuevaSegura2026!')

    def test_no_afecta_sesion_al_cambiar_clave_de_otro_usuario(self):
        empresa = EmpresaFactory(configurar_usuarios_plan_pendiente=True)
        admin = UserFactory(
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            username='admin2',
            password='claveVieja123',
        )
        tecnico = UserFactory(
            empresa=empresa,
            rol_usuario='TECNICO',
            username='tecnico_original',
            password='claveViejaTec123',
        )

        client = Client()
        assert client.login(username='admin2', password='claveVieja123')

        client.post(reverse('core:configurar_usuarios_setup'), data={
            f'usuario_{admin.id}_username': 'admin2',
            f'usuario_{admin.id}_email': admin.email,
            f'usuario_{tecnico.id}_username': 'tecnico_original',
            f'usuario_{tecnico.id}_email': 'tecnico@empresa-real.com',
            f'usuario_{tecnico.id}_password': 'claveNuevaTec2026!',
        })

        # El admin (quien hizo la petición) sigue logueado con normalidad.
        dashboard_resp = client.get(reverse('core:dashboard'))
        assert dashboard_resp.status_code == 200
        assert dashboard_resp.wsgi_request.user.pk == admin.pk

        tecnico.refresh_from_db()
        assert tecnico.check_password('claveNuevaTec2026!')
