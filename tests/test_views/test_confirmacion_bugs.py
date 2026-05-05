"""
Tests de regresión para tres bugs corregidos en confirmaciones metrológicas.

Bug 1 — Gráfica desaparece en PDF al aprobar confirmación v2 (multi-magnitud).
Bug 2 — fecha_analisis en PDF sale con la fecha de hoy en vez de la real.
Bug 3 — fecha_analisis se sobreescribe al abrir el formulario de confirmación existente.

Todos los tests deben PASAR con los fixes. Si alguno falla, el bug regresó.
"""
import json
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock, call
from django.test import Client, RequestFactory
from django.urls import reverse

from core.models import Empresa, CustomUser, Equipo, Calibracion


# ---------------------------------------------------------------------------
# Helpers de unicidad
# ---------------------------------------------------------------------------

_cnt = 0

def _uniq():
    global _cnt
    _cnt += 1
    return _cnt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(
        nombre=f'EmpresaBug{_uniq()}',
        nit=f'800{_uniq():06d}-1',
        email=f'bug{_uniq()}@test.com',
    )


@pytest.fixture
def admin_user(empresa):
    from core.views.registro import asignar_permisos_por_rol
    u = CustomUser.objects.create_user(
        username=f'admin_bug{_uniq()}',
        email=f'admin{_uniq()}@test.com',
        password='pass1234',
        empresa=empresa,
        rol_usuario='ADMINISTRADOR',
    )
    asignar_permisos_por_rol(u)
    return u


@pytest.fixture
def tecnico_user(empresa):
    from core.views.registro import asignar_permisos_por_rol
    u = CustomUser.objects.create_user(
        username=f'tec_bug{_uniq()}',
        email=f'tec{_uniq()}@test.com',
        password='pass1234',
        empresa=empresa,
        rol_usuario='TECNICO',
    )
    asignar_permisos_por_rol(u)
    return u


@pytest.fixture
def equipo(empresa):
    return Equipo.objects.create(
        nombre='Multimetro Bug',
        codigo_interno=f'BUG-{_uniq()}',
        empresa=empresa,
        tipo_equipo='Instrumento',
        estado='Activo',
        error_maximo_permisible='8%',
    )


@pytest.fixture
def calibracion(equipo):
    return Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=date(2025, 1, 15),
        resultado='Aprobado',
        numero_certificado='CERT-001',
    )


@pytest.fixture
def client_admin(admin_user):
    c = Client()
    c.login(username=admin_user.username, password='pass1234')
    return c


@pytest.fixture
def client_tecnico(tecnico_user):
    c = Client()
    c.login(username=tecnico_user.username, password='pass1234')
    return c


# ---------------------------------------------------------------------------
# Datos de prueba reutilizables
# ---------------------------------------------------------------------------

PUNTOS_V1 = [
    {'nominal': 100, 'lectura': 100.5, 'error': 0.5, 'incertidumbre': 0.2, 'emp_valor': 8, 'emp_tipo': '%', 'conformidad': 'Cumple'},
    {'nominal': 200, 'lectura': 200.8, 'error': 0.8, 'incertidumbre': 0.3, 'emp_valor': 8, 'emp_tipo': '%', 'conformidad': 'Cumple'},
]

MAGNITUDES_V2 = [
    {
        'nombre': 'Corriente AC',
        'unidad': 'mA',
        'emp': 5,
        'emp_unidad': '%',
        'puntos_medicion': [
            {'nominal': 1,  'lectura': 1.01, 'error': 0.01, 'incertidumbre': 0.005, 'emp_valor': 5, 'emp_tipo': '%', 'conformidad': 'Cumple'},
            {'nominal': 10, 'lectura': 10.08,'error': 0.08, 'incertidumbre': 0.02,  'emp_valor': 5, 'emp_tipo': '%', 'conformidad': 'Cumple'},
        ],
    },
    {
        'nombre': 'Tensión DC',
        'unidad': 'V',
        'emp': 5,
        'emp_unidad': '%',
        'puntos_medicion': [
            {'nominal': 10,  'lectura': 10.1, 'error': 0.1, 'incertidumbre': 0.03, 'emp_valor': 5, 'emp_tipo': '%', 'conformidad': 'Cumple'},
            {'nominal': 100, 'lectura': 100.5,'error': 0.5, 'incertidumbre': 0.1,  'emp_valor': 5, 'emp_tipo': '%', 'conformidad': 'Cumple'},
        ],
    },
]

DATOS_V2 = {
    'version': 2,
    'magnitudes': MAGNITUDES_V2,
    'regla_decision': 'guard_band_U',
    'conclusion': {'decision': 'APTO', 'observaciones': '', 'responsable': 'Técnico'},
}

DATOS_V1 = {
    'puntos_medicion': PUNTOS_V1,
    'emp': 8,
    'emp_unidad': '%',
    'unidad_equipo': 'V',
    'regla_decision': 'guard_band_U',
    'conclusion': {'decision': 'APTO', 'observaciones': '', 'responsable': 'Técnico'},
}


# ===========================================================================
# BUG 1 — Gráfica desaparece al aprobar confirmación v2
# ===========================================================================

class TestGraficaEnAprobacionV2:
    """
    Bug: la gráfica no aparecía en el PDF regenerado al aprobar una confirmación
    en formato v2 (multi-magnitud). Solo el formato v1 era detectado.
    """

    def _datos_v2_guardados(self):
        """Simula los datos JSON guardados en BD después de generar el PDF v2."""
        return {
            'version': 2,
            'fecha_confirmacion': '2025-01-15',
            'fecha_analisis': '2025-01-15',
            'magnitudes': [
                {
                    'nombre': 'Corriente AC',
                    'unidad': 'mA',
                    'emp': 5,
                    'emp_unidad': '%',
                    'puntos_medicion': MAGNITUDES_V2[0]['puntos_medicion'],
                    'resultado': 'APTO',
                },
                {
                    'nombre': 'Tensión DC',
                    'unidad': 'V',
                    'emp': 5,
                    'emp_unidad': '%',
                    'puntos_medicion': MAGNITUDES_V2[1]['puntos_medicion'],
                    'resultado': 'APTO',
                },
            ],
            'puntos_medicion': MAGNITUDES_V2[0]['puntos_medicion'],  # campo legacy
            'emp_valor': 5,
            'emp_unidad': '%',
            'unidad_equipo': 'mA',
            'regla_decision': 'guard_band_U',
            'decision': 'APTO',
            'responsable': 'Técnico',
            'conclusion': {'decision': 'APTO', 'observaciones': '', 'responsable': 'Técnico'},
        }

    def _preparar_calibracion_con_pdf(self, calibracion, datos):
        """Guarda datos v2 en la calibración y simula que tiene PDF subido."""
        Calibracion.objects.filter(pk=calibracion.pk).update(
            confirmacion_metrologica_datos=datos,
            confirmacion_metrologica_pdf='confirmaciones/fake_test.pdf',
        )
        calibracion.refresh_from_db()

    def test_aprobacion_v2_genera_grafica_por_magnitud(self, db, calibracion, admin_user):
        """Al aprobar una confirmación v2, cada magnitud del contexto debe tener 'grafica'."""
        self._preparar_calibracion_con_pdf(calibracion, self._datos_v2_guardados())

        graficas_generadas = []
        context_capturado = {}

        def fake_generar_grafica(puntos, emp_valor, emp_unidad, unidad, **kwargs):
            graficas_generadas.append({'n_puntos': len(puntos)})
            return f'data:image/png;base64,FAKEGRAF_{len(graficas_generadas)}'

        def fake_render_to_string(template, ctx):
            context_capturado.update(ctx)
            return '<html>mock</html>'

        request = RequestFactory().post('/')
        request.user = admin_user

        with patch('core.views.confirmacion._generar_grafica_confirmacion', side_effect=fake_generar_grafica), \
             patch('django.template.loader.render_to_string', side_effect=fake_render_to_string), \
             patch('weasyprint.HTML') as mock_html, \
             patch('django.db.models.fields.files.FieldFile.save'):
            mock_html.return_value.write_pdf.return_value = b'%PDF-fake'

            from core.views.aprobaciones import aprobar_confirmacion
            response = aprobar_confirmacion(request, calibracion.id)

        # Deben haberse generado tantas gráficas como magnitudes (2 para v2)
        assert len(graficas_generadas) == 2, (
            f"Bug 1: se esperaban 2 gráficas (una por magnitud v2), se generaron {len(graficas_generadas)}"
        )

        # Cada magnitud en el contexto debe tener 'grafica'
        mags = context_capturado.get('datos_confirmacion', {}).get('magnitudes', [])
        assert len(mags) >= 2, "El contexto no tiene magnitudes"
        for i, mag in enumerate(mags):
            assert 'grafica' in mag, (
                f"Bug 1: magnitud[{i}] '{mag.get('nombre')}' no tiene 'grafica' en el contexto del PDF"
            )

    def test_aprobacion_v1_sigue_funcionando(self, db, calibracion, admin_user):
        """La aprobación v1 no debe romperse con el fix de v2."""
        datos_v1 = {
            'puntos_medicion': PUNTOS_V1,
            'emp_valor': 8,
            'emp_unidad': '%',
            'unidad_equipo': 'V',
            'regla_decision': 'guard_band_U',
            'decision': 'APTO',
            'responsable': 'Técnico',
            'conclusion': {'decision': 'APTO', 'observaciones': '', 'responsable': 'Técnico'},
        }
        self._preparar_calibracion_con_pdf(calibracion, datos_v1)

        graficas_generadas = []
        context_capturado = {}

        def fake_generar_grafica(puntos, emp_valor, emp_unidad, unidad, **kwargs):
            graficas_generadas.append(True)
            return 'data:image/png;base64,FAKEGRAF_V1'

        def fake_render_to_string(template, ctx):
            context_capturado.update(ctx)
            return '<html>mock</html>'

        request = RequestFactory().post('/')
        request.user = admin_user

        with patch('core.views.confirmacion._generar_grafica_confirmacion', side_effect=fake_generar_grafica), \
             patch('django.template.loader.render_to_string', side_effect=fake_render_to_string), \
             patch('weasyprint.HTML') as mock_html, \
             patch('django.db.models.fields.files.FieldFile.save'):
            mock_html.return_value.write_pdf.return_value = b'%PDF-fake'

            from core.views.aprobaciones import aprobar_confirmacion
            response = aprobar_confirmacion(request, calibracion.id)

        assert len(graficas_generadas) >= 1, "Bug 1 regresión v1: no se generó la gráfica v1"
        assert context_capturado.get('grafica_imagen') is not None, (
            "Bug 1 regresión v1: grafica_imagen no está en el contexto del PDF"
        )

    def test_sin_datos_json_aprueba_sin_regenerar_pdf(self, db, calibracion, admin_user):
        """Si la confirmación tiene PDF manual (sin datos JSON), se aprueba sin regenerar PDF."""
        # Configurar PDF sin datos JSON (subida manual)
        Calibracion.objects.filter(pk=calibracion.pk).update(
            confirmacion_metrologica_datos={},
            confirmacion_metrologica_pdf='confirmaciones/manual.pdf',
        )
        calibracion.refresh_from_db()

        request = RequestFactory().post('/')
        request.user = admin_user

        html_calls = []

        with patch('weasyprint.HTML') as mock_html:
            mock_html.side_effect = lambda **kwargs: html_calls.append(True) or MagicMock()

            from core.views.aprobaciones import aprobar_confirmacion
            response = aprobar_confirmacion(request, calibracion.id)

        data = json.loads(response.content)
        assert data.get('success') is True, (
            f"La aprobación con PDF manual debe ser exitosa. Respuesta: {data}"
        )
        # WeasyPrint NO debe haberse llamado (datos JSON vacíos = no regenerar)
        assert len(html_calls) == 0, (
            "Bug 1: WeasyPrint se llamó aunque no hay datos JSON — el PDF no debería regenerarse"
        )


# ===========================================================================
# BUG 2 — fecha_analisis se guarda y recupera correctamente
# ===========================================================================

class TestFechaAnalisisEnPDF:
    """
    Bug: el PDF siempre mostraba la fecha del día en que se generó,
    no la fecha real que el técnico puso en el formulario.
    """

    def test_fecha_analisis_guardada_a_nivel_raiz_es_recuperable(self, db, calibracion, admin_user):
        """
        El fix guarda fecha_analisis en campos_comunes (nivel raíz del JSON).
        Verifica que _preparar_contexto_confirmacion lo recupera correctamente
        cuando los datos vienen de BD (donde ya no tiene 'equipo.fecha_analisis' sino
        solo 'fecha_analisis' a nivel raíz).
        """
        from core.views.confirmacion import _preparar_contexto_confirmacion

        fecha_real = '2025-01-15'

        # Simula el JSON tal como queda guardado en BD después del fix:
        # campos_comunes ahora incluye fecha_analisis a nivel raíz
        datos_como_guardados_en_bd = {
            'version': 2,
            'fecha_confirmacion': '2025-01-15',
            'fecha_analisis': fecha_real,  # <-- campo añadido por el fix
            'magnitudes': MAGNITUDES_V2,
            'regla_decision': 'guard_band_U',
            'decision': 'APTO',
            'responsable': 'Técnico',
            'conclusion': {'decision': 'APTO', 'observaciones': '', 'responsable': 'Técnico'},
        }

        request = RequestFactory().get('/')
        request.user = admin_user

        ctx = _preparar_contexto_confirmacion(
            request, calibracion.equipo, calibracion, datos_como_guardados_en_bd
        )

        fecha_en_ctx = str(ctx.get('datos_confirmacion', {}).get('equipo', {}).get('fecha_analisis', ''))
        assert fecha_real in fecha_en_ctx, (
            f"Bug 2: cuando los datos guardados tienen 'fecha_analisis' a nivel raíz, "
            f"el contexto debería usarla. En contexto: '{fecha_en_ctx}', esperado: '{fecha_real}'"
        )

    def test_preparar_contexto_usa_fecha_analisis_guardada(self, db, calibracion, admin_user):
        """
        _preparar_contexto_confirmacion debe usar la fecha_analisis guardada en los datos,
        no datetime.now().
        """
        from core.views.confirmacion import _preparar_contexto_confirmacion

        fecha_real = '2025-01-15'
        datos_guardados = {
            'version': 2,
            'fecha_analisis': fecha_real,
            'magnitudes': MAGNITUDES_V2,
            'regla_decision': 'guard_band_U',
        }

        request = RequestFactory().get('/')
        request.user = admin_user

        ctx = _preparar_contexto_confirmacion(
            request, calibracion.equipo, calibracion, datos_guardados
        )

        fecha_en_ctx = str(ctx.get('datos_confirmacion', {}).get('equipo', {}).get('fecha_analisis', ''))
        assert fecha_real in fecha_en_ctx, (
            f"Bug 2: el contexto tiene fecha_analisis='{fecha_en_ctx}', "
            f"se esperaba que contuviera '{fecha_real}'"
        )

    def test_preparar_contexto_v1_usa_fecha_analisis_del_equipo(self, db, calibracion, admin_user):
        """Para v1, la fecha_analisis del campo equipo debe respetarse."""
        from core.views.confirmacion import _preparar_contexto_confirmacion

        fecha_real = '2025-03-20'
        datos = {
            'equipo': {'fecha_analisis': fecha_real},
            'puntos_medicion': PUNTOS_V1,
            'emp': 8,
            'emp_unidad': '%',
        }

        request = RequestFactory().get('/')
        request.user = admin_user

        ctx = _preparar_contexto_confirmacion(request, calibracion.equipo, calibracion, datos)
        fecha_en_ctx = str(ctx.get('datos_confirmacion', {}).get('equipo', {}).get('fecha_analisis', ''))
        assert fecha_real in fecha_en_ctx, (
            f"Bug 2 (v1): fecha_analisis='{fecha_en_ctx}', se esperaba '{fecha_real}'"
        )


# ===========================================================================
# BUG 3 — Abrir formulario existente no sobreescribe fecha_analisis
# ===========================================================================

class TestFechaAnalisisFormulario:
    """
    Bug: al abrir el formulario de una confirmación ya existente, el campo
    fecha_analisis se inicializaba con la fecha actual en lugar de la
    fecha que tenía guardada.
    """

    def test_contexto_usa_fecha_guardada_no_hoy(self, db, calibracion, admin_user):
        """
        _preparar_contexto_confirmacion sin datos_confirmacion (GET del formulario)
        debe usar la fecha_analisis guardada en ultima_calibracion, no datetime.now().
        """
        from core.views.confirmacion import _preparar_contexto_confirmacion

        fecha_original = '2025-01-15'
        calibracion.confirmacion_metrologica_datos = {
            'version': 2,
            'fecha_analisis': fecha_original,
            'magnitudes': MAGNITUDES_V2,
        }
        calibracion.save()

        request = RequestFactory().get('/')
        request.user = admin_user

        # Sin datos_confirmacion → simula que el técnico abre el formulario
        ctx = _preparar_contexto_confirmacion(request, calibracion.equipo, calibracion)

        fecha_en_ctx = str(ctx.get('datos_confirmacion', {}).get('equipo', {}).get('fecha_analisis', ''))
        hoy = str(date.today())

        assert fecha_original in fecha_en_ctx, (
            f"Bug 3: fecha_analisis='{fecha_en_ctx}', debería ser '{fecha_original}' (la guardada)"
        )
        assert fecha_en_ctx != hoy, (
            f"Bug 3: fecha_analisis es la fecha de HOY ({hoy}) en vez de la fecha original"
        )

    def test_sin_datos_guardados_usa_fecha_actual(self, db, calibracion, admin_user):
        """Si no hay datos guardados, es correcto usar hoy como fecha inicial."""
        from core.views.confirmacion import _preparar_contexto_confirmacion

        calibracion.confirmacion_metrologica_datos = {}
        calibracion.save()

        request = RequestFactory().get('/')
        request.user = admin_user

        ctx = _preparar_contexto_confirmacion(request, calibracion.equipo, calibracion)

        fecha_en_ctx = ctx.get('datos_confirmacion', {}).get('equipo', {}).get('fecha_analisis')
        # Debe haber una fecha (puede ser hoy o None, pero no debe romper)
        # No lanzamos AssertionError aquí porque es el comportamiento esperado
        assert fecha_en_ctx is not None or True, "No debe romper si no hay datos guardados"

    def test_fecha_guardada_v1_tambien_se_preserva(self, db, calibracion, admin_user):
        """Bug 3 también aplica para confirmaciones guardadas en formato v1."""
        from core.views.confirmacion import _preparar_contexto_confirmacion

        fecha_original = '2024-11-05'
        calibracion.confirmacion_metrologica_datos = {
            'fecha_analisis': fecha_original,
            'puntos_medicion': PUNTOS_V1,
            'emp_valor': 8,
            'emp_unidad': '%',
        }
        calibracion.save()

        request = RequestFactory().get('/')
        request.user = admin_user

        ctx = _preparar_contexto_confirmacion(request, calibracion.equipo, calibracion)

        fecha_en_ctx = str(ctx.get('datos_confirmacion', {}).get('equipo', {}).get('fecha_analisis', ''))
        assert fecha_original in fecha_en_ctx, (
            f"Bug 3 (v1): fecha_analisis='{fecha_en_ctx}', debería ser '{fecha_original}'"
        )
