"""
Tests para el sistema de aprobaciones de documentos metrológicos.

Cubre: confirmaciones metrológicas, intervalos de calibración y comprobaciones.
"""
import json
import pytest
from django.test import Client
from django.urls import reverse
from django.core.files.base import ContentFile

from core.models import Empresa, CustomUser, Equipo, Calibracion, Comprobacion


@pytest.fixture
def empresa(db):
    return Empresa.objects.create(
        nombre="Empresa Test Aprobaciones",
        nit="900111222-3",
        limite_equipos_empresa=100,
    )


@pytest.fixture
def admin_user(empresa):
    return CustomUser.objects.create_user(
        username="admin_aprobador",
        email="admin@test.com",
        password="testpass123",
        empresa=empresa,
        rol_usuario="ADMINISTRADOR",
    )


@pytest.fixture
def tecnico_user(empresa):
    return CustomUser.objects.create_user(
        username="tecnico_creador",
        email="tecnico@test.com",
        password="testpass123",
        empresa=empresa,
        rol_usuario="TECNICO",
    )


@pytest.fixture
def otro_admin(empresa):
    """Segundo admin para probar auto-aprobación."""
    return CustomUser.objects.create_user(
        username="otro_admin",
        email="otroadmin@test.com",
        password="testpass123",
        empresa=empresa,
        rol_usuario="ADMINISTRADOR",
    )


@pytest.fixture
def equipo(empresa):
    return Equipo.objects.create(
        codigo_interno="EQ-APR-001",
        nombre="Equipo Aprobaciones Test",
        empresa=empresa,
        tipo_equipo="Equipo de Medición",
        estado="Activo",
    )


@pytest.fixture
def calibracion_con_confirmacion(equipo, tecnico_user):
    """Calibración con confirmación metrológica pendiente de aprobación (generada por plataforma)."""
    from datetime import date
    cal = Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=date.today(),
        nombre_proveedor="Lab Test",
        resultado="Aprobado",
        creado_por=tecnico_user,
        confirmacion_estado_aprobacion='pendiente',
        confirmacion_metrologica_datos={'puntos_medicion': [{'valor': 1.0}]},
    )
    cal.confirmacion_metrologica_pdf.save(
        'test_confirmacion.pdf',
        ContentFile(b'%PDF-1.4 test'),
        save=True,
    )
    return cal


@pytest.fixture
def calibracion_con_intervalos(equipo, tecnico_user):
    """Calibración con intervalos pendientes de aprobación (generada por plataforma)."""
    from datetime import date
    cal = Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=date.today(),
        nombre_proveedor="Lab Test Intervalos",
        resultado="Aprobado",
        creado_por=tecnico_user,
        intervalos_estado_aprobacion='pendiente',
        intervalos_calibracion_datos={'metodo': 'test', 'puntos_medicion': []},
    )
    cal.intervalos_calibracion_pdf.save(
        'test_intervalos.pdf',
        ContentFile(b'%PDF-1.4 test'),
        save=True,
    )
    return cal


@pytest.fixture
def comprobacion_pendiente(equipo, tecnico_user):
    """Comprobación metrológica pendiente de aprobación (generada por plataforma)."""
    from datetime import date
    comp = Comprobacion.objects.create(
        equipo=equipo,
        fecha_comprobacion=date.today(),
        resultado="Aprobado",
        creado_por=tecnico_user,
        estado_aprobacion='pendiente',
        datos_comprobacion={'puntos_medicion': [{'valor': 1.0, 'conformidad': 'CONFORME'}]},
    )
    comp.comprobacion_pdf.save(
        'test_comprobacion.pdf',
        ContentFile(b'%PDF-1.4 test'),
        save=True,
    )
    return comp


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    client.login(username="admin_aprobador", password="testpass123")
    client.user = admin_user
    return client


@pytest.fixture
def tecnico_client(tecnico_user):
    client = Client()
    client.login(username="tecnico_creador", password="testpass123")
    client.user = tecnico_user
    return client


# ===================== Tests de puede_aprobar() =====================

@pytest.mark.django_db
class TestPuedeAprobar:

    def test_admin_puede_aprobar_documento_de_otro(self, admin_user, calibracion_con_confirmacion):
        from core.views.aprobaciones import puede_aprobar
        assert puede_aprobar(admin_user, calibracion_con_confirmacion) is True

    def test_tecnico_no_puede_aprobar(self, tecnico_user, calibracion_con_confirmacion):
        from core.views.aprobaciones import puede_aprobar
        # Cambiar creado_por para que no sea el mismo técnico
        calibracion_con_confirmacion.creado_por = None
        assert puede_aprobar(tecnico_user, calibracion_con_confirmacion) is False

    def test_no_auto_aprobacion(self, admin_user, calibracion_con_confirmacion):
        from core.views.aprobaciones import puede_aprobar
        calibracion_con_confirmacion.creado_por = admin_user
        assert puede_aprobar(admin_user, calibracion_con_confirmacion) is False


# ===================== Tests de Aprobar Confirmación =====================

@pytest.mark.django_db
class TestAprobarConfirmacion:

    def test_aprobar_confirmacion_cambia_estado(self, admin_client, calibracion_con_confirmacion):
        url = reverse('core:aprobar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = admin_client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        calibracion_con_confirmacion.refresh_from_db()
        assert calibracion_con_confirmacion.confirmacion_estado_aprobacion == 'aprobado'
        assert calibracion_con_confirmacion.confirmacion_aprobado_por == admin_client.user
        assert calibracion_con_confirmacion.confirmacion_fecha_aprobacion is not None

    def test_tecnico_no_puede_aprobar_confirmacion(self, tecnico_client, calibracion_con_confirmacion):
        # El técnico es el creador, así que no puede aprobar
        url = reverse('core:aprobar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = tecnico_client.post(url)

        assert response.status_code == 403

        calibracion_con_confirmacion.refresh_from_db()
        assert calibracion_con_confirmacion.confirmacion_estado_aprobacion == 'pendiente'

    def test_rechazar_confirmacion_guarda_motivo(self, admin_client, calibracion_con_confirmacion):
        url = reverse('core:rechazar_confirmacion', args=[calibracion_con_confirmacion.id])
        motivo = "El análisis tiene datos incorrectos en el punto 3"
        response = admin_client.post(
            url,
            data=json.dumps({'observaciones': motivo}),
            content_type='application/json',
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        calibracion_con_confirmacion.refresh_from_db()
        assert calibracion_con_confirmacion.confirmacion_estado_aprobacion == 'rechazado'
        assert calibracion_con_confirmacion.confirmacion_observaciones_rechazo == motivo
        assert calibracion_con_confirmacion.confirmacion_aprobado_por is None

    def test_rechazar_sin_observaciones_falla(self, admin_client, calibracion_con_confirmacion):
        url = reverse('core:rechazar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = admin_client.post(
            url,
            data=json.dumps({'observaciones': ''}),
            content_type='application/json',
        )

        assert response.status_code == 400

        calibracion_con_confirmacion.refresh_from_db()
        assert calibracion_con_confirmacion.confirmacion_estado_aprobacion == 'pendiente'


# ===================== Tests de Aprobar Intervalos =====================

@pytest.mark.django_db
class TestAprobarIntervalos:

    def test_aprobar_intervalos_cambia_estado(self, admin_client, calibracion_con_intervalos):
        url = reverse('core:aprobar_intervalos', args=[calibracion_con_intervalos.id])
        response = admin_client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        calibracion_con_intervalos.refresh_from_db()
        assert calibracion_con_intervalos.intervalos_estado_aprobacion == 'aprobado'
        assert calibracion_con_intervalos.intervalos_aprobado_por == admin_client.user


# ===================== Tests de Aprobar Comprobación =====================

@pytest.mark.django_db
class TestAprobarComprobacion:

    def test_aprobar_comprobacion_cambia_estado(self, admin_client, comprobacion_pendiente):
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_pendiente.id])
        response = admin_client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        comprobacion_pendiente.refresh_from_db()
        assert comprobacion_pendiente.estado_aprobacion == 'aprobado'
        assert comprobacion_pendiente.aprobado_por == admin_client.user

    def test_rechazar_comprobacion_guarda_motivo(self, admin_client, comprobacion_pendiente):
        url = reverse('core:rechazar_comprobacion', args=[comprobacion_pendiente.id])
        motivo = "Puntos de medición fuera de rango"
        response = admin_client.post(
            url,
            data=json.dumps({'observaciones': motivo}),
            content_type='application/json',
        )

        assert response.status_code == 200

        comprobacion_pendiente.refresh_from_db()
        assert comprobacion_pendiente.estado_aprobacion == 'rechazado'
        assert comprobacion_pendiente.observaciones_rechazo == motivo


# ===================== Tests de Página de Aprobaciones =====================

@pytest.mark.django_db
class TestPaginaAprobaciones:

    def test_pagina_lista_pendientes(self, admin_client, calibracion_con_confirmacion):
        url = reverse('core:aprobaciones')
        response = admin_client.get(url)

        assert response.status_code == 200
        assert response.context['es_aprobador'] is True
        # El admin ve la confirmación pendiente (creada por otro usuario)
        assert calibracion_con_confirmacion in response.context['confirmaciones_pendientes']

    def test_pagina_excluye_documentos_propios(self, empresa, equipo):
        """Un admin no debe ver sus propios documentos pendientes para aprobar."""
        from datetime import date
        admin = CustomUser.objects.create_user(
            username="admin_propio",
            email="adminprop@test.com",
            password="testpass123",
            empresa=empresa,
            rol_usuario="ADMINISTRADOR",
        )
        cal = Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            nombre_proveedor="Lab",
            resultado="Aprobado",
            creado_por=admin,
            confirmacion_estado_aprobacion='pendiente',
        )
        cal.confirmacion_metrologica_pdf.save(
            'test.pdf', ContentFile(b'%PDF'), save=True,
        )

        client = Client()
        client.login(username="admin_propio", password="testpass123")

        url = reverse('core:aprobaciones')
        response = client.get(url)

        assert response.status_code == 200
        assert cal not in response.context['confirmaciones_pendientes']

    def test_tecnico_ve_solo_sus_documentos(self, tecnico_client, calibracion_con_confirmacion):
        url = reverse('core:aprobaciones')
        response = tecnico_client.get(url)

        assert response.status_code == 200
        assert response.context['es_aprobador'] is False
        # El técnico ve su propio documento pendiente
        assert calibracion_con_confirmacion in response.context['confirmaciones_pendientes']
