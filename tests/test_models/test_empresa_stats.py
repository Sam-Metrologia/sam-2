"""
Tests para el método recalcular_stats_dashboard() del modelo Empresa.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion


@pytest.mark.django_db
@pytest.mark.unit
class TestEmpresaStatsRecalcular:
    """Tests del método recalcular_stats_dashboard() en Empresa."""

    def _empresa(self, empresa_factory):
        return empresa_factory()

    def _equipo(self, empresa, estado='Activo', **kwargs):
        return Equipo.objects.create(
            empresa=empresa,
            codigo_interno=f'EQ-{Equipo.objects.count() + 1:04d}',
            nombre='Equipo Test',
            tipo_equipo='Equipo de Medición',
            estado=estado,
            **kwargs,
        )

    # ──────────────────────────────────────────────────────────────────────────

    def test_empresa_sin_equipos_stats_en_cero(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        empresa.recalcular_stats_dashboard()

        assert empresa.stats_total_equipos == 0
        assert empresa.stats_equipos_activos == 0
        assert empresa.stats_calibraciones_vencidas == 0
        assert empresa.stats_compliance_calibracion == {'realizadas': 0, 'no_cumplidas': 0, 'pendientes': 0}

    def test_conteos_basicos_correctos(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        self._equipo(empresa, estado='Activo')
        self._equipo(empresa, estado='Activo')
        self._equipo(empresa, estado='Inactivo')
        self._equipo(empresa, estado='De Baja')

        empresa.recalcular_stats_dashboard()

        assert empresa.stats_total_equipos == 4
        assert empresa.stats_equipos_activos == 2
        assert empresa.stats_equipos_inactivos == 1
        assert empresa.stats_equipos_de_baja == 1

    def test_calibraciones_vencidas(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        ayer = date.today() - timedelta(days=1)
        # Crear equipo y luego establecer la fecha directamente (save() recalcula proxima_calibracion)
        eq = self._equipo(empresa, estado='Activo')
        Equipo.objects.filter(pk=eq.pk).update(proxima_calibracion=ayer)
        self._equipo(empresa, estado='Activo')  # sin próxima calibración

        empresa.recalcular_stats_dashboard()

        assert empresa.stats_calibraciones_vencidas == 1

    def test_calibraciones_proximas_30_dias(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        en_15_dias = date.today() + timedelta(days=15)
        en_60_dias = date.today() + timedelta(days=60)
        eq1 = self._equipo(empresa, estado='Activo')
        eq2 = self._equipo(empresa, estado='Activo')
        Equipo.objects.filter(pk=eq1.pk).update(proxima_calibracion=en_15_dias)
        Equipo.objects.filter(pk=eq2.pk).update(proxima_calibracion=en_60_dias)  # fuera del rango

        empresa.recalcular_stats_dashboard()

        assert empresa.stats_calibraciones_proximas == 1

    def test_equipos_de_baja_excluidos_de_actividades(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        ayer = date.today() - timedelta(days=1)
        # Equipo de baja con calibración vencida — NO debe contarse
        eq1 = self._equipo(empresa, estado='De Baja')
        Equipo.objects.filter(pk=eq1.pk).update(proxima_calibracion=ayer)
        # Equipo inactivo con calibración vencida — NO debe contarse
        eq2 = self._equipo(empresa, estado='Inactivo')
        Equipo.objects.filter(pk=eq2.pk).update(proxima_calibracion=ayer)

        empresa.recalcular_stats_dashboard()

        assert empresa.stats_calibraciones_vencidas == 0

    def test_compliance_calibracion_json(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        empresa.recalcular_stats_dashboard()

        c = empresa.stats_compliance_calibracion
        assert 'realizadas' in c
        assert 'no_cumplidas' in c
        assert 'pendientes' in c

    def test_compliance_mantenimiento_json(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        empresa.recalcular_stats_dashboard()

        c = empresa.stats_compliance_mantenimiento
        assert isinstance(c, dict)
        assert 'realizadas' in c

    def test_compliance_comprobacion_json(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        empresa.recalcular_stats_dashboard()

        c = empresa.stats_compliance_comprobacion
        assert isinstance(c, dict)
        assert 'pendientes' in c

    def test_timestamp_se_actualiza(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        assert empresa.stats_ultima_actualizacion is None

        empresa.recalcular_stats_dashboard()

        assert empresa.stats_ultima_actualizacion is not None
        # Debe ser reciente (últimos 5 segundos)
        delta = timezone.now() - empresa.stats_ultima_actualizacion
        assert delta.total_seconds() < 5

    def test_fecha_calculo_es_hoy(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        empresa.recalcular_stats_dashboard()

        assert empresa.stats_fecha_calculo == date.today()

    def test_idempotente_llamar_dos_veces(self, empresa_factory):
        empresa = self._empresa(empresa_factory)
        self._equipo(empresa, estado='Activo')

        empresa.recalcular_stats_dashboard()
        ts_1 = empresa.stats_total_equipos
        empresa.recalcular_stats_dashboard()
        ts_2 = empresa.stats_total_equipos

        assert ts_1 == ts_2 == 1
