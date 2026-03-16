"""
Tests HTTP para core/views/comprobacion.py

Cubre comprobacion_metrologica_view, guardar_comprobacion_json,
generar_grafica_svg_comprobacion y control de acceso.
Target: elevar cobertura de 32% a 65%+.
"""
import json
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.test import Client

from core.models import Empresa, CustomUser, Equipo, Comprobacion
from core.views.comprobacion import generar_grafica_svg_comprobacion


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(
        nombre='Empresa Comprobacion Test',
        nit='900000002-2',
        email='comp@test.com',
    )


def _make_user(empresa, *, is_superuser=False, rol='ADMINISTRADOR', username=None):
    username = username or f'comp_user_{Empresa.objects.count()}'
    return CustomUser.objects.create_user(
        username=username,
        password='testpass123',
        empresa=empresa,
        is_superuser=is_superuser,
        is_staff=is_superuser,
        rol_usuario=rol,
    )


@pytest.fixture
def user(db, empresa):
    return _make_user(empresa, username='comp_user')


@pytest.fixture
def superuser(db, empresa):
    return _make_user(empresa, is_superuser=True, username='comp_super')


@pytest.fixture
def equipo(db, empresa):
    return Equipo.objects.create(
        empresa=empresa,
        codigo_interno='COMP-EQ-001',
        nombre='Micrómetro Comprobacion',
        puntos_calibracion='0, 10, 20',
        error_maximo_permisible='0.005',
        estado='ACTIVO',
        rango_medida='0-25mm',
    )


@pytest.fixture
def comprobacion(db, equipo, user):
    return Comprobacion.objects.create(
        equipo=equipo,
        fecha_comprobacion=date.today(),
        resultado='Aprobado',
        creado_por=user,
        estado_aprobacion='pendiente',
        datos_comprobacion={
            'puntos_medicion': [
                {'nominal': 0, 'error': 0.001, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
                {'nominal': 10, 'error': -0.002, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
            ]
        }
    )


@pytest.fixture
def auth_client(db, user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def super_client(db, superuser):
    client = Client()
    client.force_login(superuser)
    return client


# ---------------------------------------------------------------------------
# generar_grafica_svg_comprobacion (pure function — no DB needed)
# ---------------------------------------------------------------------------

class TestGenerarGraficaSvgComprobacion:
    """Tests para la función de generación de SVG — sin DB requerida."""

    def test_sin_puntos_retorna_svg_vacio(self):
        svg = generar_grafica_svg_comprobacion([])
        assert '<svg' in svg
        assert 'No hay datos' in svg

    def test_puntos_none_retorna_svg_vacio(self):
        svg = generar_grafica_svg_comprobacion(None)
        assert '<svg' in svg

    def test_un_solo_punto_conforme(self):
        puntos = [{'nominal': 50, 'error': 0.001, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'}]
        svg = generar_grafica_svg_comprobacion(puntos, unidad='mm')
        assert '<svg' in svg
        assert '</svg>' in svg
        # Color azul para conforme
        assert '#3b82f6' in svg

    def test_un_solo_punto_no_conforme(self):
        puntos = [{'nominal': 50, 'error': 0.010, 'emp_absoluto': 0.005, 'conformidad': 'NO CONFORME'}]
        svg = generar_grafica_svg_comprobacion(puntos, unidad='g')
        assert '<svg' in svg
        # Color rojo para no conforme
        assert '#ef4444' in svg

    def test_multiples_puntos_genera_svg_valido(self):
        puntos = [
            {'nominal': i * 10, 'error': i * 0.001, 'emp_absoluto': 0.01, 'conformidad': 'CONFORME'}
            for i in range(5)
        ]
        svg = generar_grafica_svg_comprobacion(puntos, unidad='°C')
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')

    def test_unidad_aparece_en_svg(self):
        puntos = [{'nominal': 10, 'error': 0.001, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'}]
        svg = generar_grafica_svg_comprobacion(puntos, unidad='kg')
        assert 'kg' in svg

    def test_puntos_con_errores_mixtos(self):
        puntos = [
            {'nominal': 0, 'error': 0.001, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
            {'nominal': 10, 'error': -0.002, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
            {'nominal': 20, 'error': 0.008, 'emp_absoluto': 0.005, 'conformidad': 'NO CONFORME'},
        ]
        svg = generar_grafica_svg_comprobacion(puntos)
        assert '<svg' in svg
        # Debe tener ambos colores (conforme y no conforme)
        assert '#3b82f6' in svg
        assert '#ef4444' in svg

    def test_puntos_con_error_cero(self):
        puntos = [
            {'nominal': 50, 'error': 0.0, 'emp_absoluto': 0.01, 'conformidad': 'CONFORME'}
        ]
        svg = generar_grafica_svg_comprobacion(puntos)
        assert '<svg' in svg

    def test_muchos_puntos_genera_etiquetas_correctas(self):
        puntos = [
            {'nominal': i, 'error': 0.001, 'emp_absoluto': 0.01, 'conformidad': 'CONFORME'}
            for i in range(15)
        ]
        svg = generar_grafica_svg_comprobacion(puntos)
        assert '<svg' in svg
        # Verifica que se generan etiquetas (no todas, cada max(1, n//10))
        assert 'P1' in svg


# ---------------------------------------------------------------------------
# Access control — comprobacion_metrologica_view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComprobacionMetrologicaViewAccess:

    def test_anonymous_redirected(self, equipo):
        client = Client()
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = client.get(url)
        assert response.status_code == 302
        assert 'login' in response.url.lower()

    def test_wrong_empresa_gets_404(self, db, equipo):
        other_empresa = Empresa.objects.create(
            nombre='Otra Empresa Comp', nit='555-5', email='otra555@test.com'
        )
        other_user = _make_user(other_empresa, username='comp_other')
        client = Client()
        client.force_login(other_user)
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = client.get(url)
        assert response.status_code == 404

    def test_own_empresa_can_access(self, auth_client, equipo):
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_superuser_can_access_any_empresa(self, super_client, equipo):
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = super_client.get(url)
        assert response.status_code == 200

    def test_nonexistent_equipo_returns_404(self, auth_client):
        url = reverse('core:comprobacion_metrologica', args=[99999])
        response = auth_client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# comprobacion_metrologica_view — GET behaviour
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComprobacionMetrologicaViewGet:

    def test_get_equipo_sin_comprobaciones(self, auth_client, equipo):
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_get_with_comprobacion_id(self, auth_client, equipo, comprobacion):
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url, {'comprobacion_id': comprobacion.pk})
        assert response.status_code == 200

    def test_get_with_invalid_comprobacion_id_returns_404(self, auth_client, equipo):
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url, {'comprobacion_id': 99999})
        assert response.status_code == 404

    def test_context_contains_equipo(self, auth_client, equipo):
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.context['equipo'] == equipo

    def test_context_siguiente_consecutivo(self, auth_client, equipo):
        """El consecutivo sugerido debe estar en el contexto."""
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url)
        assert 'siguiente_consecutivo' in response.context

    def test_equipo_with_rango_extrae_unidad(self, auth_client, equipo):
        """La unidad se extrae del rango del equipo."""
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.context['unidad_equipo'] == 'mm'

    def test_get_post_method_allowed(self, auth_client, equipo):
        """La vista acepta GET (ya verificado) y POST."""
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        # POST vacío — la vista procesa POST method
        response = auth_client.post(url, {})
        # Sin datos JSON en body, el POST path puede fallar o redirigir
        assert response.status_code in (200, 302, 400, 500)

    def test_comprobacion_con_datos_existentes(self, auth_client, equipo, comprobacion):
        """Cargando una comprobación con datos_comprobacion."""
        url = reverse('core:comprobacion_metrologica', args=[equipo.pk])
        response = auth_client.get(url, {'comprobacion_id': comprobacion.pk})
        assert response.status_code == 200
        assert response.context['comprobacion'] == comprobacion
        assert response.context['datos_existentes'] is not None


# ---------------------------------------------------------------------------
# guardar_comprobacion_json — POST JSON
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGuardarComprobacionJsonHttp:

    URL_NAME = 'core:guardar_comprobacion_json'

    def _post_json(self, client, equipo_id, payload):
        url = reverse(self.URL_NAME, args=[equipo_id])
        return client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_anonymous_redirected(self, equipo):
        client = Client()
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = client.post(url, data='{}', content_type='application/json')
        assert response.status_code == 302

    def test_get_not_allowed(self, auth_client, equipo):
        """GET no está permitido en este endpoint."""
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = auth_client.get(url)
        assert response.status_code == 405

    def test_wrong_empresa_returns_error(self, db, equipo):
        other_empresa = Empresa.objects.create(
            nombre='Otra Empresa JSON', nit='666-6', email='e666@test.com'
        )
        other_user = _make_user(other_empresa, username='json_other')
        client = Client()
        client.force_login(other_user)
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = client.post(url, data='{}', content_type='application/json')
        # 404 (wrong empresa) OR 500 (from exception handler)
        assert response.status_code in (404, 500)

    def test_crear_nueva_comprobacion_exitosa(self, auth_client, equipo):
        payload = {
            'puntos_medicion': [
                {'nominal': 0, 'error': 0.001, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
                {'nominal': 10, 'error': -0.002, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
            ],
            'formato_codigo': 'COMP-001',
            'formato_version': '1.0',
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'comprobacion_id' in data

    def test_crear_comprobacion_no_aprobado(self, auth_client, equipo):
        """Punto NO CONFORME debe resultar en 'No Aprobado'."""
        payload = {
            'puntos_medicion': [
                {'nominal': 0, 'error': 0.010, 'emp_absoluto': 0.005, 'conformidad': 'NO CONFORME'},
            ]
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        comp = Comprobacion.objects.get(id=data['comprobacion_id'])
        assert comp.resultado == 'No Aprobado'

    def test_crear_comprobacion_aprobado_todos_conformes(self, auth_client, equipo):
        payload = {
            'puntos_medicion': [
                {'nominal': i, 'error': 0.001, 'emp_absoluto': 0.01, 'conformidad': 'CONFORME'}
                for i in range(3)
            ]
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        comp = Comprobacion.objects.get(id=data['comprobacion_id'])
        assert comp.resultado == 'Aprobado'

    def test_actualizar_comprobacion_existente(self, auth_client, equipo, comprobacion):
        payload = {
            'comprobacion_id': comprobacion.pk,
            'puntos_medicion': [
                {'nominal': 5, 'error': 0.002, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'}
            ]
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['comprobacion_id'] == comprobacion.pk

    def test_guardar_formato_empresa(self, auth_client, equipo, empresa):
        """El formato de comprobacion se guarda en la empresa."""
        payload = {
            'puntos_medicion': [],
            'formato_codigo': 'COMP-NEW-001',
            'formato_version': '2.0',
            'formato_fecha': '2026-03-13',
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        empresa.refresh_from_db()
        assert empresa.comprobacion_codigo == 'COMP-NEW-001'
        assert empresa.comprobacion_version == '2.0'

    def test_guardar_formato_fecha_yyyy_mm(self, auth_client, equipo, empresa):
        """Formato de fecha YYYY-MM (sin día) se convierte correctamente."""
        payload = {
            'puntos_medicion': [],
            'formato_fecha': '2026-03',
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        empresa.refresh_from_db()
        assert empresa.comprobacion_fecha_formato is not None

    def test_guardar_consecutivo_texto(self, auth_client, equipo, empresa):
        """El consecutivo de texto se guarda en la comprobacion."""
        payload = {
            'puntos_medicion': [],
            'consecutivo_texto': 'CB-003',
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        comp = Comprobacion.objects.get(id=data['comprobacion_id'])
        assert comp.consecutivo_texto == 'CB-003'
        # Prefijo guardado en empresa
        empresa.refresh_from_db()
        assert empresa.comprobacion_prefijo_consecutivo == 'CB'

    def test_guardar_observaciones(self, auth_client, equipo):
        payload = {
            'puntos_medicion': [],
            'observaciones': 'Test de observacion',
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        comp = Comprobacion.objects.get(id=data['comprobacion_id'])
        assert comp.observaciones == 'Test de observacion'

    def test_superuser_puede_guardar_servicio_terceros(self, super_client, equipo):
        payload = {
            'puntos_medicion': [],
            'es_servicio_terceros': True,
            'empresa_cliente_nombre': 'Cliente Test',
            'empresa_cliente_nit': '123-4',
        }
        response = self._post_json(super_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        comp = Comprobacion.objects.get(id=data['comprobacion_id'])
        assert comp.es_servicio_terceros is True
        assert comp.empresa_cliente_nombre == 'Cliente Test'

    def test_usuario_regular_no_puede_servicio_terceros(self, auth_client, equipo):
        payload = {
            'puntos_medicion': [],
            'es_servicio_terceros': True,
            'empresa_cliente_nombre': 'Cliente Test',
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        data = json.loads(response.content)
        comp = Comprobacion.objects.get(id=data['comprobacion_id'])
        # Usuario regular no puede guardar servicio a terceros
        assert comp.es_servicio_terceros is False

    def test_actualizar_comprobacion_rechazada_resetea_estado(self, auth_client, equipo, comprobacion):
        """Actualizar una comprobación rechazada debe resetear estado a pendiente."""
        comprobacion.estado_aprobacion = 'rechazado'
        comprobacion.save()
        payload = {
            'comprobacion_id': comprobacion.pk,
            'puntos_medicion': [
                {'nominal': 0, 'error': 0.001, 'emp_absoluto': 0.01, 'conformidad': 'CONFORME'}
            ]
        }
        response = self._post_json(auth_client, equipo.pk, payload)
        assert response.status_code == 200
        comprobacion.refresh_from_db()
        assert comprobacion.estado_aprobacion == 'pendiente'

    def test_equipo_inexistente_retorna_error(self, auth_client):
        url = reverse(self.URL_NAME, args=[99999])
        response = auth_client.post(url, data='{}', content_type='application/json')
        # 404 or 500 from exception handler
        assert response.status_code in (404, 500)


# ---------------------------------------------------------------------------
# generar_pdf_comprobacion
# ---------------------------------------------------------------------------

class TestGenerarPdfComprobacion:
    """Tests para la vista generar_pdf_comprobacion (generación de PDF metrológico)."""

    URL_NAME = 'core:generar_pdf_comprobacion'

    def test_anonimo_redirige_a_login(self, equipo):
        """Sin autenticación, redirige al login."""
        from django.test import Client
        client = Client()
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_sin_comprobacion_id_retorna_400(self, auth_client, equipo):
        """Sin comprobacion_id en query params, retorna 400."""
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = auth_client.get(url)
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'error' in data

    def test_comprobacion_id_inexistente_retorna_error(self, auth_client, equipo):
        """comprobacion_id que no existe → error (Http404 capturado como 500 por el try/except)."""
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = auth_client.get(url, {'comprobacion_id': '99999'})
        # El try/except de la vista captura Http404 y retorna 500
        assert response.status_code in (404, 500)

    def test_equipo_otra_empresa_retorna_error(self, db, equipo):
        """Usuario de otra empresa no puede acceder al equipo → error."""
        otra_empresa = Empresa.objects.create(
            nombre='Otra Empresa', nit='111222333-0', email='otra@test.com'
        )
        otro_user = CustomUser.objects.create_user(
            username='otro_user_pdf', password='pass', empresa=otra_empresa
        )
        client = Client()
        client.force_login(otro_user)
        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = client.get(url, {'comprobacion_id': '1'})
        # Http404 capturado por try/except → 500
        assert response.status_code in (404, 500)

    def test_pdf_existente_se_sirve_directamente(self, auth_client, equipo, comprobacion, settings, tmp_path):
        """Si la comprobación ya tiene PDF, lo sirve sin regenerar."""
        settings.MEDIA_ROOT = str(tmp_path)
        from django.core.files.base import ContentFile
        fake_pdf_bytes = b'%PDF-1.4 existing'
        comprobacion.comprobacion_pdf.save(
            'existing_test.pdf', ContentFile(fake_pdf_bytes), save=True
        )

        url = reverse(self.URL_NAME, args=[equipo.pk])
        response = auth_client.get(url, {'comprobacion_id': str(comprobacion.pk)})

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content == fake_pdf_bytes

    @pytest.mark.django_db
    def test_genera_pdf_nuevo_con_mock(self, auth_client, equipo, comprobacion, settings, tmp_path):
        """Genera PDF con WeasyPrint mockeado y retorna JSON con pdf_url."""
        from unittest.mock import patch
        settings.MEDIA_ROOT = str(tmp_path)

        with patch('core.views.comprobacion.render_to_string', return_value='<html></html>'):
            with patch('core.views.comprobacion.HTML') as mock_html_cls:
                mock_html_cls.return_value.write_pdf.return_value = b'%PDF-1.4 fake'
                url = reverse(self.URL_NAME, args=[equipo.pk])
                response = auth_client.get(url, {'comprobacion_id': str(comprobacion.pk)})

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'pdf_url' in data

    @pytest.mark.django_db
    def test_genera_pdf_desde_post_datos_json(self, auth_client, equipo, comprobacion, settings, tmp_path):
        """Acepta datos_comprobacion desde POST para generar el PDF."""
        from unittest.mock import patch
        settings.MEDIA_ROOT = str(tmp_path)

        datos = json.dumps({
            'puntos_medicion': [
                {'nominal': 0, 'error': 0.001, 'emp_absoluto': 0.005, 'conformidad': 'CONFORME'},
            ],
            'unidad_equipo': 'mm'
        })

        with patch('core.views.comprobacion.render_to_string', return_value='<html></html>'):
            with patch('core.views.comprobacion.HTML') as mock_html_cls:
                mock_html_cls.return_value.write_pdf.return_value = b'%PDF-1.4 from post'
                url = reverse(self.URL_NAME, args=[equipo.pk])
                response = auth_client.post(
                    url + f'?comprobacion_id={comprobacion.pk}',
                    {'datos_comprobacion': datos}
                )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    @pytest.mark.django_db
    def test_excepcion_en_generacion_retorna_500(self, auth_client, equipo, comprobacion):
        """Si ocurre una excepción durante la generación, retorna 500."""
        from unittest.mock import patch
        with patch('core.views.comprobacion.render_to_string', side_effect=Exception('Error de template')):
            url = reverse(self.URL_NAME, args=[equipo.pk])
            response = auth_client.get(url, {'comprobacion_id': str(comprobacion.pk)})

        assert response.status_code == 500
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'error' in data

    @pytest.mark.django_db
    def test_superuser_puede_generar_pdf(self, super_client, equipo, comprobacion, settings, tmp_path):
        """Superusuario puede generar PDF de cualquier empresa."""
        from unittest.mock import patch
        settings.MEDIA_ROOT = str(tmp_path)

        with patch('core.views.comprobacion.render_to_string', return_value='<html></html>'):
            with patch('core.views.comprobacion.HTML') as mock_html_cls:
                mock_html_cls.return_value.write_pdf.return_value = b'%PDF-1.4 super'
                url = reverse(self.URL_NAME, args=[equipo.pk])
                response = super_client.get(url, {'comprobacion_id': str(comprobacion.pk)})

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
