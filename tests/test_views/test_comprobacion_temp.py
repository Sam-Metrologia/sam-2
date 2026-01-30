"""
Tests para confirmacion.py - Confirmación Metrológica

Enfoque en:
- Validaciones metrológicas críticas
- Parsing de puntos de calibración
- Cálculos de conformidad
- Manejo de datos JSON
- Edge cases con datos inválidos

NO testear:
- Generación de gráficas matplotlib (complejo, bajo ROI)
- Getters triviales
- Templates HTML
"""

import pytest
import json
from datetime import date, datetime, timedelta
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from decimal import Decimal

from core.models import Empresa, CustomUser, Equipo, Calibracion, Proveedor
from core.views.confirmacion import (
    safe_float,
    _preparar_contexto_confirmacion,
    confirmacion_metrologica,
    guardar_confirmacion
)


# ==================== FIXTURES ====================

@pytest.fixture
def empresa_test():
    """Empresa de prueba con configuración metrológica"""
    return Empresa.objects.create(
        nombre='Empresa Test Metrología',
        nit='900123456-7',
        email='test@metrologia.com',
        formato_codificacion_empresa='REG-TEST-CM-001',
        formato_version_empresa='1.0',
        formato_fecha_version_empresa=date.today()
    )


@pytest.fixture
def usuario_test(empresa_test):
    """Usuario autenticado de la empresa"""
    return CustomUser.objects.create_user(
        username='usuario_metro',
        email='usuario@metrologia.com',
        password='testpass123',
        empresa=empresa_test,
        first_name='Usuario',
        last_name='Test'
    )


@pytest.fixture
def proveedor_test(empresa_test):
    """Proveedor/laboratorio de calibración"""
    return Proveedor.objects.create(
        nombre_empresa='Lab Calibración Test',
        correo_electronico='lab@test.com',
        empresa=empresa_test,
        tipo_servicio='Calibración'
    )


@pytest.fixture
def equipo_test(empresa_test):
    """Equipo con datos metrológicos completos"""
    return Equipo.objects.create(
        empresa=empresa_test,
        codigo_interno='EQ-001',
        nombre='Balanza Analítica',
        marca='Mettler Toledo',
        modelo='XS204',
        numero_serie='SN12345',
        rango_medida='0 - 220 g',
        resolucion=Decimal('0.0001'),
        error_maximo_permisible='0.1%',
        puntos_calibracion='0, 50, 100, 150, 200',
        estado='ACTIVO'
    )


@pytest.fixture
def calibracion_test(equipo_test, proveedor_test):
    """Calibración reciente del equipo"""
    return Calibracion.objects.create(
        equipo=equipo_test,
        fecha_calibracion=date.today() - timedelta(days=30),
        proveedor=proveedor_test,
        numero_certificado='CERT-2026-001',
        resultado='Aprobado',  # Debe ser 'Aprobado' o 'No Aprobado' según el modelo
        costo_calibracion=Decimal('150.00')
    )


@pytest.fixture
def request_factory():
    """Factory para crear requests simulados"""
    return RequestFactory()


# ==================== TESTS: safe_float ====================

class TestSafeFloat:
    """Tests para la función helper safe_float - conversión segura crítica"""

    def test_safe_float_con_numero_valido(self):
        """Convertir número válido"""
        assert safe_float('123.45') == 123.45
        assert safe_float(456.78) == 456.78
        assert safe_float(100) == 100.0

    def test_safe_float_con_none_retorna_default(self):
        """None debe retornar valor default"""
        assert safe_float(None) == 0.0
        assert safe_float(None, 10.5) == 10.5

    def test_safe_float_con_string_vacio_retorna_default(self):
        """String vacío debe retornar default"""
        assert safe_float('') == 0.0
        assert safe_float('   ') == 0.0
        assert safe_float('', 5.0) == 5.0

    def test_safe_float_con_valor_invalido_retorna_default(self):
        """Valores inválidos deben retornar default"""
        assert safe_float('abc') == 0.0
        assert safe_float('12.34.56') == 0.0
        assert safe_float([1, 2, 3]) == 0.0
        assert safe_float({'key': 'value'}) == 0.0

    def test_safe_float_con_string_numerico(self):
        """Convertir strings numéricos correctamente"""
        assert safe_float('  42.5  ') == 42.5
        assert safe_float('-15.3') == -15.3
        assert safe_float('0') == 0.0

    def test_safe_float_con_default_customizado(self):
        """Usar default personalizado cuando falla conversión"""
        assert safe_float('invalid', 99.9) == 99.9
        assert safe_float(None, -1.0) == -1.0


# ==================== TESTS: _preparar_contexto_confirmacion ====================

@pytest.mark.django_db
class TestPrepararContextoConfirmacion:
    """Tests para preparación de contexto metrológico - lógica crítica"""

    def test_preparar_contexto_con_equipo_y_calibracion(
        self, request_factory, usuario_test, equipo_test, calibracion_test
    ):
        """Preparar contexto con datos completos"""
        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(
            request, equipo_test, calibracion_test
        )

        # Verificar estructura del contexto
        assert 'equipo' in context
        assert 'ultima_calibracion' in context
        assert 'puntos_medicion_json' in context
        assert 'emp_info' in context
        assert 'datos_confirmacion' in context

        # Verificar datos del equipo
        assert context['equipo'] == equipo_test
        assert context['ultima_calibracion'] == calibracion_test

    def test_parsear_puntos_medicion_desde_equipo(
        self, request_factory, usuario_test, equipo_test, calibracion_test
    ):
        """Parsear puntos de calibración desde campo del equipo"""
        # Equipo tiene: '0, 50, 100, 150, 200'
        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(
            request, equipo_test, calibracion_test
        )

        puntos_json = json.loads(context['puntos_medicion_json'])

        # Debe tener 5 puntos
        assert len(puntos_json) == 5

        # Verificar valores nominales
        assert puntos_json[0]['nominal'] == 0
        assert puntos_json[1]['nominal'] == 50
        assert puntos_json[2]['nominal'] == 100
        assert puntos_json[3]['nominal'] == 150
        assert puntos_json[4]['nominal'] == 200

        # Verificar estructura de cada punto
        for punto in puntos_json:
            assert 'nominal' in punto
            assert 'lectura' in punto
            assert 'incertidumbre' in punto
            assert 'error' in punto
            assert 'conformidad' in punto

    def test_parsear_puntos_con_formato_alternativo(
        self, request_factory, usuario_test, empresa_test, calibracion_test
    ):
        """Parsear puntos con diferentes separadores (;, saltos de línea)"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-002',
            nombre='Medidor Test',
            puntos_calibracion='10;20;30\n40;50'  # Mix de separadores
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        puntos_json = json.loads(context['puntos_medicion_json'])

        # Debe parsear correctamente todos los puntos
        assert len(puntos_json) == 5
        assert [p['nominal'] for p in puntos_json] == [10, 20, 30, 40, 50]

    def test_generar_puntos_automaticos_desde_rango(
        self, request_factory, usuario_test, empresa_test
    ):
        """Generar puntos automáticos cuando no están definidos"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-003',
            nombre='Equipo Sin Puntos',
            rango_medida='0 - 100',  # Tiene rango pero no puntos
            puntos_calibracion=''
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        puntos_json = json.loads(context['puntos_medicion_json'])

        # Debe generar 5 puntos equidistantes
        assert len(puntos_json) == 5
        assert puntos_json[0]['nominal'] == 0
        assert puntos_json[4]['nominal'] == 100

    def test_parsear_emp_porcentaje(
        self, request_factory, usuario_test, empresa_test
    ):
        """Parsear EMP en formato porcentaje"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-004',
            nombre='Equipo EMP %',
            error_maximo_permisible='0.5%'
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        emp_info = context['emp_info']

        assert emp_info['valor'] == 0.5
        assert emp_info['unidad'] == '%'
        assert '0.5%' in emp_info['texto']

    def test_parsear_emp_absoluto(
        self, request_factory, usuario_test, empresa_test
    ):
        """Parsear EMP en unidades absolutas"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-005',
            nombre='Equipo EMP Absoluto',
            error_maximo_permisible='2 mm'
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        emp_info = context['emp_info']

        assert emp_info['valor'] == 2.0
        assert emp_info['unidad'] == 'mm'

    def test_parsear_emp_sin_unidad(
        self, request_factory, usuario_test, empresa_test
    ):
        """Parsear EMP sin unidad explícita"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-006',
            nombre='Equipo EMP Simple',
            error_maximo_permisible='5.0'
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        emp_info = context['emp_info']

        assert emp_info['valor'] == 5.0
        assert emp_info['unidad'] == ''

    def test_contexto_con_datos_confirmacion_post(
        self, request_factory, usuario_test, equipo_test, calibracion_test
    ):
        """Preparar contexto con datos del POST (datos ingresados por usuario)"""
        request = request_factory.post('/guardar/')
        request.user = usuario_test

        datos_post = {
            'puntos_medicion': [
                {'nominal': 0, 'lectura': 0.001, 'error': 0.001, 'incertidumbre': 0.0005},
                {'nominal': 100, 'lectura': 99.995, 'error': -0.005, 'incertidumbre': 0.001}
            ],
            'formato': {
                'codigo': 'CUSTOM-001',
                'version': '2.0',
                'fecha': '2026-01-15'
            }
        }

        context = _preparar_contexto_confirmacion(
            request, equipo_test, calibracion_test, datos_post
        )

        # Verificar que usa datos del POST
        puntos_json = json.loads(context['puntos_medicion_json'])
        assert len(puntos_json) == 2
        assert puntos_json[0]['lectura'] == 0.001
        assert puntos_json[1]['error'] == -0.005

        # Verificar formato personalizado
        datos_conf = context['datos_confirmacion']
        assert datos_conf['formato']['codigo'] == 'CUSTOM-001'
        assert datos_conf['formato']['version'] == '2.0'

    def test_manejo_equipo_sin_calibraciones(
        self, request_factory, usuario_test, equipo_test
    ):
        """Manejar equipo sin calibraciones históricas"""
        # No crear calibración
        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo_test, None)

        # Debe funcionar sin calibraciones
        assert context['ultima_calibracion'] is None
        assert 'puntos_medicion_json' in context

        # Verificar datos de laboratorio por defecto
        datos_conf = context['datos_confirmacion']
        assert datos_conf['laboratorio'] == 'N/A'
        assert datos_conf['numero_certificado'] == 'N/A'


# ==================== TESTS: Edge Cases ====================

@pytest.mark.django_db
class TestConfirmacionEdgeCases:
    """Tests de casos extremos y validaciones"""

    def test_puntos_con_valores_negativos(
        self, request_factory, usuario_test, empresa_test
    ):
        """Manejar puntos de medición con valores negativos (temperaturas, etc)"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-TEMP',
            nombre='Termómetro',
            puntos_calibracion='-50, -25, 0, 25, 50'
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        puntos_json = json.loads(context['puntos_medicion_json'])

        assert len(puntos_json) == 5
        assert puntos_json[0]['nominal'] == -50
        assert puntos_json[2]['nominal'] == 0
        assert puntos_json[4]['nominal'] == 50

    def test_puntos_con_decimales(
        self, request_factory, usuario_test, empresa_test
    ):
        """Manejar puntos con valores decimales precisos"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-PRECISION',
            nombre='Micrómetro',
            puntos_calibracion='0.001, 0.005, 0.010, 0.050'
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        puntos_json = json.loads(context['puntos_medicion_json'])

        assert len(puntos_json) == 4
        assert puntos_json[0]['nominal'] == 0.001
        assert puntos_json[3]['nominal'] == 0.050

    def test_emp_con_formato_complejo(
        self, request_factory, usuario_test, empresa_test
    ):
        """Parsear EMP con formatos complejos"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-COMPLEX',
            nombre='Equipo Complejo',
            error_maximo_permisible='± 0.15 °C'  # Con símbolo ±
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        emp_info = context['emp_info']

        # Debe extraer el valor numérico
        assert emp_info['valor'] == 0.15
        assert emp_info['unidad'] == '°C'

    def test_rango_invalido_no_genera_puntos(
        self, request_factory, usuario_test, empresa_test
    ):
        """Rango mal formado no debe causar error"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-BAD-RANGE',
            nombre='Equipo Rango Malo',
            rango_medida='abc - xyz',  # Rango inválido
            puntos_calibracion=''
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        puntos_json = json.loads(context['puntos_medicion_json'])

        # No debe generar puntos si el rango es inválido
        assert len(puntos_json) == 0

    def test_puntos_con_caracteres_extra_ignora_invalidos(
        self, request_factory, usuario_test, empresa_test
    ):
        """Puntos con caracteres extra deben filtrar valores inválidos"""
        equipo = Equipo.objects.create(
            empresa=empresa_test,
            codigo_interno='EQ-MIXED',
            nombre='Equipo Mixto',
            puntos_calibracion='10, abc, 20, xyz, 30'  # Mix válidos/inválidos
        )

        request = request_factory.get('/confirmacion/')
        request.user = usuario_test

        context = _preparar_contexto_confirmacion(request, equipo, None)

        puntos_json = json.loads(context['puntos_medicion_json'])

        # Solo debe parsear los valores numéricos válidos
        assert len(puntos_json) == 3
        assert [p['nominal'] for p in puntos_json] == [10, 20, 30]
