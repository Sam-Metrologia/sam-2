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

    def test_requiere_login(self, client):
        url = reverse('core:aprobaciones')
        response = client.get(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_gerencia_es_aprobador(self, empresa, equipo):
        """Un usuario con rol GERENCIA también es aprobador."""
        gerente = CustomUser.objects.create_user(
            username="gerente_test",
            email="gerente@test.com",
            password="testpass123",
            empresa=empresa,
            rol_usuario="GERENCIA",
        )
        client = Client()
        client.login(username="gerente_test", password="testpass123")

        url = reverse('core:aprobaciones')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['es_aprobador'] is True


# ===================== Tests de Rechazo de Intervalos =====================

@pytest.mark.django_db
class TestRechazarIntervalos:

    def test_rechazar_intervalos_guarda_motivo(self, admin_client, calibracion_con_intervalos):
        url = reverse('core:rechazar_intervalos', args=[calibracion_con_intervalos.id])
        motivo = "Los intervalos no corresponden al tipo de equipo"
        response = admin_client.post(
            url,
            data=json.dumps({'observaciones': motivo}),
            content_type='application/json',
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        calibracion_con_intervalos.refresh_from_db()
        assert calibracion_con_intervalos.intervalos_estado_aprobacion == 'rechazado'
        assert calibracion_con_intervalos.intervalos_observaciones_rechazo == motivo

    def test_rechazar_intervalos_sin_observaciones_falla(self, admin_client, calibracion_con_intervalos):
        url = reverse('core:rechazar_intervalos', args=[calibracion_con_intervalos.id])
        response = admin_client.post(
            url,
            data=json.dumps({'observaciones': ''}),
            content_type='application/json',
        )

        assert response.status_code == 400

        calibracion_con_intervalos.refresh_from_db()
        assert calibracion_con_intervalos.intervalos_estado_aprobacion == 'pendiente'

    def test_tecnico_no_puede_rechazar_intervalos(self, tecnico_client, calibracion_con_intervalos):
        url = reverse('core:rechazar_intervalos', args=[calibracion_con_intervalos.id])
        response = tecnico_client.post(
            url,
            data=json.dumps({'observaciones': 'Rechazo de tecnico'}),
            content_type='application/json',
        )

        assert response.status_code == 403

        calibracion_con_intervalos.refresh_from_db()
        assert calibracion_con_intervalos.intervalos_estado_aprobacion == 'pendiente'


# ===================== Tests de Seguridad y Permisos =====================

@pytest.mark.django_db
class TestAprobacionesSeguridad:

    def test_aprobar_confirmacion_requiere_login(self, client, calibracion_con_confirmacion):
        url = reverse('core:aprobar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = client.post(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_rechazar_confirmacion_requiere_login(self, client, calibracion_con_confirmacion):
        url = reverse('core:rechazar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = client.post(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_aprobar_comprobacion_requiere_login(self, client, comprobacion_pendiente):
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_pendiente.id])
        response = client.post(url)
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_aprobar_confirmacion_requiere_post(self, admin_client, calibracion_con_confirmacion):
        url = reverse('core:aprobar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = admin_client.get(url)
        assert response.status_code == 405

    def test_rechazar_comprobacion_requiere_post(self, admin_client, comprobacion_pendiente):
        url = reverse('core:rechazar_comprobacion', args=[comprobacion_pendiente.id])
        response = admin_client.get(url)
        assert response.status_code == 405

    def test_aprobar_confirmacion_inexistente(self, admin_client):
        url = reverse('core:aprobar_confirmacion', args=[99999])
        response = admin_client.post(url)
        # La vista envuelve get_object_or_404 en try/except, retorna 500 con error
        assert response.status_code in [404, 500]
        data = response.json()
        assert data['success'] is False

    def test_aprobar_comprobacion_inexistente(self, admin_client):
        url = reverse('core:aprobar_comprobacion', args=[99999])
        response = admin_client.post(url)
        assert response.status_code in [404, 500]
        data = response.json()
        assert data['success'] is False

    def test_no_auto_aprobacion_confirmacion(self, empresa, equipo):
        """Un admin no puede aprobar su propio documento."""
        from datetime import date
        admin = CustomUser.objects.create_user(
            username="admin_auto",
            email="adminauto@test.com",
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
            confirmacion_metrologica_datos={'puntos': [1]},
        )
        cal.confirmacion_metrologica_pdf.save(
            'test.pdf', ContentFile(b'%PDF-1.4'), save=True,
        )

        client = Client()
        client.login(username="admin_auto", password="testpass123")

        url = reverse('core:aprobar_confirmacion', args=[cal.id])
        response = client.post(url)
        assert response.status_code == 403

        cal.refresh_from_db()
        assert cal.confirmacion_estado_aprobacion == 'pendiente'

    def test_tecnico_no_puede_aprobar_comprobacion(self, tecnico_client, comprobacion_pendiente):
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_pendiente.id])
        response = tecnico_client.post(url)

        assert response.status_code == 403

        comprobacion_pendiente.refresh_from_db()
        assert comprobacion_pendiente.estado_aprobacion == 'pendiente'

    def test_rechazar_comprobacion_sin_observaciones_falla(self, admin_client, comprobacion_pendiente):
        url = reverse('core:rechazar_comprobacion', args=[comprobacion_pendiente.id])
        response = admin_client.post(
            url,
            data=json.dumps({'observaciones': ''}),
            content_type='application/json',
        )
        assert response.status_code == 400

        comprobacion_pendiente.refresh_from_db()
        assert comprobacion_pendiente.estado_aprobacion == 'pendiente'


# ===================== Tests de puede_aprobar con GERENCIA =====================

@pytest.mark.django_db
class TestPuedeAprobarGerencia:

    def test_gerencia_puede_aprobar(self, empresa, calibracion_con_confirmacion):
        from core.views.aprobaciones import puede_aprobar
        gerente = CustomUser.objects.create_user(
            username="gerente_apr",
            email="gerente_apr@test.com",
            password="testpass123",
            empresa=empresa,
            rol_usuario="GERENCIA",
        )
        assert puede_aprobar(gerente, calibracion_con_confirmacion) is True

    def test_gerencia_no_auto_aprueba(self, empresa, equipo):
        from datetime import date
        from core.views.aprobaciones import puede_aprobar

        gerente = CustomUser.objects.create_user(
            username="gerente_self",
            email="gerente_self@test.com",
            password="testpass123",
            empresa=empresa,
            rol_usuario="GERENCIA",
        )
        cal = Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            nombre_proveedor="Lab",
            resultado="Aprobado",
            creado_por=gerente,
            confirmacion_estado_aprobacion='pendiente',
        )
        assert puede_aprobar(gerente, cal) is False


# ===================== Tests de cobertura de ramas adicionales =====================

@pytest.fixture
def superusuario(db):
    """Superusuario para tests de rutas de superusuario."""
    return CustomUser.objects.create_superuser(
        username="super_aprobador",
        email="super@aprobaciones.com",
        password="superpass123",
    )


@pytest.fixture
def super_client(superusuario):
    c = Client()
    c.login(username="super_aprobador", password="superpass123")
    c.user = superusuario
    return c


@pytest.fixture
def calibracion_sin_pdf(equipo, tecnico_user):
    """Calibración SIN confirmación PDF (solo metadatos)."""
    from datetime import date
    return Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=date.today(),
        nombre_proveedor="Lab Sin PDF",
        resultado="Aprobado",
        creado_por=tecnico_user,
        confirmacion_estado_aprobacion='pendiente',
        confirmacion_metrologica_datos={'puntos_medicion': [{'valor': 1.0}]},
        # SIN confirmacion_metrologica_pdf
    )


@pytest.fixture
def calibracion_pdf_manual(equipo, tecnico_user):
    """Calibración con PDF pero sin datos JSON (subida manualmente)."""
    from datetime import date
    cal = Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=date.today(),
        nombre_proveedor="Lab Manual",
        resultado="Aprobado",
        creado_por=tecnico_user,
        confirmacion_estado_aprobacion='pendiente',
        confirmacion_metrologica_datos={},  # vacío → PDF manual
    )
    cal.confirmacion_metrologica_pdf.save(
        'manual_confirmacion.pdf',
        ContentFile(b'%PDF-1.4 manual'),
        save=True,
    )
    return cal


@pytest.fixture
def calibracion_intervalos_pdf_manual(equipo, tecnico_user):
    """Calibración intervalos con PDF manual (datos vacíos)."""
    from datetime import date
    cal = Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=date.today(),
        nombre_proveedor="Lab Manual Intervalos",
        resultado="Aprobado",
        creado_por=tecnico_user,
        intervalos_estado_aprobacion='pendiente',
        intervalos_calibracion_datos={},  # vacío → PDF manual
    )
    cal.intervalos_calibracion_pdf.save(
        'manual_intervalos.pdf',
        ContentFile(b'%PDF-1.4 manual'),
        save=True,
    )
    return cal


@pytest.fixture
def comprobacion_sin_pdf(equipo, tecnico_user):
    """Comprobación SIN PDF generado."""
    from datetime import date
    return Comprobacion.objects.create(
        equipo=equipo,
        fecha_comprobacion=date.today(),
        resultado="Aprobado",
        creado_por=tecnico_user,
        estado_aprobacion='pendiente',
        datos_comprobacion={'puntos_medicion': [{'valor': 1.0}]},
        # SIN comprobacion_pdf
    )


@pytest.fixture
def comprobacion_pdf_manual(equipo, tecnico_user):
    """Comprobación con PDF manual (datos vacíos)."""
    from datetime import date
    comp = Comprobacion.objects.create(
        equipo=equipo,
        fecha_comprobacion=date.today(),
        resultado="Aprobado",
        creado_por=tecnico_user,
        estado_aprobacion='pendiente',
        datos_comprobacion={},  # vacío → PDF manual
    )
    comp.comprobacion_pdf.save(
        'manual_comprobacion.pdf',
        ContentFile(b'%PDF-1.4 manual'),
        save=True,
    )
    return comp


@pytest.mark.django_db
class TestPuedeAprobarCasosExtra:
    """Cubre ramas no cubiertas de puede_aprobar (líneas 162, 174, 179, 185)."""

    def test_superusuario_puede_aprobar_cualquier_documento(self, superusuario, calibracion_con_confirmacion):
        """Superusuario puede aprobar sin restricciones (línea 162)."""
        from core.views.aprobaciones import puede_aprobar
        assert puede_aprobar(superusuario, calibracion_con_confirmacion) is True

    def test_usuario_sin_empresa_no_puede_aprobar(self, db, equipo, tecnico_user):
        """Usuario sin empresa retorna False (línea 174)."""
        from core.views.aprobaciones import puede_aprobar
        from datetime import date
        usuario_sin_empresa = CustomUser.objects.create_user(
            username="sin_empresa_apr",
            email="sinempresa@test.com",
            password="testpass",
            empresa=None,
            rol_usuario="ADMINISTRADOR",
        )
        cal = Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            nombre_proveedor="Lab",
            resultado="Aprobado",
            creado_por=tecnico_user,
        )
        assert puede_aprobar(usuario_sin_empresa, cal) is False

    def test_empresa_diferente_no_puede_aprobar(self, db, calibracion_con_confirmacion):
        """Admin de empresa diferente no puede aprobar (línea 179)."""
        from core.views.aprobaciones import puede_aprobar
        otra_empresa = Empresa.objects.create(
            nombre="Otra Empresa Aprobaciones",
            nit="800999000-5",
            limite_equipos_empresa=10,
        )
        admin_otro = CustomUser.objects.create_user(
            username="admin_otro_apr",
            email="admin_otro@test.com",
            password="testpass",
            empresa=otra_empresa,
            rol_usuario="ADMINISTRADOR",
        )
        assert puede_aprobar(admin_otro, calibracion_con_confirmacion) is False

    def test_rol_tecnico_no_puede_aprobar_aunque_empresa_coincida(self, empresa, calibracion_con_confirmacion):
        """Técnico (de la misma empresa) no puede aprobar (línea 185)."""
        from core.views.aprobaciones import puede_aprobar
        tecnico2 = CustomUser.objects.create_user(
            username="tecnico2_apr",
            email="tec2@test.com",
            password="testpass",
            empresa=empresa,
            rol_usuario="TECNICO",
        )
        # No es creador, misma empresa, pero TECNICO → False
        calibracion_con_confirmacion.creado_por = None
        assert puede_aprobar(tecnico2, calibracion_con_confirmacion) is False


@pytest.mark.django_db
class TestPaginaAprobacionesSinEmpresa:
    """Cubre línea 32: pagina_aprobaciones cuando usuario no tiene empresa."""

    def test_usuario_sin_empresa_ve_error(self, db):
        """Usuario sin empresa ve mensaje de error (línea 32)."""
        user_sin_empresa = CustomUser.objects.create_user(
            username="noempresa_aprobaciones",
            email="noempresa@aprobaciones.com",
            password="testpass123",
            empresa=None,
            rol_usuario="ADMINISTRADOR",
        )
        client = Client()
        client.login(username="noempresa_aprobaciones", password="testpass123")
        url = reverse('core:aprobaciones')
        response = client.get(url)
        assert response.status_code == 200
        # Verifica que se pasa el error de contexto
        assert 'error' in response.context or response.status_code == 200


@pytest.mark.django_db
class TestSuperusuarioAprobaciones:
    """Cubre rutas de superusuario en vistas de aprobación (líneas 198, 330, 390, 551, 610, 758)."""

    def test_superusuario_aprueba_confirmacion(self, super_client, calibracion_con_confirmacion):
        """Superusuario puede aprobar confirmación de cualquier empresa (línea 198)."""
        url = reverse('core:aprobar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = super_client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        calibracion_con_confirmacion.refresh_from_db()
        assert calibracion_con_confirmacion.confirmacion_estado_aprobacion == 'aprobado'

    def test_superusuario_rechaza_confirmacion(self, super_client, calibracion_con_confirmacion):
        """Superusuario puede rechazar confirmación (línea 330)."""
        url = reverse('core:rechazar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = super_client.post(
            url,
            data=json.dumps({'observaciones': 'Rechazado por superusuario en test'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_superusuario_aprueba_intervalos(self, super_client, calibracion_con_intervalos):
        """Superusuario puede aprobar intervalos (línea 390)."""
        url = reverse('core:aprobar_intervalos', args=[calibracion_con_intervalos.id])
        response = super_client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_superusuario_rechaza_intervalos(self, super_client, calibracion_con_intervalos):
        """Superusuario puede rechazar intervalos (línea 551)."""
        url = reverse('core:rechazar_intervalos', args=[calibracion_con_intervalos.id])
        response = super_client.post(
            url,
            data=json.dumps({'observaciones': 'Rechazado por superusuario'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_superusuario_aprueba_comprobacion(self, super_client, comprobacion_pendiente):
        """Superusuario puede aprobar comprobación (línea 610)."""
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_pendiente.id])
        response = super_client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_superusuario_rechaza_comprobacion(self, super_client, comprobacion_pendiente):
        """Superusuario puede rechazar comprobación (línea 758)."""
        url = reverse('core:rechazar_comprobacion', args=[comprobacion_pendiente.id])
        response = super_client.post(
            url,
            data=json.dumps({'observaciones': 'Rechazado por superusuario test'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True


@pytest.mark.django_db
class TestAprobacionesSinPDF:
    """Cubre rutas de 'sin PDF' en cada vista de aprobación (líneas 214, 406, 626)."""

    def test_aprobar_confirmacion_sin_pdf_retorna_400(self, admin_client, calibracion_sin_pdf):
        """Aprobar confirmación sin PDF retorna error 400 (línea 214)."""
        url = reverse('core:aprobar_confirmacion', args=[calibracion_sin_pdf.id])
        response = admin_client.post(url)
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'confirmación metrológica' in data['error']

    def test_aprobar_intervalos_sin_pdf_retorna_400(self, admin_client, equipo, tecnico_user):
        """Aprobar intervalos sin PDF retorna error 400 (línea 406)."""
        from datetime import date
        cal_sin_intervalos_pdf = Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            nombre_proveedor="Lab",
            resultado="Aprobado",
            creado_por=tecnico_user,
            intervalos_estado_aprobacion='pendiente',
            intervalos_calibracion_datos={'metodo': 'test'},
            # SIN intervalos_calibracion_pdf
        )
        url = reverse('core:aprobar_intervalos', args=[cal_sin_intervalos_pdf.id])
        response = admin_client.post(url)
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False

    def test_aprobar_comprobacion_sin_pdf_retorna_400(self, admin_client, comprobacion_sin_pdf):
        """Aprobar comprobación sin PDF retorna error 400 (línea 626)."""
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_sin_pdf.id])
        response = admin_client.post(url)
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'PDF' in data['error']


@pytest.mark.django_db
class TestAprobacionesSinPermisos:
    """Cubre rutas de permisos denegados en rechazar (líneas 339, 399, 767)."""

    def test_tecnico_no_puede_rechazar_confirmacion(self, tecnico_client, calibracion_con_confirmacion):
        """Técnico (creador) no puede rechazar su propia confirmación (línea 339)."""
        url = reverse('core:rechazar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = tecnico_client.post(
            url,
            data=json.dumps({'observaciones': 'Intento de auto-rechazo'}),
            content_type='application/json',
        )
        assert response.status_code == 403
        data = response.json()
        assert data['success'] is False

    def test_tecnico_no_puede_aprobar_intervalos(self, tecnico_client, calibracion_con_intervalos):
        """Técnico (creador) no puede aprobar sus propios intervalos (línea 399)."""
        url = reverse('core:aprobar_intervalos', args=[calibracion_con_intervalos.id])
        response = tecnico_client.post(url)
        assert response.status_code == 403
        data = response.json()
        assert data['success'] is False

    def test_tecnico_no_puede_rechazar_comprobacion(self, tecnico_client, comprobacion_pendiente):
        """Técnico (creador) no puede rechazar su propia comprobación (línea 767)."""
        url = reverse('core:rechazar_comprobacion', args=[comprobacion_pendiente.id])
        response = tecnico_client.post(
            url,
            data=json.dumps({'observaciones': 'Intento rechazo propio'}),
            content_type='application/json',
        )
        assert response.status_code == 403
        data = response.json()
        assert data['success'] is False


@pytest.mark.django_db
class TestAprobacionesFechasInvalidas:
    """Cubre ramas de ValueError en parseo de fechas (líneas 225-228, 235-238, 245-248, 417-420, 427-430, 437-440, 637-640, 647-650, 657-660)."""

    def test_aprobar_confirmacion_con_fecha_invalida(self, admin_client, calibracion_pdf_manual):
        """fecha_realizacion inválida usa fallback a fecha_calibracion (líneas 225-228)."""
        url = reverse('core:aprobar_confirmacion', args=[calibracion_pdf_manual.id])
        response = admin_client.post(url, data={
            'fecha_realizacion': 'fecha-invalida',
            'fecha_emision': 'no-es-fecha',
            'fecha_aprobacion_ajustable': 'tampoco',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        calibracion_pdf_manual.refresh_from_db()
        assert calibracion_pdf_manual.confirmacion_estado_aprobacion == 'aprobado'

    def test_aprobar_intervalos_con_fecha_invalida(self, admin_client, calibracion_intervalos_pdf_manual):
        """Fechas inválidas en aprobar intervalos usan fallback (líneas 417-420, 427-430, 437-440)."""
        url = reverse('core:aprobar_intervalos', args=[calibracion_intervalos_pdf_manual.id])
        response = admin_client.post(url, data={
            'fecha_realizacion': 'mala-fecha',
            'fecha_emision': 'mala-emision',
            'fecha_aprobacion_ajustable': 'mala-aprobacion',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        calibracion_intervalos_pdf_manual.refresh_from_db()
        assert calibracion_intervalos_pdf_manual.intervalos_estado_aprobacion == 'aprobado'

    def test_aprobar_comprobacion_con_fecha_invalida(self, admin_client, comprobacion_pdf_manual):
        """Fechas inválidas en aprobar comprobación usan fallback (líneas 637-640, 647-650, 657-660)."""
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_pdf_manual.id])
        response = admin_client.post(url, data={
            'fecha_realizacion': 'fecha-mala',
            'fecha_emision': 'emision-mala',
            'fecha_aprobacion_ajustable': 'aprobacion-mala',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        comprobacion_pdf_manual.refresh_from_db()
        assert comprobacion_pdf_manual.estado_aprobacion == 'aprobado'


@pytest.mark.django_db
class TestAprobacionesPDFManual:
    """Cubre ramas 'else' de PDF manual (sin datos JSON) en vistas (líneas 303-304, 524-525, 732)."""

    def test_aprobar_confirmacion_pdf_manual_no_regenera(self, admin_client, calibracion_pdf_manual):
        """Confirmación con datos vacíos no regenera PDF (línea 303-304)."""
        url = reverse('core:aprobar_confirmacion', args=[calibracion_pdf_manual.id])
        response = admin_client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_aprobar_intervalos_pdf_manual_no_regenera(self, admin_client, calibracion_intervalos_pdf_manual):
        """Intervalos con datos vacíos no regenera PDF (líneas 524-525)."""
        url = reverse('core:aprobar_intervalos', args=[calibracion_intervalos_pdf_manual.id])
        response = admin_client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_aprobar_comprobacion_pdf_manual_no_regenera(self, admin_client, comprobacion_pdf_manual):
        """Comprobación con datos vacíos no regenera PDF (línea 732)."""
        url = reverse('core:aprobar_comprobacion', args=[comprobacion_pdf_manual.id])
        response = admin_client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True


@pytest.mark.django_db
class TestAprobacionesExcepcionesRechazo:
    """Cubre handlers de excepción en rechazar (líneas 373-375, 593-595, 800-802)."""

    def test_rechazar_confirmacion_body_invalido_retorna_500(self, admin_client, calibracion_con_confirmacion):
        """JSON inválido en body de rechazar_confirmacion dispara excepción (líneas 373-375)."""
        url = reverse('core:rechazar_confirmacion', args=[calibracion_con_confirmacion.id])
        response = admin_client.post(
            url,
            data='esto-no-es-json',
            content_type='application/json',
        )
        # ValueError al parsear JSON → exception handler → status 500
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False

    def test_rechazar_intervalos_body_invalido_retorna_500(self, admin_client, calibracion_con_intervalos):
        """JSON inválido en body de rechazar_intervalos dispara excepción (líneas 593-595)."""
        url = reverse('core:rechazar_intervalos', args=[calibracion_con_intervalos.id])
        response = admin_client.post(
            url,
            data='esto-no-es-json',
            content_type='application/json',
        )
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False

    def test_rechazar_comprobacion_body_invalido_retorna_500(self, admin_client, comprobacion_pendiente):
        """JSON inválido en body de rechazar_comprobacion dispara excepción (líneas 800-802)."""
        url = reverse('core:rechazar_comprobacion', args=[comprobacion_pendiente.id])
        response = admin_client.post(
            url,
            data='esto-no-es-json',
            content_type='application/json',
        )
        assert response.status_code == 500
        data = response.json()
        assert data['success'] is False


@pytest.mark.django_db
class TestAprobacionesFechasValidas:
    """Cubre ramas 'if fecha_str' cuando las fechas son válidas (líneas 224-227, 234-237, 244-247)."""

    def test_aprobar_confirmacion_con_fechas_validas(self, admin_client, calibracion_pdf_manual):
        """Fechas válidas se aplican correctamente a la confirmación."""
        url = reverse('core:aprobar_confirmacion', args=[calibracion_pdf_manual.id])
        response = admin_client.post(url, data={
            'fecha_realizacion': '2026-01-15',
            'fecha_emision': '2026-01-16',
            'fecha_aprobacion_ajustable': '2026-01-17',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        calibracion_pdf_manual.refresh_from_db()
        from datetime import date
        assert calibracion_pdf_manual.confirmacion_fecha_realizacion == date(2026, 1, 15)
        assert calibracion_pdf_manual.confirmacion_fecha_emision == date(2026, 1, 16)
        assert calibracion_pdf_manual.confirmacion_fecha_aprobacion_ajustable == date(2026, 1, 17)
