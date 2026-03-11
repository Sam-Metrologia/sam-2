"""
Tests para verificar que el dashboard usa las stats pre-computadas correctamente.
"""
import pytest
from datetime import date, timedelta
from django.test import Client
from django.urls import reverse
from core.models import Empresa, Equipo


def _make_equipo(empresa, estado='Activo', **kwargs):
    return Equipo.objects.create(
        empresa=empresa,
        codigo_interno=f'EQ-{Equipo.objects.count() + 1:04d}',
        nombre='Equipo Test',
        tipo_equipo='Equipo de Medición',
        estado=estado,
        **kwargs,
    )


def _login_user(empresa, rol='Administrador'):
    from tests.factories import UserFactory
    user = UserFactory(empresa=empresa, is_superuser=False, rol_usuario=rol)
    client = Client()
    client.force_login(user)
    return client, user


@pytest.mark.django_db
class TestDashboardUsaStats:

    def test_dashboard_usa_stats_cuando_son_frescos(self, empresa_factory, db):
        """Cuando stats_fecha_calculo == today, el dashboard usa los stats pre-computados."""
        empresa = empresa_factory()
        empresa.stats_total_equipos = 42
        empresa.stats_equipos_activos = 42
        empresa.stats_equipos_inactivos = 0
        empresa.stats_equipos_de_baja = 0
        empresa.stats_calibraciones_vencidas = 5
        empresa.stats_calibraciones_proximas = 3
        empresa.stats_mantenimientos_vencidos = 1
        empresa.stats_mantenimientos_proximos = 2
        empresa.stats_comprobaciones_vencidas = 0
        empresa.stats_comprobaciones_proximas = 0
        empresa.stats_compliance_calibracion = {'realizadas': 10, 'no_cumplidas': 2, 'pendientes': 3}
        empresa.stats_compliance_mantenimiento = {'realizadas': 5, 'no_cumplidas': 1, 'pendientes': 2}
        empresa.stats_compliance_comprobacion = {'realizadas': 0, 'no_cumplidas': 0, 'pendientes': 0}
        empresa.stats_fecha_calculo = date.today()
        empresa.save(update_fields=[
            'stats_total_equipos', 'stats_equipos_activos', 'stats_equipos_inactivos',
            'stats_equipos_de_baja', 'stats_calibraciones_vencidas', 'stats_calibraciones_proximas',
            'stats_mantenimientos_vencidos', 'stats_mantenimientos_proximos',
            'stats_comprobaciones_vencidas', 'stats_comprobaciones_proximas',
            'stats_compliance_calibracion', 'stats_compliance_mantenimiento',
            'stats_compliance_comprobacion', 'stats_fecha_calculo',
        ])

        client, _ = _login_user(empresa)
        response = client.get(reverse('core:dashboard'))

        assert response.status_code == 200
        assert response.context['total_equipos'] == 42
        assert response.context['calibraciones_vencidas'] == 5

    def test_dashboard_usa_calculo_cuando_stats_son_de_ayer(self, empresa_factory, db):
        """Cuando stats_fecha_calculo es de ayer (distinto de today), usa cálculo normal."""
        empresa = empresa_factory()
        ayer = date.today() - timedelta(days=1)
        # Poner un valor falso para saber si usa stats o recalcula
        Empresa.objects.filter(pk=empresa.pk).update(
            stats_total_equipos=9999,
            stats_fecha_calculo=ayer,
        )

        _make_equipo(empresa, estado='Activo')

        client, _ = _login_user(empresa)
        response = client.get(reverse('core:dashboard'))

        assert response.status_code == 200
        # Debe usar el cálculo real (1 equipo), no el stats falso (9999)
        assert response.context['total_equipos'] == 1

    def test_dashboard_usa_calculo_cuando_stats_son_none(self, empresa_factory, db):
        """Cuando stats_fecha_calculo es None (nunca calculado), usa cálculo normal."""
        empresa = empresa_factory()
        assert empresa.stats_fecha_calculo is None

        _make_equipo(empresa, estado='Activo')
        _make_equipo(empresa, estado='Activo')

        client, _ = _login_user(empresa)
        response = client.get(reverse('core:dashboard'))

        assert response.status_code == 200
        assert response.context['total_equipos'] == 2

    def test_superusuario_usa_calculo_original(self, empresa_factory, db):
        """El superusuario siempre usa el cálculo completo, nunca las stats de empresa."""
        empresa = empresa_factory()
        # Poner stats falsos
        Empresa.objects.filter(pk=empresa.pk).update(
            stats_total_equipos=8888,
            stats_fecha_calculo=date.today(),
        )

        from tests.factories import UserFactory
        superuser = UserFactory(is_superuser=True, is_staff=True, empresa=empresa)
        client = Client()
        client.force_login(superuser)

        response = client.get(reverse('core:dashboard'))

        assert response.status_code == 200
        # Superusuario recalcula — tiene 0 equipos reales (los stats decían 8888)
        assert response.context.get('total_equipos', 0) != 8888

    def test_stats_coinciden_con_calculo_fresco(self, empresa_factory, db):
        """
        Los stats pre-computados deben coincidir con el cálculo original.
        Este test detecta discrepancias silenciosas.
        """
        empresa = empresa_factory()
        _make_equipo(empresa, estado='Activo')
        _make_equipo(empresa, estado='Inactivo')

        # Calcular stats
        empresa.recalcular_stats_dashboard()
        empresa.refresh_from_db()

        # Verificar que coinciden con los valores reales
        equipos_reales = Equipo.objects.filter(empresa=empresa)
        total_real = equipos_reales.count()
        activos_real = equipos_reales.filter(estado='Activo').count()

        assert empresa.stats_total_equipos == total_real
        assert empresa.stats_equipos_activos == activos_real
