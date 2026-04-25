"""
Tests para dashboard_prestamos — secciones colapsables, chips, agrupación por prestatario.
Cubre: acceso, contexto, agrupación, vencidos, equipos disponibles, multi-tenant.
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.utils import timezone

from core.models import PrestamoEquipo, Equipo


# ── Helpers ──────────────────────────────────────────────────────────────────

def _add_perm(user, codename):
    perm = Permission.objects.get(codename=codename)
    user.user_permissions.add(perm)


def _crear_prestamo(equipo, empresa, user, nombre='Juan Pérez', dias_vence=7, estado='ACTIVO'):
    fecha_dev = date.today() + timedelta(days=dias_vence)
    return PrestamoEquipo.objects.create(
        equipo=equipo,
        empresa=empresa,
        nombre_prestatario=nombre,
        estado_prestamo=estado,
        prestado_por=user,
        fecha_devolucion_programada=fecha_dev,
    )


# ── Acceso y permisos ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDashboardAcceso:

    def test_requiere_login(self, client):
        url = reverse('core:dashboard_prestamos')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_requiere_permiso_view_prestamo(self, authenticated_client):
        """Sin permiso can_view_prestamo → 403."""
        url = reverse('core:dashboard_prestamos')
        response = authenticated_client.get(url)
        assert response.status_code == 403

    def test_acceso_con_permiso(self, authenticated_client):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        url = reverse('core:dashboard_prestamos')
        response = authenticated_client.get(url)
        assert response.status_code == 200

    def test_usa_template_correcto(self, authenticated_client):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        response = authenticated_client.get(reverse('core:dashboard_prestamos'))
        assert 'core/prestamos/dashboard.html' in [t.name for t in response.templates]


# ── Contexto básico ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDashboardContexto:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_sin_prestamos_contexto_vacios(self, authenticated_client):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        r = authenticated_client.get(self.url)
        assert r.status_code == 200
        assert r.context['total_prestamos_activos'] == 0
        assert r.context['total_prestatarios'] == 0
        assert r.context['prestamos_vencidos'] == 0

    def test_contexto_con_prestamo_activo(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user, 'Ana López')

        r = authenticated_client.get(self.url)
        assert r.context['total_prestamos_activos'] == 1
        assert r.context['total_prestatarios'] == 1
        assert r.context['prestamos_vencidos'] == 0

    def test_claves_de_contexto_presentes(self, authenticated_client):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        r = authenticated_client.get(self.url)
        claves = [
            'prestatarios', 'total_prestamos_activos', 'total_prestatarios',
            'prestamos_vencidos', 'devoluciones_proximas', 'equipos_disponibles',
            'equipos_prestados', 'familias_disponibles',
        ]
        for clave in claves:
            assert clave in r.context, f"Falta '{clave}' en el contexto"


# ── Agrupación por prestatario ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestAgrupacionPrestatario:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_dos_equipos_mismo_prestatario_una_fila(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        eq1 = equipo_factory(empresa=user.empresa)
        eq2 = equipo_factory(empresa=user.empresa)
        _crear_prestamo(eq1, user.empresa, user, 'Carlos Ruiz')
        _crear_prestamo(eq2, user.empresa, user, 'Carlos Ruiz')

        r = authenticated_client.get(self.url)
        assert r.context['total_prestatarios'] == 1
        assert r.context['total_prestamos_activos'] == 2
        prestatarios = list(r.context['prestatarios'])
        assert len(prestatarios) == 1
        assert len(prestatarios[0]['prestamos']) == 2

    def test_dos_prestatarios_distintos_dos_filas(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        eq1 = equipo_factory(empresa=user.empresa)
        eq2 = equipo_factory(empresa=user.empresa)
        _crear_prestamo(eq1, user.empresa, user, 'Ana López')
        _crear_prestamo(eq2, user.empresa, user, 'Luis Torres')

        r = authenticated_client.get(self.url)
        assert r.context['total_prestatarios'] == 2
        nombres = {p['nombre'] for p in r.context['prestatarios']}
        assert 'Ana López' in nombres
        assert 'Luis Torres' in nombres


# ── Préstamos vencidos ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPrestamosVencidos:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_prestamo_vencido_contado(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user, dias_vence=-3)  # Vencido hace 3 días

        r = authenticated_client.get(self.url)
        assert r.context['prestamos_vencidos'] == 1

    def test_prestamo_no_vencido_no_contado(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user, dias_vence=10)  # Vence en 10 días

        r = authenticated_client.get(self.url)
        assert r.context['prestamos_vencidos'] == 0

    def test_prestatario_con_equipos_vencidos_flag(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        eq1 = equipo_factory(empresa=user.empresa)
        eq2 = equipo_factory(empresa=user.empresa)
        _crear_prestamo(eq1, user.empresa, user, 'Pedro Mora', dias_vence=-1)
        _crear_prestamo(eq2, user.empresa, user, 'Pedro Mora', dias_vence=5)

        r = authenticated_client.get(self.url)
        prestatario = list(r.context['prestatarios'])[0]
        assert prestatario['equipos_vencidos'] == 1
        assert prestatario['cantidad_equipos'] == 2

    def test_prestamos_devueltos_no_aparecen(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user, estado='DEVUELTO')

        r = authenticated_client.get(self.url)
        assert r.context['total_prestamos_activos'] == 0


# ── Equipos disponibles y familias ────────────────────────────────────────────

@pytest.mark.django_db
class TestEquiposDisponibles:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_equipo_sin_prestamo_aparece_disponible(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo_factory(empresa=user.empresa, estado='Activo')

        r = authenticated_client.get(self.url)
        assert r.context['equipos_disponibles'] >= 1

    def test_equipo_prestado_no_aparece_disponible(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa, estado='Activo')
        _crear_prestamo(equipo, user.empresa, user)

        r = authenticated_client.get(self.url)
        # El equipo está prestado, no debe estar en familias_disponibles
        codigos = [
            eq.codigo_interno
            for equipos in r.context['familias_disponibles'].values()
            for eq in equipos
        ]
        assert equipo.codigo_interno not in codigos

    def test_equipos_agrupados_por_tipo(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo_factory(empresa=user.empresa, estado='Activo', tipo_equipo='Termómetro')
        equipo_factory(empresa=user.empresa, estado='Activo', tipo_equipo='Termómetro')
        equipo_factory(empresa=user.empresa, estado='Activo', tipo_equipo='Balanza')

        r = authenticated_client.get(self.url)
        familias = r.context['familias_disponibles']
        assert 'Termómetro' in familias
        assert 'Balanza' in familias
        assert len(familias['Termómetro']) == 2
        assert len(familias['Balanza']) == 1

    def test_equipo_inactivo_no_disponible(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo_factory(empresa=user.empresa, estado='Inactivo')

        r = authenticated_client.get(self.url)
        # Los inactivos no deben aparecer en ninguna familia
        total_en_familias = sum(
            len(eqs) for eqs in r.context['familias_disponibles'].values()
        )
        assert total_en_familias == 0


# ── Aislamiento multi-tenant ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestMultiTenantDashboard:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_no_ve_prestamos_de_otra_empresa(
        self, authenticated_client, equipo_factory, user_factory, empresa_factory
    ):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')

        # Crear empresa y usuario externos
        otra_empresa = empresa_factory()
        otro_user = user_factory(empresa=otra_empresa)
        equipo_otro = equipo_factory(empresa=otra_empresa)
        _crear_prestamo(equipo_otro, otra_empresa, otro_user, 'Externo Corp')

        r = authenticated_client.get(self.url)
        nombres = {p['nombre'] for p in r.context['prestatarios']}
        assert 'Externo Corp' not in nombres
        assert r.context['total_prestamos_activos'] == 0

    def test_no_ve_equipos_disponibles_de_otra_empresa(
        self, authenticated_client, equipo_factory, empresa_factory
    ):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')

        otra_empresa = empresa_factory()
        equipo_externo = equipo_factory(empresa=otra_empresa, estado='Activo')

        r = authenticated_client.get(self.url)
        codigos = [
            eq.codigo_interno
            for equipos in r.context['familias_disponibles'].values()
            for eq in equipos
        ]
        assert equipo_externo.codigo_interno not in codigos


# ── Devoluciones próximas ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDevolucionesProximas:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_devolucion_en_7_dias_contada(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user, dias_vence=5)  # En 5 días

        r = authenticated_client.get(self.url)
        assert r.context['devoluciones_proximas'] == 1

    def test_devolucion_en_30_dias_no_contada(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user, dias_vence=30)

        r = authenticated_client.get(self.url)
        assert r.context['devoluciones_proximas'] == 0


# ── Contenido del template (chips y estructura) ───────────────────────────────

@pytest.mark.django_db
class TestContenidoTemplate:

    def setup_method(self):
        self.url = reverse('core:dashboard_prestamos')

    def test_chips_contienen_codigo_interno(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa, codigo_interno='CM-99')
        _crear_prestamo(equipo, user.empresa, user)

        r = authenticated_client.get(self.url)
        assert b'CM-99' in r.content

    def test_template_renderiza_sin_errores_sin_datos(self, authenticated_client):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        r = authenticated_client.get(self.url)
        assert r.status_code == 200
        assert b'Panel de Pr' in r.content  # "Panel de Préstamos"

    def test_template_contiene_secciones_colapsables(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user)

        r = authenticated_client.get(self.url)
        assert b'toggleSection' in r.content
        assert b'sec-inspectores' in r.content

    def test_filtro_busqueda_presente_en_html(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        _crear_prestamo(equipo, user.empresa, user)

        r = authenticated_client.get(self.url)
        assert b'filtro-inspectores' in r.content

    def test_enlace_a_detalle_prestamo_en_chips(self, authenticated_client, equipo_factory):
        user = authenticated_client.user
        _add_perm(user, 'can_view_prestamo')
        equipo = equipo_factory(empresa=user.empresa)
        prestamo = _crear_prestamo(equipo, user.empresa, user)

        r = authenticated_client.get(self.url)
        url_detalle = reverse('core:detalle_prestamo', args=[prestamo.pk])
        assert url_detalle.encode() in r.content
