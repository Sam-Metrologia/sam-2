"""
Tests para el comando de gestión recalcular_stats_empresas.
"""
import pytest
from io import StringIO
from django.core.management import call_command
from core.models import Empresa, Equipo


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
class TestRecalcularStatsCommand:

    def test_recalcula_todas_las_empresas(self, empresa_factory):
        empresa1 = empresa_factory()
        empresa2 = empresa_factory()
        _make_equipo(empresa1)
        _make_equipo(empresa1)
        _make_equipo(empresa2)

        # Llamar al comando (ignora las señales que ya actualizaron)
        stdout = StringIO()
        call_command('recalcular_stats_empresas', stdout=stdout)

        empresa1.refresh_from_db()
        empresa2.refresh_from_db()
        assert empresa1.stats_total_equipos == 2
        assert empresa2.stats_total_equipos == 1

    def test_recalcula_empresa_especifica(self, empresa_factory):
        empresa1 = empresa_factory()
        empresa2 = empresa_factory()
        _make_equipo(empresa1)
        _make_equipo(empresa2)

        # Resetear stats de empresa1 para verificar que el comando las recalcula
        Empresa.objects.filter(pk=empresa1.pk).update(stats_total_equipos=99)

        stdout = StringIO()
        call_command('recalcular_stats_empresas', empresa_id=empresa1.pk, stdout=stdout)

        empresa1.refresh_from_db()
        assert empresa1.stats_total_equipos == 1  # recalculado correctamente

    def test_dry_run_no_guarda(self, empresa_factory):
        empresa = empresa_factory()
        _make_equipo(empresa)

        # Forzar un valor distinto antes del dry-run
        Empresa.objects.filter(pk=empresa.pk).update(stats_total_equipos=999)

        stdout = StringIO()
        call_command('recalcular_stats_empresas', dry_run=True, stdout=stdout)

        empresa.refresh_from_db()
        # dry-run no debe haber cambiado el valor
        assert empresa.stats_total_equipos == 999

    def test_output_contiene_nombre_empresa(self, empresa_factory):
        empresa = empresa_factory(nombre='Empresa Especial SA')

        stdout = StringIO()
        call_command('recalcular_stats_empresas', stdout=stdout)

        output = stdout.getvalue()
        assert 'Empresa Especial SA' in output

    def test_maneja_error_sin_explotar(self, empresa_factory, monkeypatch):
        empresa = empresa_factory()

        def _raise(self):
            raise RuntimeError("Error simulado en test")

        monkeypatch.setattr(Empresa, 'recalcular_stats_dashboard', _raise)

        stderr = StringIO()
        stdout = StringIO()
        # No debe lanzar excepción
        call_command('recalcular_stats_empresas', stdout=stdout, stderr=stderr)

        error_output = stderr.getvalue()
        assert 'Error simulado' in error_output or 'errores' in stdout.getvalue()
