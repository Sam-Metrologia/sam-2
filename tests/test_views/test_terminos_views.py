"""
Tests HTTP para core/views/terminos.py

Cubre: get_client_ip, aceptar_terminos, rechazar_terminos,
       ver_terminos_pdf, mi_aceptacion_terminos.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from django.test import Client, RequestFactory
from django.urls import reverse

from core.models import Empresa, CustomUser, TerminosYCondiciones, AceptacionTerminos
from core.views.terminos import get_client_ip


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(
        nombre='Empresa Terminos Test',
        nit='900999001-1',
        email='terminos@test.com',
    )


@pytest.fixture
def user(db, empresa):
    return CustomUser.objects.create_user(
        username='terminos_user',
        password='testpass123',
        empresa=empresa,
    )


@pytest.fixture
def terminos(db):
    return TerminosYCondiciones.objects.create(
        version='1.0',
        fecha_vigencia=date.today(),
        titulo='Contrato SAM Test',
        activo=True,
    )


@pytest.fixture
def auth_client(db, user):
    client = Client()
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# get_client_ip — función helper pura
# ---------------------------------------------------------------------------

class TestGetClientIp:

    def test_uses_remote_addr_when_no_forwarded(self):
        factory = RequestFactory()
        request = factory.get('/', REMOTE_ADDR='10.0.0.1')
        assert get_client_ip(request) == '10.0.0.1'

    def test_uses_first_ip_from_x_forwarded_for(self):
        factory = RequestFactory()
        request = factory.get(
            '/',
            HTTP_X_FORWARDED_FOR='203.0.113.1, 10.0.0.2, 172.16.0.1',
            REMOTE_ADDR='10.0.0.2',
        )
        assert get_client_ip(request) == '203.0.113.1'

    def test_uses_single_ip_from_x_forwarded_for(self):
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.5')
        assert get_client_ip(request) == '192.168.1.5'


# ---------------------------------------------------------------------------
# aceptar_terminos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAceptarTerminos:

    URL = 'core:aceptar_terminos'

    def test_anonymous_redirected_to_login(self):
        client = Client()
        response = client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'login' in response.url.lower()

    def test_get_no_terminos_activos_redirects_dashboard(self, auth_client):
        # No TerminosYCondiciones creados → redirige a dashboard
        response = auth_client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'dashboard' in response.url

    def test_get_with_active_terminos_renders_form(self, auth_client, terminos):
        response = auth_client.get(reverse(self.URL))
        assert response.status_code == 200

    def test_get_already_accepted_redirects_dashboard(self, db, user, terminos):
        # Crear aceptación previa
        AceptacionTerminos.objects.create(
            usuario=user,
            terminos=terminos,
            empresa=user.empresa,
            ip_address='127.0.0.1',
            aceptado=True,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'dashboard' in response.url

    def test_post_without_checkbox_stays_on_page(self, auth_client, terminos):
        response = auth_client.post(reverse(self.URL), {})
        assert response.status_code == 200

    def test_post_with_checkbox_creates_aceptacion_and_redirects(self, auth_client, user, terminos):
        assert not AceptacionTerminos.objects.filter(usuario=user).exists()
        response = auth_client.post(reverse(self.URL), {'acepta_terminos': 'on'})
        assert response.status_code == 302
        assert 'dashboard' in response.url
        assert AceptacionTerminos.objects.filter(usuario=user, terminos=terminos).exists()

    def test_post_crear_aceptacion_returns_none_shows_error(self, auth_client, terminos):
        """Si crear_aceptacion retorna None, se muestra error y se re-renderiza el form."""
        with patch('core.views.terminos.AceptacionTerminos.crear_aceptacion', return_value=None):
            response = auth_client.post(reverse(self.URL), {'acepta_terminos': 'on'})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# rechazar_terminos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRechazarTerminos:

    URL = 'core:rechazar_terminos'

    def test_anonymous_redirected(self):
        client = Client()
        response = client.post(reverse(self.URL))
        assert response.status_code == 302

    def test_get_redirects_to_aceptar_terminos(self, auth_client):
        response = auth_client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'aceptar_terminos' in response.url or 'terminos' in response.url

    def test_post_logs_out_and_redirects_to_login(self, db, user):
        client = Client()
        client.force_login(user)
        response = client.post(reverse(self.URL))
        assert response.status_code == 302
        assert 'login' in response.url.lower()
        # Usuario ya no está autenticado
        response2 = client.get(reverse('core:dashboard'))
        assert response2.status_code == 302
        assert 'login' in response2.url.lower()


# ---------------------------------------------------------------------------
# ver_terminos_pdf
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVerTerminosPdf:

    URL = 'core:ver_terminos_pdf'

    def test_anonymous_redirected(self):
        client = Client()
        response = client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'login' in response.url.lower()

    def test_no_terminos_returns_404_text(self, auth_client):
        response = auth_client.get(reverse(self.URL))
        assert response.status_code == 404

    def test_terminos_without_pdf_returns_404(self, auth_client, terminos):
        # terminos sin archivo_pdf (es None/blank)
        assert not terminos.archivo_pdf
        response = auth_client.get(reverse(self.URL))
        assert response.status_code == 404

    def test_terminos_with_pdf_returns_pdf_response(self, auth_client, terminos):
        mock_pdf = MagicMock()
        mock_pdf.read.return_value = b'%PDF-1.4 fake content'
        terminos.archivo_pdf = mock_pdf
        with patch.object(
            TerminosYCondiciones, 'get_terminos_activos', return_value=terminos
        ):
            response = auth_client.get(reverse(self.URL))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert 'inline' in response['Content-Disposition']
        assert f'v{terminos.version}' in response['Content-Disposition']


# ---------------------------------------------------------------------------
# mi_aceptacion_terminos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMiAceptacionTerminos:

    URL = 'core:mi_aceptacion_terminos'

    def test_anonymous_redirected(self):
        client = Client()
        response = client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'login' in response.url.lower()

    def test_no_aceptacion_redirects_to_aceptar(self, auth_client, terminos):
        response = auth_client.get(reverse(self.URL))
        assert response.status_code == 302
        assert 'aceptar_terminos' in response.url or 'terminos' in response.url

    def test_with_aceptacion_renders_200(self, db, user, terminos):
        AceptacionTerminos.objects.create(
            usuario=user,
            terminos=terminos,
            empresa=user.empresa,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0',
            aceptado=True,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse(self.URL))
        assert response.status_code == 200

    def test_context_contains_aceptacion(self, db, user, terminos):
        AceptacionTerminos.objects.create(
            usuario=user,
            terminos=terminos,
            empresa=user.empresa,
            ip_address='10.0.0.1',
            aceptado=True,
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse(self.URL))
        assert response.status_code == 200
        assert 'mi_aceptacion' in response.context
        assert response.context['mi_aceptacion'].usuario == user

    def test_sin_aceptacion_redirige_via_vista_directa(self, db, user, terminos):
        """Línea 153: la vista redirige cuando no hay aceptación (bypasea middleware con RequestFactory)."""
        from django.test import RequestFactory
        from core.views.terminos import mi_aceptacion_terminos

        factory = RequestFactory()
        request = factory.get('/core/mi-aceptacion-terminos/')
        request.user = user  # sin AceptacionTerminos para terminos activos

        response = mi_aceptacion_terminos(request)

        # La vista redirige (línea 153) — la URL exacta depende del patrón de terminos
        assert response.status_code == 302
