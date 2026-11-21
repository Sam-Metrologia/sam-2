"""
Tests de la lectura automática de certificados con IA (core/lectura_certificados.py y
core/views/lectura_ia.py).

Los casos de conversión imitan certificados reales probados en la fase 0 (2026-11-21):
laboratorios que redondean el error (Dishegro), que dan corrección en vez de error
(Novatest), multímetros que cambian de mV a V (Colmetrik), tablas por frecuencia (DEKRA),
factores de corrección con U en % (Wavecontrol) y errores en µm con lectura en mm (Pinzuar).
Los datos son inventados: no se guardan certificados de clientes en el repositorio.
"""
import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core import lectura_certificados as lc
from core.models import Calibracion, CustomUser, Empresa, Equipo, LecturaCertificado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def punto(ref, lect=None, err=None, tipo='error', u=None, u_tipo=None, unidad='psi', **extra):
    p = {
        'referencia': ref, 'unidad_referencia': extra.pop('unidad_referencia', unidad),
        'lectura': lect, 'unidad_lectura': extra.pop('unidad_lectura', unidad),
        'error_reportado': err, 'unidad_error': extra.pop('unidad_error', unidad), 'tipo_error': tipo,
        'incertidumbre': u, 'unidad_incertidumbre': extra.pop('unidad_incertidumbre', unidad),
        'incertidumbre_tipo': u_tipo, 'k': 2,
    }
    p.update(extra)
    return p


def resultado(*tablas, numero='CERT-1', fecha='2026-01-05', notas=None, confianza='alta'):
    return {'certificados': [{
        'laboratorio': 'Lab Prueba', 'numero_certificado': numero, 'fecha_calibracion': fecha,
        'equipo': {'tipo': 'Manómetro'}, 'notas': notas,
        'tablas': [{'nombre': nombre, 'confianza': confianza, 'puntos': puntos} for nombre, puntos in tablas],
    }]}


class EquipoFalso:
    def __init__(self, emp='2 %'):
        self.error_maximo_permisible = emp


_n = 0


def _empresa():
    global _n
    _n += 1
    return Empresa.objects.create(nombre=f'Empresa IA {_n}', nit=f'9{_n:08d}-1', email=f'ia{_n}@test.com')


def _usuario(empresa, superusuario=False):
    user = CustomUser.objects.create_user(
        username=f'ia_user_{CustomUser.objects.count()}', password='testpass123', empresa=empresa,
        is_superuser=superusuario, is_staff=superusuario, rol_usuario='ADMINISTRADOR')
    if not superusuario:
        for codename in ('can_view_calibracion', 'can_change_calibracion'):
            user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


def _equipo(empresa, codigo='IA-001', estado='Activo', emp='2%'):
    return Equipo.objects.create(empresa=empresa, codigo_interno=codigo, nombre=f'Equipo {codigo}',
                                 error_maximo_permisible=emp, estado=estado)


def _calibracion(equipo, dias=30, con_pdf=True, confirmacion=None, numero='CERT-1'):
    cal = Calibracion.objects.create(
        equipo=equipo, fecha_calibracion=date.today() - timedelta(days=dias),
        numero_certificado=numero, resultado='Aprobado')
    if con_pdf:
        cal.documento_calibracion.save('cert.pdf', SimpleUploadedFile('cert.pdf', b'%PDF-1.4 prueba'), save=True)
    if confirmacion is not None:
        Calibracion.objects.filter(pk=cal.pk).update(confirmacion_metrologica_datos=confirmacion)
        cal.refresh_from_db()
    return cal


def _cliente(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture(autouse=True)
def sin_hilos(settings):
    """En tests no se arrancan hilos: la cola se procesa a mano con procesar_pendientes()."""
    settings.LECTURA_IA_EN_SEGUNDO_PLANO = False


# ---------------------------------------------------------------------------
# Conversión de unidades
# ---------------------------------------------------------------------------

class TestFactorConversion:
    @pytest.mark.parametrize('desde,hacia,esperado', [
        ('V', 'V', 1.0), ('mV', 'V', 1e-3), ('V', 'mV', 1e3), ('µm', 'mm', 1e-3), ('um', 'mm', 1e-3),
        ('μm', 'mm', 1e-3), ('lux', 'klx', 1e-3), ('klx', 'lx', 1e3), ('kΩ', 'Ω', 1e3), ('mbar', 'bar', 1e-3),
        ('dB', 'dBuV', 1.0), ('m', 'mm', 1e3),
    ])
    def test_convertibles(self, desde, hacia, esperado):
        assert lc.factor_conversion(desde, hacia) == pytest.approx(esperado)

    @pytest.mark.parametrize('desde,hacia', [('psi', 'bar'), ('V', 'A'), ('%', 'V'), ('ppm', 'mm')])
    def test_no_convertibles(self, desde, hacia):
        assert lc.factor_conversion(desde, hacia) is None


# ---------------------------------------------------------------------------
# construir_propuesta: reglas decididas con el usuario
# ---------------------------------------------------------------------------

class TestErrorDelCertificado:
    def test_usa_el_error_del_certificado_aunque_no_cuadre_por_redondeo(self):
        # Dishegro: patrón 49,9 / lectura 50,0 / error 0,06 (recalcularlo daría 0,1).
        prop = lc.construir_propuesta(resultado(('Presión', [punto(49.9, 50.0, 0.06, u=0.15)])))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert p['nominal'] == 49.9 and p['lectura'] == 50.0
        assert p['error_certificado'] == 0.06

    def test_correccion_se_convierte_a_error_cambiando_signo(self):
        # Novatest: corrección = patrón - lectura.
        prop = lc.construir_propuesta(resultado(('Metano', [
            punto(1020, 1000, 10, tipo='correccion', u=74, unidad='ppm')])))
        assert prop['magnitudes'][0]['puntos_medicion'][0]['error_certificado'] == -10

    def test_correccion_cero_no_queda_como_menos_cero(self):
        prop = lc.construir_propuesta(resultado(('Gas', [punto(0, 0, 0, tipo='correccion', u=0.5, unidad='ppm')])))
        valor = prop['magnitudes'][0]['puntos_medicion'][0]['error_certificado']
        assert valor == 0 and str(valor) == '0.0'

    @pytest.mark.parametrize('tipo,unidad_error', [('relativo_%', '%'), ('factor', None), ('ninguno', None)])
    def test_sin_error_absoluto_la_plataforma_lo_calcula(self, tipo, unidad_error):
        prop = lc.construir_propuesta(resultado(('Fuerza', [
            punto(24.9996, 25.6667, 2.7, tipo=tipo, u=1.1, unidad='N', unidad_error=unidad_error)])))
        assert 'error_certificado' not in prop['magnitudes'][0]['puntos_medicion'][0]

    def test_error_en_micras_con_lectura_en_mm_se_convierte(self):
        # Pinzuar pie de rey: error en µm, patrón y lectura en mm.
        prop = lc.construir_propuesta(resultado(('Exteriores', [
            punto(2.05, 2.067, 16.7, u=6.6, unidad='mm', unidad_error='µm', unidad_incertidumbre='µm')])))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert p['error_certificado'] == pytest.approx(0.0167)
        assert p['incertidumbre'] == pytest.approx(0.0066)


class TestPuntosIncompletos:
    def test_sin_lectura_pero_con_error_se_reconstruye(self):
        prop = lc.construir_propuesta(resultado(('Ángulo', [punto(45, None, 0.2, u=0.1, unidad='°')])))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert p['lectura'] == pytest.approx(45.2)
        assert 'lectura' in p['revisar']

    def test_sin_lectura_ni_error_se_descarta_y_tabla_vacia_desaparece(self):
        prop = lc.construir_propuesta(resultado(
            ('Buena', [punto(10, 10.1, None, tipo='ninguno', u=0.1)]),
            ('Repetibilidad', [punto(30, None, None, tipo='ninguno')]),
        ))
        assert [m['nombre'] for m in prop['magnitudes']] == ['Buena']
        assert any('sin lectura ni error' in a for a in prop['lectura_ia']['avisos'])

    def test_sin_referencia_se_descarta(self):
        prop = lc.construir_propuesta(resultado(('T', [punto(None, 5, 0.1), punto(10, 10.1, 0.1, u=0.1)])))
        assert len(prop['magnitudes'][0]['puntos_medicion']) == 1

    def test_incertidumbre_en_porcentaje_pasa_a_absoluta(self):
        # Wavecontrol: U = 2,8 % del valor.
        prop = lc.construir_propuesta(resultado(('Campo E', [
            punto(750, 746.3, 1.005, tipo='factor', u=2.8, u_tipo='%', unidad='V/m', unidad_incertidumbre='%')])))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert p['incertidumbre'] == pytest.approx(21.0)
        assert 'revisar' not in p

    def test_incertidumbre_por_formula_queda_vacia_y_marcada(self):
        prop = lc.construir_propuesta(resultado(
            ('Regla', [punto(9.99, 10.0, -0.01, tipo='correccion', u=None, unidad='mm')]),
            notas='U = ± (0.041 + 0.0046*L) mm'))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert p['incertidumbre'] == ''
        assert 'incertidumbre' in p['revisar']
        assert any('0.041' in a for a in prop['lectura_ia']['avisos'])

    def test_tabla_poco_legible_se_marca_completa(self):
        prop = lc.construir_propuesta(resultado(('T', [punto(10, 10.1, 0.1, u=0.1)]), confianza='baja'))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert set(p['revisar']) >= {'nominal', 'lectura', 'incertidumbre'}


class TestVariablesSeparadas:
    def test_multimetro_que_pasa_de_mV_a_V_queda_en_una_variable_en_V(self):
        prop = lc.construir_propuesta(resultado(('Tensión DC', [
            punto(540, 540.3, 0.3, u=0.069, unidad='mV'),
            punto(6, 6.01, 0.01, u=0.0048, unidad='V'), punto(18, 18.01, 0.01, u=0.0048, unidad='V'),
        ])))
        assert len(prop['magnitudes']) == 1
        mag = prop['magnitudes'][0]
        assert (mag['nombre'], mag['unidad']) == ('Tensión DC', 'V')
        p = mag['puntos_medicion'][0]
        assert (p['nominal'], p['lectura'], p['incertidumbre'], p['error_certificado']) == pytest.approx(
            (0.54, 0.5403, 0.000069, 0.0003))

    def test_nombre_fijo_por_magnitud_no_por_titulo_del_laboratorio(self):
        datos = {'certificados': [{'numero_certificado': 'X', 'fecha_calibracion': '2026-01-01', 'tablas': [
            {'nombre': 'Tabla 1. Resultados de las Superficies para Medición de Exteriores',
             'magnitud': 'Longitud', 'variante': 'Exteriores', 'puntos': [punto(10, 10.01, 0.01, u=0.006, unidad='mm')]},
            {'nombre': 'Tabla 2. Resultados de Interiores', 'magnitud': 'Longitud', 'variante': 'Interiores',
             'puntos': [punto(5, 4.96, -0.04, u=0.006, unidad='mm')]},
        ]}]}
        prop = lc.construir_propuesta(datos)
        assert [m['nombre'] for m in prop['magnitudes']] == ['Longitud · Exteriores', 'Longitud · Interiores']

    def test_misma_tabla_en_dos_unidades_carga_las_dos(self):
        # Novatest: la misma tabla en mbar (instrumento) y en kPa (SI).
        datos = {'certificados': [{'numero_certificado': 'CP', 'fecha_calibracion': '2026-06-23', 'tablas': [
            {'nombre': 'En unidades del instrumento', 'magnitud': 'Presión',
             'puntos': [punto(10.43, 10, 0.43, tipo='correccion', u=0.54, unidad='mbar')]},
            {'nombre': 'En SI', 'magnitud': 'Presión',
             'puntos': [punto(1.043, 1.0, 0.043, tipo='correccion', u=0.054, unidad='kPa')]},
        ]}]}
        prop = lc.construir_propuesta(datos)
        assert [(m['nombre'], m['unidad']) for m in prop['magnitudes']] == [
            ('Presión (mbar)', 'mbar'), ('Presión (kPa)', 'kPa')]

    def test_si_la_ia_pone_la_unidad_como_variante_se_ignora(self):
        datos = {'certificados': [{'numero_certificado': 'CP', 'tablas': [
            {'nombre': 'a', 'magnitud': 'Presión', 'variante': 'psi', 'puntos': [punto(2.772, 2.8, -0.028, u=0.06)]},
            {'nombre': 'b', 'magnitud': 'Presión', 'variante': 'kPa',
             'puntos': [punto(19.11, 19.31, -0.19, u=0.41, unidad='kPa')]},
        ]}]}
        assert [m['nombre'] for m in lc.construir_propuesta(datos)['magnitudes']] == [
            'Presión (psi)', 'Presión (kPa)']

    def test_cada_frecuencia_es_una_variable(self):
        # DEKRA: la misma tabla a varias frecuencias.
        puntos = [punto(r, r + 2, 2, u=1.4, unidad='dBuV', unidad_error='dB', condicion=f)
                  for f in ('50 MHz', '250 MHz') for r in (99.9, 89.9, 81.9)]
        prop = lc.construir_propuesta(resultado(('Nivel de entrada', puntos)))
        assert [m['nombre'] for m in prop['magnitudes']] == [
            'Nivel de entrada · 50 MHz', 'Nivel de entrada · 250 MHz']
        assert all('revisar' not in p for m in prop['magnitudes'] for p in m['puntos_medicion'])

    def test_frecuencia_con_un_solo_punto_igual_se_separa_si_las_demas_tienen_varios(self):
        # Multímetro: corriente AC a 60 Hz (2 puntos), 1 kHz (2) y 500 Hz (1).
        puntos = [punto(54, 53.95, -0.05, u=0.075, unidad='mA', condicion='60 Hz'),
                  punto(540, 540, 0, u=0.81, unidad='mA', condicion='60 Hz'),
                  punto(6, 6.02, 0.02, u=0.011, unidad='mA', condicion='1 kHz'),
                  punto(54, 54.2, 0.2, u=0.075, unidad='mA', condicion='1 kHz'),
                  punto(18, 18.05, 0.05, u=0.0065, unidad='A', condicion='500 Hz')]
        prop = lc.construir_propuesta(resultado(('Corriente AC', puntos)))
        assert [m['nombre'] for m in prop['magnitudes']] == [
            'Corriente AC · 60 Hz', 'Corriente AC · 1 kHz', 'Corriente AC · 500 Hz']

    @pytest.mark.parametrize('condicion,esperada', [
        ('(0,00 a 19,99) Ω', ''), ('(20,0 a 199,9) Ω', ''), ('0 - 600 mV', ''), ('0,1 lx ≤ Ev < 85 lx', ''),
        ('500 V, 4,00 MΩ a 39,99 MΩ', '500 V'), ('60 Hz', '60 Hz'), ('1 kHz', '1 kHz'), ('Eje X', 'Eje X'),
        ('Aire Sintético', ''), ('3 Vrms', '3 Vrms'), (None, ''),
    ])
    def test_el_rango_del_equipo_no_es_condicion(self, condicion, esperada):
        assert lc._condicion_limpia(condicion) == esperada

    def test_rangos_distintos_de_la_misma_funcion_quedan_en_una_tabla(self):
        # Telurómetro: misma resistencia medida en 3 rangos del equipo.
        puntos = [punto(1.0073, 1.02, 0.0127, u=0.0078, unidad='Ω', condicion='(0,00 a 19,99) Ω'),
                  punto(5.007, 5.01, 0.003, u=0.0089, unidad='Ω', condicion='(0,00 a 19,99) Ω'),
                  punto(20.0033, 20.2, 0.197, u=0.049, unidad='Ω', condicion='(20,0 a 199,9) Ω'),
                  punto(180, 182.3, 2.3, u=0.071, unidad='Ω', condicion='(20,0 a 199,9) Ω'),
                  punto(500, 501, 1, u=0.49, unidad='Ω', condicion='(200 a 999) Ω')]
        prop = lc.construir_propuesta(resultado(('Resistencia', puntos)))
        assert len(prop['magnitudes']) == 1
        assert prop['magnitudes'][0]['nombre'] == 'Resistencia'
        assert len(prop['magnitudes'][0]['puntos_medicion']) == 5

    def test_rango_con_tension_de_prueba_conserva_solo_la_tension(self):
        puntos = [punto(0.5, 0.498, -0.002, u=0.0022, unidad='MΩ', condicion='500 V, 0,100 MΩ a 3,999 MΩ'),
                  punto(5, 5.02, 0.02, u=0.0086, unidad='MΩ', condicion='500 V, 4,00 MΩ a 39,99 MΩ')]
        prop = lc.construir_propuesta(resultado(('Aislamiento', puntos)))
        assert [m['nombre'] for m in prop['magnitudes']] == ['Aislamiento · 500 V']

    def test_gas_cero_va_en_la_misma_tabla(self):
        puntos = [punto(0, 0, 0, tipo='correccion', u=0.58, unidad='ppm', condicion='Aire Sintético'),
                  punto(1020, 1000, 10, tipo='correccion', u=74, unidad='ppm', condicion='Metano (CH4)'),
                  punto(10000, 10000, 10, tipo='correccion', u=130, unidad='ppm', condicion='Metano (CH4)')]
        prop = lc.construir_propuesta(resultado(('Detector', puntos)))
        assert len(prop['magnitudes']) == 1
        assert [p['nominal'] for p in prop['magnitudes'][0]['puntos_medicion']] == [0, 1020, 10000]

    def test_no_modifica_lo_que_leyo_gemini(self):
        datos = resultado(('R', [punto(1, 1.02, 0.02, u=0.01, unidad='Ω', condicion='(0 a 20) Ω')]))
        copia = json.loads(json.dumps(datos))
        lc.construir_propuesta(datos)
        assert datos == copia

    def test_respuesta_en_frecuencia_con_un_punto_por_frecuencia_no_se_parte(self):
        puntos = [punto(750, 748, None, tipo='factor', u=2.8, u_tipo='%', unidad='V/m', condicion=f)
                  for f in ('10 Hz', '60 Hz', '1 kHz')]
        prop = lc.construir_propuesta(resultado(('Respuesta en frecuencia · Eje X', puntos)))
        assert len(prop['magnitudes']) == 1
        assert len(prop['magnitudes'][0]['puntos_medicion']) == 3


class TestVariosCertificadosEnUnPdf:
    def _pdf_con_tres(self):
        datos = {'certificados': []}
        for numero, fecha in (('CC 230321-92468', '2023-03-21'), ('CLX-241056', '2024-08-08'),
                              ('LX-001-47', '2025-10-29')):
            datos['certificados'].append({
                'laboratorio': 'Lab', 'numero_certificado': numero, 'fecha_calibracion': fecha,
                'tablas': [{'nombre': 'Iluminancia', 'puntos': [punto(500, 498, -2, u=3.5, unidad='lx')]}]})
        return datos

    def test_carga_todos_con_la_fecha_de_cada_certificado(self):
        # Si están unidos en un PDF es porque se analizan en conjunto.
        class Cal:
            numero_certificado = 'lx-001-47'
            fecha_calibracion = date(2025, 10, 29)
        prop = lc.construir_propuesta(self._pdf_con_tres(), calibracion=Cal())
        assert [m['nombre'] for m in prop['magnitudes']] == [
            'Iluminancia · cert. 2023-03-21', 'Iluminancia · cert. 2024-08-08', 'Iluminancia · cert. 2025-10-29']
        # Los datos generales son los del certificado de esta calibración.
        assert prop['numero_certificado'] == 'LX-001-47'
        assert any('se cargaron todos' in a for a in prop['lectura_ia']['avisos'])

    def test_sin_saber_cual_es_toma_los_datos_del_mas_reciente(self):
        prop = lc.construir_propuesta(self._pdf_con_tres())
        assert len(prop['magnitudes']) == 3
        assert prop['fecha_certificado'] == '2025-10-29'


class TestNombresDeAniosAnteriores:
    def test_reusa_el_nombre_anterior_con_la_misma_unidad(self):
        prop = lc.construir_propuesta(resultado(('Presión', [punto(10, 10.1, 0.1, u=0.1, unidad='mbar')])),
                                      nombres_previos=[('Presión manómetro', 'mbar'), ('Otra', 'psi')])
        assert prop['magnitudes'][0]['nombre'] == 'Presión manómetro'
        assert any('misma gráfica histórica' in a for a in prop['lectura_ia']['avisos'])

    def test_reusa_confirmacion_antigua_sin_nombre(self):
        prop = lc.construir_propuesta(resultado(('Presión', [punto(10, 10.1, 0.1, u=0.1, unidad='psi')])),
                                      nombres_previos=[('', 'psi')])
        assert prop['magnitudes'][0]['nombre'] == ''

    def test_si_el_nombre_ya_coincide_no_cambia_nada(self):
        prop = lc.construir_propuesta(resultado(('Presión', [punto(10, 10.1, 0.1, u=0.1, unidad='psi')])),
                                      nombres_previos=[('Presión', 'psi'), ('Otra', 'psi')])
        assert prop['magnitudes'][0]['nombre'] == 'Presión'

    def test_no_adivina_si_hay_varias_candidatas(self):
        datos = {'certificados': [{'numero_certificado': 'X', 'tablas': [
            {'nombre': 'a', 'magnitud': 'Longitud', 'variante': 'Exteriores', 'puntos': [punto(1, 1.01, 0.01, u=0.01, unidad='mm')]},
            {'nombre': 'b', 'magnitud': 'Longitud', 'variante': 'Interiores', 'puntos': [punto(1, 1.01, 0.01, u=0.01, unidad='mm')]},
        ]}]}
        prop = lc.construir_propuesta(datos, nombres_previos=[('Ext', 'mm'), ('Int', 'mm')])
        assert [m['nombre'] for m in prop['magnitudes']] == ['Longitud · Exteriores', 'Longitud · Interiores']


class TestEmpYDatosGenerales:
    def test_emp_de_la_hoja_de_vida_va_en_cada_punto(self):
        prop = lc.construir_propuesta(resultado(('T', [punto(10, 10.1, 0.1, u=0.1)])), equipo=EquipoFalso('0,5 %'))
        p = prop['magnitudes'][0]['puntos_medicion'][0]
        assert (p['emp_valor'], p['emp_tipo']) == (0.5, '%')

    def test_emp_absoluto(self):
        prop = lc.construir_propuesta(resultado(('T', [punto(10, 10.1, 0.1, u=0.1)])), equipo=EquipoFalso('0.2 mm'))
        assert prop['magnitudes'][0]['emp'] == 0.2 and prop['magnitudes'][0]['emp_unidad'] == 'abs'

    def test_sin_emp_lee_igual_y_avisa(self):
        prop = lc.construir_propuesta(resultado(('T', [punto(10, 10.1, 0.1, u=0.1)])), equipo=EquipoFalso(''))
        assert prop['magnitudes'][0]['puntos_medicion'][0]['emp_valor'] == ''
        assert any('EMP' in a for a in prop['lectura_ia']['avisos'])

    def test_datos_del_certificado(self):
        prop = lc.construir_propuesta(resultado(('T', [punto(10, 10.1, 0.1, u=0.1)]), numero='P-303-24', fecha='2024-10-31'))
        assert prop['numero_certificado'] == 'P-303-24'
        assert prop['fecha_certificado'] == '2024-10-31'
        assert prop['laboratorio'] == 'Lab Prueba'
        assert prop['version'] == 2

    def test_pdf_sin_resultados(self):
        prop = lc.construir_propuesta({'certificados': []})
        assert prop['magnitudes'] == []
        assert prop['lectura_ia']['avisos']


class TestResultadoMagnitud:
    def test_puntos_no_aplica_no_cuentan(self):
        from core.views.confirmacion import _resultado_magnitud
        assert _resultado_magnitud([{'conformidad': 'N/A'}, {'conformidad': 'Cumple'}]) == 'APTO'
        assert _resultado_magnitud([{'conformidad': 'N/A'}, {'conformidad': 'No Cumple'}]) == 'NO APTO'
        assert _resultado_magnitud([{'conformidad': 'N/A'}]) == 'NO APTO'
        assert _resultado_magnitud([]) == 'APTO'  # comportamiento previo


# ---------------------------------------------------------------------------
# Cola de lecturas
# ---------------------------------------------------------------------------

RESULTADO_OK = resultado(('Presión', [punto(49.9, 50.0, 0.06, u=0.15), punto(99.9, 100.0, 0.06, u=0.15)]))
INFO_OK = {'segundos': 12.3, 'tokens_entrada': 2000, 'tokens_salida': 3000}


@pytest.mark.django_db
class TestCola:
    def test_no_se_puede_leer_sin_pdf(self):
        cal = _calibracion(_equipo(_empresa()), con_pdf=False)
        with pytest.raises(lc.ErrorLectura):
            lc.solicitar_lectura(cal)

    def test_lectura_exitosa_guarda_propuesta(self):
        cal = _calibracion(_equipo(_empresa()))
        lc.solicitar_lectura(cal)
        with patch('core.lectura_certificados.leer_pdf_con_gemini', return_value=(RESULTADO_OK, INFO_OK)) as gemini:
            assert lc.procesar_pendientes() == 1
        gemini.assert_called_once_with(b'%PDF-1.4 prueba')
        lectura = LecturaCertificado.objects.get(calibracion=cal)
        assert lectura.estado == LecturaCertificado.ESTADO_LISTO
        assert lectura.resultado_crudo == RESULTADO_OK
        assert lectura.propuesta['magnitudes'][0]['puntos_medicion'][0]['error_certificado'] == 0.06
        assert (lectura.tokens_entrada, lectura.tokens_salida, lectura.intentos) == (2000, 3000, 1)
        assert lectura.empresa_id == cal.equipo.empresa_id

    def test_sin_saldo_en_gemini_falla_con_mensaje_claro(self):
        cal = _calibracion(_equipo(_empresa()))
        lc.solicitar_lectura(cal)
        with patch('core.lectura_certificados.leer_pdf_con_gemini',
                   side_effect=Exception('402 RESOURCE_EXHAUSTED prepayment credits are depleted')):
            lc.procesar_pendientes()
        lectura = LecturaCertificado.objects.get(calibracion=cal)
        assert lectura.estado == LecturaCertificado.ESTADO_FALLO
        assert 'saldo' in lectura.mensaje_error

    def test_un_certificado_que_falla_no_frena_a_los_demas(self):
        empresa = _empresa()
        malo = _calibracion(_equipo(empresa, 'A'))
        bueno = _calibracion(_equipo(empresa, 'B'))
        lc.solicitar_lectura(malo)
        lc.solicitar_lectura(bueno)
        with patch('core.lectura_certificados.leer_pdf_con_gemini',
                   side_effect=[RuntimeError('timeout'), (RESULTADO_OK, INFO_OK)]):
            assert lc.procesar_pendientes() == 2
        assert LecturaCertificado.objects.get(calibracion=malo).estado == 'fallo'
        assert LecturaCertificado.objects.get(calibracion=bueno).estado == 'listo'

    def test_usa_los_nombres_de_confirmaciones_anteriores_del_equipo(self):
        equipo = _equipo(_empresa())
        _calibracion(equipo, dias=400, confirmacion={'version': 2, 'magnitudes': [
            {'nombre': 'Presión del manómetro', 'unidad': 'psi', 'puntos_medicion': []}]})
        cal = _calibracion(equipo, dias=10)
        assert lc.nombres_previos_equipo(cal) == [('Presión del manómetro', 'psi')]
        lc.solicitar_lectura(cal)
        with patch('core.lectura_certificados.leer_pdf_con_gemini', return_value=(RESULTADO_OK, INFO_OK)):
            lc.procesar_pendientes()
        assert LecturaCertificado.objects.get(calibracion=cal).propuesta['magnitudes'][0]['nombre'] == 'Presión del manómetro'

    def test_una_lectura_solo_se_reserva_una_vez(self):
        lc.solicitar_lectura(_calibracion(_equipo(_empresa())))
        assert lc.tomar_siguiente() is not None
        assert lc.tomar_siguiente() is None

    def test_lectura_interrumpida_por_reinicio_se_retoma(self):
        cal = _calibracion(_equipo(_empresa()))
        lectura = lc.solicitar_lectura(cal)
        LecturaCertificado.objects.filter(pk=lectura.pk).update(
            estado='procesando', intentos=1, iniciado_en=timezone.now() - timedelta(minutes=30))
        retomada = lc.tomar_siguiente()
        assert retomada.pk == lectura.pk and retomada.intentos == 2

    def test_lectura_interrumpida_tres_veces_falla(self):
        lectura = lc.solicitar_lectura(_calibracion(_equipo(_empresa())))
        LecturaCertificado.objects.filter(pk=lectura.pk).update(
            estado='procesando', intentos=3, iniciado_en=timezone.now() - timedelta(minutes=30))
        assert lc.tomar_siguiente() is None
        assert LecturaCertificado.objects.get(pk=lectura.pk).estado == 'fallo'

    def test_volver_a_solicitar_reinicia_una_fallida(self):
        cal = _calibracion(_equipo(_empresa()))
        lectura = lc.solicitar_lectura(cal)
        lectura.marcar_fallo('x')
        lectura = lc.solicitar_lectura(cal)
        assert lectura.estado == 'pendiente' and lectura.intentos == 0 and lectura.mensaje_error == ''


@pytest.mark.django_db
class TestCandidatasMasivas:
    def test_solo_ultima_calibracion_con_pdf_y_sin_confirmacion(self):
        empresa = _empresa()
        eq1 = _equipo(empresa, 'E1')
        _calibracion(eq1, dias=400)                       # vieja: no
        ultima_eq1 = _calibracion(eq1, dias=10)           # sí
        eq2 = _equipo(empresa, 'E2')
        _calibracion(eq2, dias=10, confirmacion={'version': 2, 'magnitudes': []})  # ya confirmada: no
        eq3 = _equipo(empresa, 'E3')
        _calibracion(eq3, dias=10, con_pdf=False)         # sin PDF: no
        eq4 = _equipo(empresa, 'E4', estado='De Baja')
        _calibracion(eq4, dias=10)                        # equipo de baja: no
        _calibracion(_equipo(_empresa(), 'OTRA'))        # otra empresa: no

        assert [c.id for c in lc.candidatas_masivas(empresa)] == [ultima_eq1.id]

    def test_no_repite_las_que_estan_en_curso_o_listas_pero_si_las_fallidas(self):
        empresa = _empresa()
        en_curso = _calibracion(_equipo(empresa, 'A'))
        fallida = _calibracion(_equipo(empresa, 'B'))
        lc.solicitar_lectura(en_curso)
        lc.solicitar_lectura(fallida).marcar_fallo('x')
        assert [c.id for c in lc.candidatas_masivas(empresa)] == [fallida.id]


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVistas:
    def test_solicitar_lectura(self):
        empresa = _empresa()
        cal = _calibracion(_equipo(empresa))
        resp = _cliente(_usuario(empresa)).post(reverse('core:solicitar_lectura_certificado', args=[cal.id]))
        assert resp.status_code == 200
        assert resp.json()['estado'] == 'pendiente'
        assert LecturaCertificado.objects.get(calibracion=cal).solicitado_por is not None

    def test_no_puede_leer_certificados_de_otra_empresa(self):
        cal = _calibracion(_equipo(_empresa()))
        resp = _cliente(_usuario(_empresa())).post(reverse('core:solicitar_lectura_certificado', args=[cal.id]))
        assert resp.status_code == 404
        assert not LecturaCertificado.objects.exists()

    def test_no_lee_si_ya_hay_confirmacion(self):
        empresa = _empresa()
        cal = _calibracion(_equipo(empresa), confirmacion={'version': 2, 'magnitudes': []})
        resp = _cliente(_usuario(empresa)).post(reverse('core:solicitar_lectura_certificado', args=[cal.id]))
        assert resp.status_code == 400

    def test_estado_y_descartar(self):
        empresa = _empresa()
        cal = _calibracion(_equipo(empresa))
        cliente = _cliente(_usuario(empresa))
        assert cliente.get(reverse('core:estado_lectura_certificado', args=[cal.id])).json()['estado'] == 'ninguna'
        lc.solicitar_lectura(cal)
        with patch('core.lectura_certificados.leer_pdf_con_gemini', return_value=(RESULTADO_OK, INFO_OK)):
            lc.procesar_pendientes()
        datos = cliente.get(reverse('core:estado_lectura_certificado', args=[cal.id])).json()
        assert datos['estado'] == 'listo' and datos['variables'] == 1
        cliente.post(reverse('core:descartar_lectura_certificado', args=[cal.id]))
        assert not LecturaCertificado.objects.filter(calibracion=cal).exists()

    def test_indice_lista_empresas_con_lo_pendiente(self):
        con_pdf = _empresa()
        _calibracion(_equipo(con_pdf, 'A'))
        cal_leida = _calibracion(_equipo(con_pdf, 'B'))
        LecturaCertificado.objects.create(calibracion=cal_leida, empresa=con_pdf, estado='listo', propuesta={})
        sin_pdf = _empresa()
        _calibracion(_equipo(sin_pdf, 'C'), con_pdf=False)
        superusuario = _usuario(_empresa(), superusuario=True)

        resp = _cliente(superusuario).get(reverse('core:lectura_certificados_indice'))
        assert resp.status_code == 200
        filas = {f['empresa'].id: f for f in resp.context['filas']}
        assert sin_pdf.id not in filas
        assert (filas[con_pdf.id]['por_leer'], filas[con_pdf.id]['por_revisar']) == (1, 1)
        assert 'Lectura de certificados IA' in resp.content.decode()  # entrada del menú

    def test_indice_solo_superusuario(self):
        resp = _cliente(_usuario(_empresa())).get(reverse('core:lectura_certificados_indice'))
        assert resp.status_code == 403

    def test_masiva_solo_superusuario(self):
        empresa = _empresa()
        resp = _cliente(_usuario(empresa)).get(reverse('core:lectura_masiva_empresa', args=[empresa.id]))
        assert resp.status_code == 403

    def test_masiva_encola_las_pendientes(self):
        empresa = _empresa()
        _calibracion(_equipo(empresa, 'A'))
        _calibracion(_equipo(empresa, 'B'))
        cliente = _cliente(_usuario(_empresa(), superusuario=True))
        url = reverse('core:lectura_masiva_empresa', args=[empresa.id])
        resp = cliente.get(url)
        assert resp.status_code == 200 and len(resp.context['candidatas']) == 2
        cliente.post(url)
        assert LecturaCertificado.objects.filter(empresa=empresa, origen='masiva', estado='pendiente').count() == 2
        assert len(cliente.get(url).context['candidatas']) == 0


@pytest.mark.django_db
class TestPrecargaEnConfirmacion:
    def _lectura_lista(self, cal, propuesta_extra=None):
        propuesta = lc.construir_propuesta(RESULTADO_OK, equipo=cal.equipo, calibracion=cal)
        if propuesta_extra:
            propuesta.update(propuesta_extra)
        return LecturaCertificado.objects.create(
            calibracion=cal, empresa=cal.equipo.empresa, estado='listo', propuesta=propuesta)

    def test_precarga_la_propuesta_si_no_hay_confirmacion(self):
        empresa = _empresa()
        equipo = _equipo(empresa)
        cal = _calibracion(equipo)
        self._lectura_lista(cal, {'laboratorio': '</script><script>alert(1)</script>'})
        resp = _cliente(_usuario(empresa)).get(
            reverse('core:confirmacion_metrologica', args=[equipo.id]) + f'?calibracion_id={cal.id}')
        assert resp.status_code == 200
        assert resp.context['lectura_ia_precargada'] is True
        html = resp.content.decode()
        assert 'Datos precargados desde el certificado' in html
        assert '"error_certificado": 0.06' in html
        # El texto que viene del PDF no puede cerrar el <script>.
        assert '</script><script>alert(1)' not in html

    def test_si_ya_hay_confirmacion_no_la_reemplaza(self):
        empresa = _empresa()
        equipo = _equipo(empresa)
        cal = _calibracion(equipo, confirmacion={'version': 2, 'magnitudes': [], 'laboratorio': 'Guardado'})
        self._lectura_lista(cal)
        resp = _cliente(_usuario(empresa)).get(
            reverse('core:confirmacion_metrologica', args=[equipo.id]) + f'?calibracion_id={cal.id}')
        assert resp.context['lectura_ia_precargada'] is False
        assert 'error_certificado' not in resp.context['datos_previos_json']

    def test_al_guardar_conserva_error_del_certificado_y_puntos_cero_y_negativos(self):
        empresa = _empresa()
        equipo = _equipo(empresa)
        cal = _calibracion(equipo)
        puntos = [
            {'nominal': -5.4, 'lectura': -5.408, 'incertidumbre': 0.00069, 'error': -0.008,
             'error_certificado': -0.008, 'conformidad': 'Cumple', 'emp_valor': 0.5, 'emp_tipo': '%'},
            {'nominal': 0, 'lectura': 0, 'incertidumbre': 0.048, 'error': 0,
             'conformidad': 'N/A', 'emp_valor': 0.5, 'emp_tipo': '%'},
            {'nominal': 49.9, 'lectura': 50.0, 'incertidumbre': 0.15, 'error': 0.06,
             'error_certificado': 0.06, 'conformidad': 'Cumple', 'emp_valor': 0.5, 'emp_tipo': '%'},
        ]
        datos = {'version': 2, 'magnitudes': [{'nombre': 'V', 'unidad': 'V', 'emp': 0.5, 'emp_unidad': '%',
                                               'puntos_medicion': puntos}],
                 'equipo': {'fecha_analisis': '2026-11-21'}, 'conclusion': {'decision': 'apto'}}
        with patch('weasyprint.HTML') as html:
            html.return_value.write_pdf.return_value = b'%PDF-1.4 conf'
            resp = _cliente(_usuario(empresa)).post(
                reverse('core:generar_pdf_confirmacion', args=[equipo.id]) + f'?calibracion_id={cal.id}',
                data=json.dumps(datos), content_type='application/json')
        assert resp.status_code == 200, resp.content[:300]
        cal.refresh_from_db()
        mag = cal.confirmacion_metrologica_datos['magnitudes'][0]
        guardados = mag['puntos_medicion']
        assert [p['nominal'] for p in guardados] == [-5.4, 0, 49.9]
        assert guardados[0]['error_certificado'] == -0.008
        assert 'error_certificado' not in guardados[1]
        # El punto en cero con EMP en % ("N/A") no vuelve NO APTA la variable.
        assert mag['resultado'] == 'APTO'

    def test_siguiente_pendiente_de_la_misma_empresa(self):
        empresa = _empresa()
        eq_a, eq_b, eq_c = _equipo(empresa, 'A-1'), _equipo(empresa, 'B-1'), _equipo(empresa, 'C-1')
        cal_a, cal_b = _calibracion(eq_a), _calibracion(eq_b)
        cal_c = _calibracion(eq_c, confirmacion={'version': 2, 'magnitudes': []})  # ya revisada: no cuenta
        for cal in (cal_a, cal_b, cal_c):
            self._lectura_lista(cal)
        self._lectura_lista(_calibracion(_equipo(_empresa(), 'Z-OTRA')))  # otra empresa: no cuenta
        resp = _cliente(_usuario(empresa)).get(
            reverse('core:confirmacion_metrologica', args=[eq_a.id]) + f'?calibracion_id={cal_a.id}')
        assert resp.context['lectura_ia_siguiente'].calibracion_id == cal_b.id
        assert resp.context['lectura_ia_pendientes'] == 1
        assert 'Saltar al siguiente pendiente (B-1)' in resp.content.decode()

    def test_muestra_boton_para_leer(self):
        empresa = _empresa()
        equipo = _equipo(empresa)
        cal = _calibracion(equipo)
        resp = _cliente(_usuario(empresa)).get(
            reverse('core:confirmacion_metrologica', args=[equipo.id]) + f'?calibracion_id={cal.id}')
        assert 'Leer certificado con IA' in resp.content.decode()
