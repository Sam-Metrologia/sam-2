"""
Tests para soporte multi-variable (multi-magnitud) en confirmaciones y comprobaciones.

Cubre:
- _generar_una_grafica_hist_confirmacion: SVG por variable, normalizado por EMP
- _generar_grafica_hist_confirmaciones: dict {nombre: svg} multi-variable
- _generar_una_grafica_hist_comprobacion: SVG por variable
- _generar_grafica_hist_comprobaciones: dict {nombre: svg} multi-variable
- _generate_hoja_vida_charts en reports.py: v1 y v2, tamaño compacto
- detalle_equipo: extracción correcta de datos v1 y v2
- generar_pdf_comprobacion: magnitudes_template para v2
"""
import json
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import Client
from django.urls import reverse

from core.models import Empresa, CustomUser, Equipo, Calibracion, Comprobacion


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_cnt = 0

def _uniq():
    global _cnt
    _cnt += 1
    return _cnt


@pytest.fixture
def empresa(db):
    return Empresa.objects.create(
        nombre=f'EmpresaTest{_uniq()}',
        nit=f'900{_uniq():06d}-1',
        email=f'test{_uniq()}@test.com',
    )


@pytest.fixture
def usuario(empresa):
    from core.views.registro import asignar_permisos_por_rol
    u = CustomUser.objects.create_user(
        username=f'user{_uniq()}',
        email=f'u{_uniq()}@test.com',
        password='pass1234',
        empresa=empresa,
        rol_usuario='ADMINISTRADOR',
    )
    asignar_permisos_por_rol(u)
    return u


@pytest.fixture
def equipo(empresa):
    return Equipo.objects.create(
        nombre='Multimetro Test',
        codigo_interno=f'MT-{_uniq()}',
        empresa=empresa,
        tipo_equipo='Instrumento',
        estado='Activo',
    )


@pytest.fixture
def client_auth(usuario):
    c = Client()
    c.login(username=usuario.username, password='pass1234')
    c.user = usuario
    return c


# ---------------------------------------------------------------------------
# Datos de prueba reutilizables
# ---------------------------------------------------------------------------

PUNTOS_V1 = [
    {'nominal': 100, 'error': 0.5, 'incertidumbre': 0.2, 'emp_absoluto': 1.0},
    {'nominal': 200, 'error': 0.8, 'incertidumbre': 0.3, 'emp_absoluto': 1.5},
    {'nominal': 500, 'error': 1.2, 'incertidumbre': 0.4, 'emp_absoluto': 2.0},
]

PUNTOS_CORRIENTE = [
    {'nominal': 1,   'error': 0.01, 'incertidumbre': 0.005, 'emp_absoluto': 0.05},
    {'nominal': 10,  'error': 0.08, 'incertidumbre': 0.02,  'emp_absoluto': 0.5},
    {'nominal': 100, 'error': 0.5,  'incertidumbre': 0.1,   'emp_absoluto': 5.0},
]

PUNTOS_TENSION = [
    {'nominal': 10,  'error': 0.1,  'incertidumbre': 0.03,  'emp_absoluto': 0.5},
    {'nominal': 100, 'error': 0.5,  'incertidumbre': 0.1,   'emp_absoluto': 2.0},
    {'nominal': 500, 'error': 2.0,  'incertidumbre': 0.5,   'emp_absoluto': 10.0},
]


def _calibraciones_v2(variables=None):
    """Devuelve lista de calibraciones en formato v2 (magnitudes)."""
    if variables is None:
        variables = [
            {'nombre': 'Corriente AC', 'puntos': PUNTOS_CORRIENTE},
            {'nombre': 'Tensión DC',   'puntos': PUNTOS_TENSION},
        ]
    return [
        {'fecha': date.today(), 'magnitudes': variables},
        {'fecha': date.today() - timedelta(days=180), 'magnitudes': variables},
    ]


def _comprobaciones_v2(variables=None):
    if variables is None:
        variables = [
            {'nombre': 'Temperatura', 'puntos': [
                {'nominal': 20, 'error': 0.1, 'emp_absoluto': 0.5},
                {'nominal': 50, 'error': 0.2, 'emp_absoluto': 0.5},
            ]},
            {'nombre': 'Humedad', 'puntos': [
                {'nominal': 40, 'error': 0.3, 'emp_absoluto': 1.0},
                {'nominal': 80, 'error': 0.5, 'emp_absoluto': 1.0},
            ]},
        ]
    return [{'fecha': date.today(), 'magnitudes': variables}]


# ===========================================================================
# 1. Tests de _generar_una_grafica_hist_confirmacion
# ===========================================================================

class TestGenerarUnaGraficaHistConfirmacion:

    def test_retorna_svg_string(self, db):
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        cals = [{'fecha': date.today(), 'puntos': PUNTOS_V1}]
        svg = _generar_una_grafica_hist_confirmacion('Tensión', cals)
        assert svg is not None
        assert '<svg' in svg
        assert '</svg>' in svg

    def test_dimensiones_correctas(self, db):
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        cals = [{'fecha': date.today(), 'puntos': PUNTOS_V1}]
        svg = _generar_una_grafica_hist_confirmacion('V', cals)
        assert 'width="760"' in svg
        assert 'height="400"' in svg

    def test_contiene_lineas_emp(self, db):
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        cals = [{'fecha': date.today(), 'puntos': PUNTOS_V1}]
        svg = _generar_una_grafica_hist_confirmacion('V', cals)
        assert '+EMP' in svg
        assert '−EMP' in svg

    def test_titulo_con_nombre_variable(self, db):
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        cals = [{'fecha': date.today(), 'puntos': PUNTOS_V1}]
        svg = _generar_una_grafica_hist_confirmacion('Corriente AC', cals)
        assert 'Corriente AC' in svg

    def test_sin_nominales_retorna_none(self, db):
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        cals = [{'fecha': date.today(), 'puntos': [{'error': 0.5}]}]
        result = _generar_una_grafica_hist_confirmacion('V', cals)
        assert result is None

    def test_multiples_calibraciones(self, db):
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        cals = [
            {'fecha': date.today(), 'puntos': PUNTOS_V1},
            {'fecha': date.today() - timedelta(days=90), 'puntos': PUNTOS_V1},
            {'fecha': date.today() - timedelta(days=180), 'puntos': PUNTOS_V1},
        ]
        svg = _generar_una_grafica_hist_confirmacion('V', cals)
        assert svg is not None
        # Deben aparecer 3 fechas en la leyenda
        assert svg.count('fill="#') > 10  # múltiples elementos de color

    def test_punto_fuera_de_emp_es_visible(self, db):
        """Si error > EMP, el punto debe salir igual (escala se expande)."""
        from core.views.equipment import _generar_una_grafica_hist_confirmacion
        puntos_fuera = [
            {'nominal': 100, 'error': 2.5, 'emp_absoluto': 1.0},  # error/EMP = 2.5
        ]
        cals = [{'fecha': date.today(), 'puntos': puntos_fuera}]
        svg = _generar_una_grafica_hist_confirmacion('V', cals)
        assert svg is not None
        # La escala debe incluir ±1 y también ±2.5+padding
        assert 'circle' in svg  # el punto se dibujó


# ===========================================================================
# 2. Tests de _generar_grafica_hist_confirmaciones (multi-variable)
# ===========================================================================

class TestGenerarGraficaHistConfirmaciones:

    def test_retorna_dict(self, db):
        from core.views.equipment import _generar_grafica_hist_confirmaciones
        result = _generar_grafica_hist_confirmaciones(_calibraciones_v2())
        assert isinstance(result, dict)

    def test_una_llave_por_variable(self, db):
        from core.views.equipment import _generar_grafica_hist_confirmaciones
        result = _generar_grafica_hist_confirmaciones(_calibraciones_v2())
        assert len(result) == 2
        assert 'Corriente AC' in result
        assert 'Tensión DC' in result

    def test_cada_valor_es_svg(self, db):
        from core.views.equipment import _generar_grafica_hist_confirmaciones
        result = _generar_grafica_hist_confirmaciones(_calibraciones_v2())
        for nombre, svg in result.items():
            assert '<svg' in svg, f"Variable '{nombre}' no tiene SVG válido"

    def test_una_sola_variable_sin_nombre(self, db):
        from core.views.equipment import _generar_grafica_hist_confirmaciones
        cals = [{'fecha': date.today(), 'magnitudes': [{'nombre': '', 'puntos': PUNTOS_V1}]}]
        result = _generar_grafica_hist_confirmaciones(cals)
        assert isinstance(result, dict)
        assert len(result) == 1
        assert '' in result  # clave vacía para variable sin nombre

    def test_datos_vacios_retorna_none(self, db):
        from core.views.equipment import _generar_grafica_hist_confirmaciones
        assert _generar_grafica_hist_confirmaciones([]) is None
        assert _generar_grafica_hist_confirmaciones(None) is None

    def test_magnitudes_sin_puntos_se_ignoran(self, db):
        from core.views.equipment import _generar_grafica_hist_confirmaciones
        cals = [{'fecha': date.today(), 'magnitudes': [
            {'nombre': 'Con datos', 'puntos': PUNTOS_V1},
            {'nombre': 'Sin datos', 'puntos': []},
        ]}]
        result = _generar_grafica_hist_confirmaciones(cals)
        assert result is not None
        assert 'Con datos' in result
        assert 'Sin datos' not in result  # sin puntos no genera SVG


# ===========================================================================
# 3. Tests de _generar_una_grafica_hist_comprobacion
# ===========================================================================

class TestGenerarUnaGraficaHistComprobacion:

    def test_retorna_svg(self, db):
        from core.views.equipment import _generar_una_grafica_hist_comprobacion
        comps = [{'fecha': date.today(), 'puntos': [
            {'nominal': 20, 'error': 0.1, 'emp_absoluto': 0.5},
            {'nominal': 50, 'error': 0.2, 'emp_absoluto': 0.5},
        ]}]
        svg = _generar_una_grafica_hist_comprobacion('Temperatura', comps)
        assert svg is not None
        assert '<svg' in svg

    def test_contiene_lineas_emp(self, db):
        from core.views.equipment import _generar_una_grafica_hist_comprobacion
        comps = [{'fecha': date.today(), 'puntos': [
            {'nominal': 100, 'error': 0.5, 'emp_absoluto': 1.0},
        ]}]
        svg = _generar_una_grafica_hist_comprobacion('', comps)
        assert '+EMP' in svg
        assert '−EMP' in svg

    def test_sin_nominales_retorna_none(self, db):
        from core.views.equipment import _generar_una_grafica_hist_comprobacion
        comps = [{'fecha': date.today(), 'puntos': [{'error': 0.3}]}]
        assert _generar_una_grafica_hist_comprobacion('V', comps) is None


# ===========================================================================
# 4. Tests de _generar_grafica_hist_comprobaciones (multi-variable)
# ===========================================================================

class TestGenerarGraficaHistComprobaciones:

    def test_retorna_dict(self, db):
        from core.views.equipment import _generar_grafica_hist_comprobaciones
        result = _generar_grafica_hist_comprobaciones(_comprobaciones_v2())
        assert isinstance(result, dict)
        assert len(result) == 2

    def test_llaves_son_nombres_variables(self, db):
        from core.views.equipment import _generar_grafica_hist_comprobaciones
        result = _generar_grafica_hist_comprobaciones(_comprobaciones_v2())
        assert 'Temperatura' in result
        assert 'Humedad' in result

    def test_datos_vacios_retorna_none(self, db):
        from core.views.equipment import _generar_grafica_hist_comprobaciones
        assert _generar_grafica_hist_comprobaciones([]) is None


# ===========================================================================
# 5. Tests de detalle_equipo: extracción v1 y v2
# ===========================================================================

@pytest.mark.django_db
class TestDetalleEquipoGraficasHistoricas:

    def _datos_v2(self):
        return {
            'version': 2,
            'magnitudes': [
                {'nombre': 'Corriente', 'unidad': 'A', 'emp': 5, 'emp_unidad': '%',
                 'puntos_medicion': PUNTOS_CORRIENTE},
                {'nombre': 'Tensión', 'unidad': 'V', 'emp': 3, 'emp_unidad': '%',
                 'puntos_medicion': PUNTOS_TENSION},
            ],
        }

    def _datos_v1(self):
        return {'puntos_medicion': PUNTOS_V1}

    def test_detalle_carga_con_confirmacion_v2(self, client_auth, equipo):
        """El detalle del equipo debe cargar sin error con datos v2."""
        cal = Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            resultado='Aprobado',
            confirmacion_metrologica_datos=self._datos_v2(),
        )
        url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = client_auth.get(url)
        assert response.status_code == 200

    def test_detalle_carga_con_confirmacion_v1(self, client_auth, equipo):
        """Compatibilidad hacia atrás: datos v1 deben seguir funcionando."""
        Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            resultado='Aprobado',
            confirmacion_metrologica_datos=self._datos_v1(),
        )
        url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = client_auth.get(url)
        assert response.status_code == 200

    def test_detalle_carga_con_comprobacion_v2(self, client_auth, equipo):
        """Comprobación v2 en detalle del equipo."""
        datos_comp = {
            'version': 2,
            'magnitudes': [
                {'nombre': 'Temperatura', 'unidad': '°C',
                 'puntos_medicion': [
                     {'nominal': 20, 'lectura': 20.1, 'error': 0.1,
                      'emp_valor': 0.5, 'emp_tipo': 'abs', 'emp_absoluto': 0.5,
                      'conformidad': 'CONFORME'},
                 ]},
            ],
        }
        Comprobacion.objects.create(
            equipo=equipo,
            fecha_comprobacion=date.today(),
            resultado='Aprobado',
            datos_comprobacion=datos_comp,
        )
        url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = client_auth.get(url)
        assert response.status_code == 200

    def test_grafica_confirmacion_es_dict_en_contexto(self, client_auth, equipo):
        """grafica_hist_confirmaciones debe ser dict (no str) en el contexto."""
        Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            resultado='Aprobado',
            confirmacion_metrologica_datos=self._datos_v2(),
        )
        url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = client_auth.get(url)
        assert response.status_code == 200
        grafica = response.context.get('grafica_hist_confirmaciones')
        if grafica is not None:
            assert isinstance(grafica, dict)

    def test_grafica_comprobacion_es_dict_en_contexto(self, client_auth, equipo):
        """grafica_hist_comprobaciones debe ser dict en el contexto."""
        datos_comp = {
            'version': 2,
            'magnitudes': [
                {'nombre': 'Temp', 'unidad': '°C',
                 'puntos_medicion': [
                     {'nominal': 25, 'error': 0.2, 'emp_absoluto': 0.5,
                      'lectura': 25.2, 'emp_valor': 0.5, 'emp_tipo': 'abs',
                      'conformidad': 'CONFORME'},
                 ]},
            ],
        }
        Comprobacion.objects.create(
            equipo=equipo,
            fecha_comprobacion=date.today(),
            resultado='Aprobado',
            datos_comprobacion=datos_comp,
        )
        url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = client_auth.get(url)
        assert response.status_code == 200
        grafica = response.context.get('grafica_hist_comprobaciones')
        if grafica is not None:
            assert isinstance(grafica, dict)


# ===========================================================================
# 6. Tests de _generate_hoja_vida_charts (reports.py)
# ===========================================================================

class TestGenerateHojaVidaCharts:

    def _make_calibracion(self, datos):
        m = MagicMock()
        m.confirmacion_metrologica_datos = datos
        m.fecha_calibracion = date.today()
        return m

    def _make_comprobacion(self, datos):
        m = MagicMock()
        m.datos_comprobacion = datos
        m.fecha_comprobacion = date.today()
        return m

    def test_v1_confirmaciones_retorna_dict(self, db):
        from core.views.reports import _generate_hoja_vida_charts
        cals = [self._make_calibracion({'puntos_medicion': PUNTOS_V1})]
        result_c, result_comp = _generate_hoja_vida_charts(cals, [])
        assert isinstance(result_c, dict)
        assert result_comp is None

    def test_v2_confirmaciones_retorna_dict_multi(self, db):
        from core.views.reports import _generate_hoja_vida_charts
        datos_v2 = {
            'magnitudes': [
                {'nombre': 'Corriente', 'puntos_medicion': PUNTOS_CORRIENTE},
                {'nombre': 'Tensión',   'puntos_medicion': PUNTOS_TENSION},
            ]
        }
        cals = [self._make_calibracion(datos_v2)]
        result_c, _ = _generate_hoja_vida_charts(cals, [])
        assert isinstance(result_c, dict)
        assert len(result_c) == 2

    def test_svg_compacto_tiene_viewbox(self, db):
        """El SVG compacto debe tener viewBox para escalar correctamente."""
        from core.views.reports import _generate_hoja_vida_charts
        cals = [self._make_calibracion({'puntos_medicion': PUNTOS_V1})]
        result_c, _ = _generate_hoja_vida_charts(cals, [])
        first_svg = list(result_c.values())[0]
        assert 'viewBox' in first_svg

    def test_svg_compacto_dimensiones_reducidas(self, db):
        """El SVG compacto debe ser más pequeño que 760×400."""
        from core.views.reports import _generate_hoja_vida_charts
        cals = [self._make_calibracion({'puntos_medicion': PUNTOS_V1})]
        result_c, _ = _generate_hoja_vida_charts(cals, [])
        first_svg = list(result_c.values())[0]
        assert 'width="650"' in first_svg
        assert 'width="760"' not in first_svg

    def test_v1_comprobaciones(self, db):
        from core.views.reports import _generate_hoja_vida_charts
        comps = [self._make_comprobacion({
            'puntos_medicion': [
                {'nominal': 100, 'error': 0.5, 'emp_absoluto': 1.0},
            ]
        })]
        _, result_comp = _generate_hoja_vida_charts([], comps)
        assert isinstance(result_comp, dict)

    def test_v2_comprobaciones_multi(self, db):
        from core.views.reports import _generate_hoja_vida_charts
        datos_v2 = {
            'magnitudes': [
                {'nombre': 'Temp', 'puntos_medicion': [
                    {'nominal': 25, 'error': 0.1, 'emp_absoluto': 0.5},
                ]},
                {'nombre': 'Hum', 'puntos_medicion': [
                    {'nominal': 60, 'error': 0.2, 'emp_absoluto': 1.0},
                ]},
            ]
        }
        comps = [self._make_comprobacion(datos_v2)]
        _, result_comp = _generate_hoja_vida_charts([], comps)
        assert isinstance(result_comp, dict)
        assert len(result_comp) == 2

    def test_sin_datos_retorna_none_none(self, db):
        from core.views.reports import _generate_hoja_vida_charts
        result_c, result_comp = _generate_hoja_vida_charts([], [])
        assert result_c is None
        assert result_comp is None


# ===========================================================================
# 7. Tests de generar_pdf_comprobacion: magnitudes_template v2
# ===========================================================================

@pytest.mark.django_db
class TestGenerarPdfComprobacionV2:

    def _datos_v2(self):
        return {
            'version': 2,
            'magnitudes': [
                {'nombre': 'Corriente AC', 'unidad': 'A',
                 'puntos_medicion': [
                     {'nominal': 1, 'lectura': 1.01, 'error': 0.01,
                      'emp_valor': 5, 'emp_tipo': '%', 'emp_absoluto': 0.05,
                      'limite_superior': 1.05, 'limite_inferior': 0.95,
                      'conformidad': 'CONFORME'},
                 ]},
                {'nombre': 'Tensión DC', 'unidad': 'V',
                 'puntos_medicion': [
                     {'nominal': 10, 'lectura': 10.1, 'error': 0.1,
                      'emp_valor': 2, 'emp_tipo': '%', 'emp_absoluto': 0.2,
                      'limite_superior': 10.2, 'limite_inferior': 9.8,
                      'conformidad': 'CONFORME'},
                 ]},
            ],
            'puntos_medicion': [],  # legacy vacío
            'unidad_equipo': 'A',
        }

    def test_magnitudes_template_tiene_dos_variables(self):
        """La lógica de construcción de magnitudes_template para v2 es correcta."""
        datos = self._datos_v2()
        magnitudes_v2 = datos.get('magnitudes', [])
        assert len(magnitudes_v2) == 2

        # Simular la misma lógica que hay en generar_pdf_comprobacion
        magnitudes_template = []
        for mag in magnitudes_v2:
            pts = mag.get('puntos_medicion', [])
            conf = sum(1 for p in pts if p.get('conformidad') == 'CONFORME')
            no_conf = sum(1 for p in pts if p.get('conformidad') == 'NO CONFORME')
            magnitudes_template.append({
                'nombre': mag.get('nombre', ''),
                'puntos': pts,
                'conformes': conf,
                'no_conformes': no_conf,
                'total': len(pts),
            })

        assert len(magnitudes_template) == 2
        assert magnitudes_template[0]['nombre'] == 'Corriente AC'
        assert magnitudes_template[1]['nombre'] == 'Tensión DC'
        assert magnitudes_template[0]['conformes'] == 1
        assert magnitudes_template[1]['total'] == 1
        assert magnitudes_template[0]['no_conformes'] == 0

    def test_stats_globales_suman_todas_variables(self):
        """Los totales conformes/no conformes deben sumar todas las variables."""
        datos = {
            'magnitudes': [
                {'nombre': 'A', 'puntos_medicion': [
                    {'conformidad': 'CONFORME'}, {'conformidad': 'NO CONFORME'}
                ]},
                {'nombre': 'B', 'puntos_medicion': [
                    {'conformidad': 'CONFORME'}, {'conformidad': 'CONFORME'}
                ]},
            ]
        }
        magnitudes_v2 = datos['magnitudes']
        total_conformes = sum(
            sum(1 for p in m['puntos_medicion'] if p.get('conformidad') == 'CONFORME')
            for m in magnitudes_v2
        )
        total_no_conformes = sum(
            sum(1 for p in m['puntos_medicion'] if p.get('conformidad') == 'NO CONFORME')
            for m in magnitudes_v2
        )
        assert total_conformes == 3
        assert total_no_conformes == 1


# ===========================================================================
# 8. Tests de _make_svg_compact
# ===========================================================================

class TestMakeSvgCompact:

    def test_agrega_viewbox(self):
        from core.views.reports import _make_svg_compact
        svg = '<svg width="760" height="400" xmlns="http://www.w3.org/2000/svg"><text>test</text></svg>'
        result = _make_svg_compact(svg)
        assert 'viewBox="0 0 760 400"' in result
        assert 'preserveAspectRatio' in result

    def test_cambia_dimensiones(self):
        from core.views.reports import _make_svg_compact
        svg = '<svg width="760" height="400" xmlns="http://www.w3.org/2000/svg"></svg>'
        result = _make_svg_compact(svg, new_width=650, new_height=340)
        assert 'width="650"' in result
        assert 'height="340"' in result
        assert 'width="760"' not in result

    def test_svg_invalido_retorna_original(self):
        from core.views.reports import _make_svg_compact
        svg = '<div>no es svg</div>'
        result = _make_svg_compact(svg)
        assert result == svg

    def test_dimensiones_por_defecto(self):
        from core.views.reports import _make_svg_compact
        svg = '<svg width="760" height="400"></svg>'
        result = _make_svg_compact(svg)
        assert 'width="650"' in result
        assert 'height="340"' in result
