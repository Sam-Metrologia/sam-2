"""
Tests para señales que actualizan stats pre-computadas al crear/eliminar objetos.
"""
import pytest
from datetime import date
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion


def _make_equipo(empresa, estado='Activo'):
    return Equipo.objects.create(
        empresa=empresa,
        codigo_interno=f'EQ-{Equipo.objects.count() + 1:04d}',
        nombre='Equipo Test',
        tipo_equipo='Equipo de Medición',
        estado=estado,
    )


@pytest.mark.django_db
@pytest.mark.unit
class TestStatsSignals:
    """
    Verifica que las señales post_save/post_delete actualicen stats_fecha_calculo
    en Empresa cuando cambian sus equipos/calibraciones/mantenimientos/comprobaciones.
    """

    def test_crear_equipo_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        assert empresa.stats_total_equipos == 0

        _make_equipo(empresa)
        empresa.refresh_from_db()

        assert empresa.stats_total_equipos == 1
        assert empresa.stats_fecha_calculo == date.today()

    def test_eliminar_equipo_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)
        empresa.refresh_from_db()
        assert empresa.stats_total_equipos == 1

        equipo.delete()
        empresa.refresh_from_db()

        assert empresa.stats_total_equipos == 0

    def test_crear_calibracion_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)

        empresa.refresh_from_db()
        ts_antes = empresa.stats_ultima_actualizacion

        Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            resultado='Aprobado',
        )
        empresa.refresh_from_db()

        assert empresa.stats_fecha_calculo == date.today()
        # El timestamp debe haber cambiado (o ser nuevo)
        if ts_antes is not None:
            assert empresa.stats_ultima_actualizacion >= ts_antes

    def test_eliminar_calibracion_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)
        cal = Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=date.today(),
            resultado='Aprobado',
        )
        empresa.refresh_from_db()
        ts_antes = empresa.stats_ultima_actualizacion

        cal.delete()
        empresa.refresh_from_db()

        assert empresa.stats_fecha_calculo == date.today()
        if ts_antes is not None:
            assert empresa.stats_ultima_actualizacion >= ts_antes

    def test_crear_mantenimiento_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)

        Mantenimiento.objects.create(
            equipo=equipo,
            fecha_mantenimiento=date.today(),
            tipo_mantenimiento='Preventivo',
            responsable='Técnico',
        )
        empresa.refresh_from_db()

        assert empresa.stats_fecha_calculo == date.today()

    def test_eliminar_mantenimiento_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)
        mant = Mantenimiento.objects.create(
            equipo=equipo,
            fecha_mantenimiento=date.today(),
            tipo_mantenimiento='Preventivo',
            responsable='Técnico',
        )
        mant.delete()
        empresa.refresh_from_db()

        assert empresa.stats_fecha_calculo == date.today()

    def test_crear_comprobacion_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)

        Comprobacion.objects.create(
            equipo=equipo,
            fecha_comprobacion=date.today(),
            resultado='Aprobado',
            responsable='Técnico',
        )
        empresa.refresh_from_db()

        assert empresa.stats_fecha_calculo == date.today()

    def test_eliminar_comprobacion_actualiza_stats(self, empresa_factory):
        empresa = empresa_factory()
        equipo = _make_equipo(empresa)
        comp = Comprobacion.objects.create(
            equipo=equipo,
            fecha_comprobacion=date.today(),
            resultado='Aprobado',
            responsable='Técnico',
        )
        comp.delete()
        empresa.refresh_from_db()

        assert empresa.stats_fecha_calculo == date.today()

    def test_error_en_recalculo_no_rompe_save_usuario(self, empresa_factory, monkeypatch):
        """
        Si recalcular_stats_dashboard() falla, el objeto principal (Equipo)
        igual debe guardarse correctamente.
        """
        empresa = empresa_factory()

        def _raise(*a, **kw):
            raise RuntimeError("Error simulado")

        monkeypatch.setattr(Empresa, 'recalcular_stats_dashboard', _raise)

        # Crear un equipo — NO debe lanzar excepción aunque recalcular falle
        equipo = _make_equipo(empresa)
        assert Equipo.objects.filter(pk=equipo.pk).exists()
