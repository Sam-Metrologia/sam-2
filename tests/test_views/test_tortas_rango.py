"""
Tests para el endpoint API tortas_rango — filtro de gráficas de torta por rango de meses.
"""
import json
import pytest
from datetime import date
from dateutil.relativedelta import relativedelta
from django.urls import reverse


URL = 'core:tortas_rango'


@pytest.mark.django_db
@pytest.mark.views
class TestTortasRangoAuth:
    """Tests de autenticación."""

    def test_requiere_login(self, client):
        url = reverse(URL)
        resp = client.get(url)
        assert resp.status_code == 302
        assert '/login/' in resp.url

    def test_usuario_autenticado_puede_acceder(self, authenticated_client):
        today = date.today()
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': today.strftime('%Y-%m'), 'hasta': today.strftime('%Y-%m')})
        assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.views
class TestTortasRangoValidacion:
    """Tests de validación de parámetros."""

    def test_sin_parametros_retorna_400(self, authenticated_client):
        url = reverse(URL)
        resp = authenticated_client.get(url)
        assert resp.status_code == 400
        data = resp.json()
        assert 'error' in data

    def test_formato_invalido_retorna_400(self, authenticated_client):
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': '01-2025', 'hasta': '03-2025'})
        assert resp.status_code == 400

    def test_rango_invertido_retorna_400(self, authenticated_client):
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': '2025-06', 'hasta': '2025-01'})
        assert resp.status_code == 400

    def test_mismo_mes_valido(self, authenticated_client):
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': '2025-01', 'hasta': '2025-01'})
        assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.views
class TestTortasRangoRespuesta:
    """Tests de estructura de la respuesta JSON."""

    def test_estructura_respuesta(self, authenticated_client):
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': '2025-01', 'hasta': '2025-03'})
        assert resp.status_code == 200
        data = resp.json()

        assert 'cal' in data
        assert 'mant' in data
        assert 'comp' in data
        assert 'mant_tipo' in data
        assert 'rango' in data

        assert data['rango']['desde'] == '2025-01'
        assert data['rango']['hasta'] == '2025-03'

    def test_claves_cal_presentes(self, authenticated_client):
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': '2025-01', 'hasta': '2025-12'})
        data = resp.json()

        cal = data['cal']
        for clave in [
            'cal_total_programmed_anual',
            'cal_realized_anual',
            'cal_no_cumplido_anual',
            'cal_pendiente_anual',
            'cal_realized_anual_percent',
            'cal_no_cumplido_anual_percent',
            'cal_pendiente_anual_percent',
        ]:
            assert clave in cal, f"Falta clave: {clave}"

    def test_sin_equipos_retorna_ceros(self, authenticated_client):
        """Con empresa sin equipos las tortas deben tener 0 en todos los conteos."""
        url = reverse(URL)
        resp = authenticated_client.get(url, {'desde': '2025-01', 'hasta': '2025-12'})
        data = resp.json()

        assert data['cal']['cal_total_programmed_anual'] == 0
        assert data['mant']['mant_total_programmed_anual'] == 0
        assert data['comp']['comp_total_programmed_anual'] == 0


@pytest.mark.django_db
@pytest.mark.views
class TestTortasRangoConEquipos:
    """Tests con equipos reales."""

    def test_calibracion_realizada_en_rango_cuenta_como_realizada(
        self, authenticated_client, equipo_factory, calibracion_factory
    ):
        user = authenticated_client.user
        today = date.today()
        equipo = equipo_factory(
            empresa=user.empresa,
            frecuencia_calibracion_meses=12,
            fecha_adquisicion=date(today.year - 1, 1, 1),
        )
        calibracion_factory(equipo=equipo, fecha_calibracion=date(today.year, today.month, 1))

        url = reverse(URL)
        desde = date(today.year, 1, 1).strftime('%Y-%m')
        hasta = date(today.year, 12, 1).strftime('%Y-%m')
        resp = authenticated_client.get(url, {'desde': desde, 'hasta': hasta})
        data = resp.json()

        assert data['cal']['cal_realized_anual'] >= 1

    def test_multitenancy_no_filtra_otra_empresa(
        self, authenticated_client, equipo_factory, empresa_factory
    ):
        """Equipos de otra empresa no deben aparecer en los datos."""
        today = date.today()
        otra_empresa = empresa_factory()
        equipo_factory(
            empresa=otra_empresa,
            frecuencia_calibracion_meses=12,
            fecha_adquisicion=date(today.year - 1, 1, 1),
        )

        url = reverse(URL)
        resp = authenticated_client.get(url, {
            'desde': f'{today.year}-01',
            'hasta': f'{today.year}-12',
        })
        data = resp.json()

        # El equipo de otra empresa no debe afectar los datos del usuario
        assert data['cal']['cal_total_programmed_anual'] == 0
