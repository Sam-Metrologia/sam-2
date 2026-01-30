"""
Tests para el Calendario de Actividades.

Cubre: vista principal, API de eventos, filtros, multitenancy,
exclusión de equipos inactivos/de baja, y exportación iCal.
"""
import json
import pytest
from datetime import date, timedelta

from django.test import Client
from django.urls import reverse

from core.models import (
    Empresa, CustomUser, Equipo,
    Calibracion, Mantenimiento, Comprobacion,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(
        nombre="Empresa Calendario Test",
        nit="900555111-1",
        limite_equipos_empresa=100,
    )


@pytest.fixture
def otra_empresa(db):
    return Empresa.objects.create(
        nombre="Otra Empresa Test",
        nit="900555222-2",
        limite_equipos_empresa=100,
    )


@pytest.fixture
def usuario(empresa):
    return CustomUser.objects.create_user(
        username="user_cal",
        email="cal@test.com",
        password="testpass123",
        empresa=empresa,
        rol_usuario="TECNICO",
    )


@pytest.fixture
def superusuario(empresa):
    return CustomUser.objects.create_user(
        username="super_cal",
        email="supercal@test.com",
        password="testpass123",
        empresa=empresa,
        is_superuser=True,
        is_staff=True,
    )


@pytest.fixture
def usuario_otra_empresa(otra_empresa):
    return CustomUser.objects.create_user(
        username="user_otra",
        email="otra@test.com",
        password="testpass123",
        empresa=otra_empresa,
        rol_usuario="TECNICO",
    )


@pytest.fixture
def user_client(usuario):
    client = Client()
    client.login(username="user_cal", password="testpass123")
    client.user = usuario
    return client


@pytest.fixture
def super_client(superusuario):
    client = Client()
    client.login(username="super_cal", password="testpass123")
    client.user = superusuario
    return client


@pytest.fixture
def otra_empresa_client(usuario_otra_empresa):
    client = Client()
    client.login(username="user_otra", password="testpass123")
    client.user = usuario_otra_empresa
    return client


@pytest.fixture
def equipo_activo(empresa):
    """Equipo activo con fechas programadas. Usa update() para evitar que save() las recalcule."""
    hoy = date.today()
    equipo = Equipo.objects.create(
        codigo_interno="EQ-CAL-001",
        nombre="Balanza Activa",
        empresa=empresa,
        tipo_equipo="Balanza",
        estado="Activo",
        responsable="Juan Perez",
    )
    # update() evita el save() que recalcula las fechas
    Equipo.objects.filter(pk=equipo.pk).update(
        proxima_calibracion=hoy + timedelta(days=10),
        proximo_mantenimiento=hoy + timedelta(days=20),
        proxima_comprobacion=hoy + timedelta(days=15),
    )
    equipo.refresh_from_db()
    return equipo


@pytest.fixture
def equipo_inactivo(empresa):
    hoy = date.today()
    equipo = Equipo.objects.create(
        codigo_interno="EQ-CAL-002",
        nombre="Termometro Inactivo",
        empresa=empresa,
        tipo_equipo="Termómetro",
        estado="Inactivo",
        responsable="Maria Lopez",
    )
    Equipo.objects.filter(pk=equipo.pk).update(
        proxima_calibracion=hoy + timedelta(days=5),
    )
    equipo.refresh_from_db()
    return equipo


@pytest.fixture
def equipo_de_baja(empresa):
    hoy = date.today()
    equipo = Equipo.objects.create(
        codigo_interno="EQ-CAL-003",
        nombre="Manometro De Baja",
        empresa=empresa,
        tipo_equipo="Manómetro",
        estado="De Baja",
        responsable="Pedro Garcia",
    )
    Equipo.objects.filter(pk=equipo.pk).update(
        proxima_calibracion=hoy + timedelta(days=5),
    )
    equipo.refresh_from_db()
    return equipo


@pytest.fixture
def equipo_otra_empresa(otra_empresa):
    hoy = date.today()
    equipo = Equipo.objects.create(
        codigo_interno="EQ-OTRA-001",
        nombre="Equipo Otra Empresa",
        empresa=otra_empresa,
        tipo_equipo="Balanza",
        estado="Activo",
        responsable="Carlos Ruiz",
    )
    Equipo.objects.filter(pk=equipo.pk).update(
        proxima_calibracion=hoy + timedelta(days=10),
    )
    equipo.refresh_from_db()
    return equipo


@pytest.fixture
def calibracion_realizada(equipo_activo):
    return Calibracion.objects.create(
        equipo=equipo_activo,
        fecha_calibracion=date.today() - timedelta(days=5),
        nombre_proveedor="Lab ABC",
        resultado="Aprobado",
        numero_certificado="CERT-001",
    )


@pytest.fixture
def mantenimiento_realizado(equipo_activo):
    return Mantenimiento.objects.create(
        equipo=equipo_activo,
        fecha_mantenimiento=date.today() - timedelta(days=3),
        tipo_mantenimiento="Preventivo",
        responsable="Juan Perez",
        descripcion="Limpieza general",
    )


@pytest.fixture
def comprobacion_realizada(equipo_activo):
    return Comprobacion.objects.create(
        equipo=equipo_activo,
        fecha_comprobacion=date.today() - timedelta(days=2),
        resultado="Aprobado",
        responsable="Juan Perez",
    )


# ============================================================================
# Tests: Vista principal del calendario
# ============================================================================

@pytest.mark.django_db
class TestCalendarioVista:

    def test_requiere_login(self, client):
        url = reverse('core:calendario_actividades')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_renderiza_pagina(self, user_client):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        assert response.status_code == 200

    def test_contiene_contenedor_calendario(self, user_client):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        content = response.content.decode()
        assert 'id="calendar"' in content

    def test_contiene_filtros(self, user_client):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        content = response.content.decode()
        assert 'filtro-tipo' in content
        assert 'filtro-responsable' in content

    def test_contiene_boton_exportar(self, user_client):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        content = response.content.decode()
        assert 'Exportar iCal' in content

    def test_carga_fullcalendar_cdn(self, user_client):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        content = response.content.decode()
        assert 'fullcalendar' in content.lower()

    def test_responsables_en_dropdown(self, user_client, equipo_activo):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        content = response.content.decode()
        assert equipo_activo.responsable in content

    def test_responsables_excluye_inactivos(self, user_client, equipo_activo, equipo_inactivo):
        url = reverse('core:calendario_actividades')
        response = user_client.get(url)
        content = response.content.decode()
        assert equipo_activo.responsable in content
        assert equipo_inactivo.responsable not in content


# ============================================================================
# Tests: API de eventos
# ============================================================================

@pytest.mark.django_db
class TestCalendarioEventosAPI:

    def test_requiere_login(self, client):
        url = reverse('core:calendario_eventos_api')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_retorna_json(self, user_client):
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_retorna_lista(self, user_client):
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url)
        data = response.json()
        assert isinstance(data, list)

    def test_incluye_eventos_programados(self, user_client, equipo_activo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        # Debe tener al menos los 3 eventos programados del equipo activo
        tipos = [e['extendedProps']['tipo'] for e in data if e['extendedProps']['estado'] == 'programado']
        assert 'calibracion' in tipos
        assert 'mantenimiento' in tipos
        assert 'comprobacion' in tipos

    def test_incluye_eventos_realizados(self, user_client, calibracion_realizada):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=30)).isoformat(),
            'end': (hoy + timedelta(days=1)).isoformat(),
        })
        data = response.json()

        realizados = [e for e in data if e.get('extendedProps', {}).get('estado') == 'realizado']
        assert len(realizados) >= 1

    def test_colores_programado_vs_realizado(self, user_client, equipo_activo, calibracion_realizada):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=30)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        for evento in data:
            props = evento.get('extendedProps', {})
            if props.get('tipo') == 'calibracion':
                if props.get('estado') == 'programado':
                    assert evento['color'] == '#3b82f6'
                elif props.get('estado') == 'realizado':
                    assert evento['color'] == '#93c5fd'

    def test_excluye_equipos_inactivos(self, user_client, equipo_activo, equipo_inactivo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        nombres = [e['extendedProps']['equipo_nombre'] for e in data]
        assert equipo_activo.nombre in nombres
        assert equipo_inactivo.nombre not in nombres

    def test_excluye_equipos_de_baja(self, user_client, equipo_activo, equipo_de_baja):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        nombres = [e['extendedProps']['equipo_nombre'] for e in data]
        assert equipo_activo.nombre in nombres
        assert equipo_de_baja.nombre not in nombres

    def test_filtro_por_tipo_calibracion(self, user_client, equipo_activo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
            'tipo': 'calibracion',
        })
        data = response.json()

        for evento in data:
            assert evento['extendedProps']['tipo'] == 'calibracion'

    def test_filtro_por_tipo_mantenimiento(self, user_client, equipo_activo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
            'tipo': 'mantenimiento',
        })
        data = response.json()

        for evento in data:
            assert evento['extendedProps']['tipo'] == 'mantenimiento'

    def test_filtro_por_responsable(self, user_client, equipo_activo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
            'responsable': 'Juan Perez',
        })
        data = response.json()

        for evento in data:
            assert evento['extendedProps']['responsable'] == 'Juan Perez'

    def test_filtro_responsable_inexistente_retorna_vacio(self, user_client, equipo_activo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
            'responsable': 'Persona Inexistente',
        })
        data = response.json()
        assert len(data) == 0

    def test_rango_fuera_de_fechas_no_retorna_eventos(self, user_client, equipo_activo):
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': '2020-01-01',
            'end': '2020-01-31',
        })
        data = response.json()
        assert len(data) == 0

    def test_evento_tiene_propiedades_requeridas(self, user_client, equipo_activo):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        assert len(data) > 0
        evento = data[0]
        assert 'title' in evento
        assert 'start' in evento
        assert 'color' in evento
        assert 'extendedProps' in evento
        assert 'equipo_id' in evento['extendedProps']
        assert 'equipo_nombre' in evento['extendedProps']
        assert 'tipo' in evento['extendedProps']
        assert 'estado' in evento['extendedProps']

    def test_fechas_invalidas_no_falla(self, user_client):
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': 'fecha-invalida',
            'end': 'otra-invalida',
        })
        assert response.status_code == 200

    def test_sin_parametros_no_falla(self, user_client):
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url)
        assert response.status_code == 200


# ============================================================================
# Tests: Multitenancy
# ============================================================================

@pytest.mark.django_db
class TestCalendarioMultitenancy:

    def test_usuario_no_ve_equipos_de_otra_empresa(
        self, user_client, equipo_activo, equipo_otra_empresa
    ):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        nombres = [e['extendedProps']['equipo_nombre'] for e in data]
        assert equipo_activo.nombre in nombres
        assert equipo_otra_empresa.nombre not in nombres

    def test_superusuario_ve_todas_las_empresas(
        self, super_client, equipo_activo, equipo_otra_empresa
    ):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = super_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        nombres = [e['extendedProps']['equipo_nombre'] for e in data]
        assert equipo_activo.nombre in nombres
        assert equipo_otra_empresa.nombre in nombres

    def test_otra_empresa_no_ve_mis_equipos(
        self, otra_empresa_client, equipo_activo, equipo_otra_empresa
    ):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = otra_empresa_client.get(url, {
            'start': (hoy - timedelta(days=1)).isoformat(),
            'end': (hoy + timedelta(days=30)).isoformat(),
        })
        data = response.json()

        nombres = [e['extendedProps']['equipo_nombre'] for e in data]
        assert equipo_otra_empresa.nombre in nombres
        assert equipo_activo.nombre not in nombres


# ============================================================================
# Tests: Exportar iCal
# ============================================================================

@pytest.mark.django_db
class TestCalendarioExportarICal:

    def test_requiere_login(self, client):
        url = reverse('core:calendario_exportar_ical')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_descarga_archivo_ics(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/calendar; charset=utf-8'
        assert 'calendario_actividades.ics' in response['Content-Disposition']

    def test_formato_vcalendar_valido(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert content.startswith('BEGIN:VCALENDAR')
        assert 'END:VCALENDAR' in content
        assert 'VERSION:2.0' in content

    def test_contiene_eventos_programados(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert 'BEGIN:VEVENT' in content
        assert equipo_activo.nombre in content

    def test_excluye_equipos_inactivos(self, user_client, equipo_activo, equipo_inactivo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert equipo_activo.nombre in content
        assert equipo_inactivo.nombre not in content

    def test_excluye_equipos_de_baja(self, user_client, equipo_activo, equipo_de_baja):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert equipo_activo.nombre in content
        assert equipo_de_baja.nombre not in content

    def test_filtro_tipo_calibracion(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url, {'tipo': 'calibracion'})
        content = response.content.decode('utf-8')
        assert 'Calibración' in content
        assert 'Mantenimiento' not in content
        assert 'Comprobación' not in content

    def test_filtro_tipo_mantenimiento(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url, {'tipo': 'mantenimiento'})
        content = response.content.decode('utf-8')
        assert 'Mantenimiento' in content
        assert 'Calibración' not in content

    def test_filtro_responsable(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url, {'responsable': 'Juan Perez'})
        content = response.content.decode('utf-8')
        assert equipo_activo.nombre in content

    def test_filtro_responsable_inexistente(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url, {'responsable': 'Nadie Existe'})
        content = response.content.decode('utf-8')
        assert 'BEGIN:VEVENT' not in content

    def test_multitenancy_no_exporta_otra_empresa(
        self, user_client, equipo_activo, equipo_otra_empresa
    ):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert equipo_activo.nombre in content
        assert equipo_otra_empresa.nombre not in content

    def test_evento_tiene_uid(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert 'UID:' in content

    def test_evento_tiene_dtstart(self, user_client, equipo_activo):
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert 'DTSTART;VALUE=DATE:' in content

    def test_equipo_sin_fechas_programadas_no_genera_eventos(self, user_client, empresa):
        Equipo.objects.create(
            codigo_interno="EQ-VACIO-001",
            nombre="Equipo Sin Fechas",
            empresa=empresa,
            tipo_equipo="Balanza",
            estado="Activo",
        )
        url = reverse('core:calendario_exportar_ical')
        response = user_client.get(url)
        content = response.content.decode('utf-8')
        assert 'Equipo Sin Fechas' not in content


# ============================================================================
# Tests: Eventos realizados de cada tipo
# ============================================================================

@pytest.mark.django_db
class TestCalendarioEventosRealizados:

    def test_calibracion_realizada_aparece(self, user_client, calibracion_realizada):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=30)).isoformat(),
            'end': (hoy + timedelta(days=1)).isoformat(),
        })
        data = response.json()

        cals_realizadas = [
            e for e in data
            if e['extendedProps']['tipo'] == 'calibracion'
            and e['extendedProps']['estado'] == 'realizado'
        ]
        assert len(cals_realizadas) >= 1
        assert cals_realizadas[0]['color'] == '#93c5fd'

    def test_mantenimiento_realizado_aparece(self, user_client, mantenimiento_realizado):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=30)).isoformat(),
            'end': (hoy + timedelta(days=1)).isoformat(),
        })
        data = response.json()

        mants_realizados = [
            e for e in data
            if e['extendedProps']['tipo'] == 'mantenimiento'
            and e['extendedProps']['estado'] == 'realizado'
        ]
        assert len(mants_realizados) >= 1
        assert mants_realizados[0]['color'] == '#6ee7b7'

    def test_comprobacion_realizada_aparece(self, user_client, comprobacion_realizada):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=30)).isoformat(),
            'end': (hoy + timedelta(days=1)).isoformat(),
        })
        data = response.json()

        comps_realizadas = [
            e for e in data
            if e['extendedProps']['tipo'] == 'comprobacion'
            and e['extendedProps']['estado'] == 'realizado'
        ]
        assert len(comps_realizadas) >= 1
        assert comps_realizadas[0]['color'] == '#fcd34d'

    def test_evento_realizado_tiene_datos_extra(self, user_client, calibracion_realizada):
        hoy = date.today()
        url = reverse('core:calendario_eventos_api')
        response = user_client.get(url, {
            'start': (hoy - timedelta(days=30)).isoformat(),
            'end': (hoy + timedelta(days=1)).isoformat(),
            'tipo': 'calibracion',
        })
        data = response.json()

        realizados = [e for e in data if e['extendedProps']['estado'] == 'realizado']
        assert len(realizados) >= 1
        props = realizados[0]['extendedProps']
        assert 'resultado' in props
        assert 'certificado' in props
