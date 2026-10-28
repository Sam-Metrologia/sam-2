"""
Regresión: campos de la hoja de vida PDF que salían como "N/A" aunque estaban llenos.

1. EMP con texto ("5%", "± 1 mm") salía N/A por un floatformat sobre un CharField.
2. Proveedor de calibración/mantenimiento/comprobación elegido de la lista (FK)
   salía N/A porque la plantilla solo leía nombre_proveedor (texto libre).
"""
import pytest
from django.template.loader import render_to_string

from core.models import Proveedor
from tests.factories import (
    EquipoFactory, CalibracionFactory, MantenimientoFactory, ComprobacionFactory,
)


def _render_hoja_vida(equipo):
    return render_to_string('core/hoja_vida_pdf.html', {
        'equipo': equipo,
        'calibraciones': list(equipo.calibraciones.all()),
        'mantenimientos': list(equipo.mantenimientos.all()),
        'comprobaciones': list(equipo.comprobaciones.all()),
    })


@pytest.mark.django_db
class TestHojaVidaCampos:

    @pytest.mark.parametrize('emp', ['5%', '± 1 mm', '0,5 mm', '0.03'])
    def test_emp_texto_se_muestra_tal_cual(self, emp):
        equipo = EquipoFactory(error_maximo_permisible=emp)
        html = _render_hoja_vida(equipo)
        assert f'<strong>Error Máximo Permisible:</strong> {emp}' in html

    def test_emp_vacio_muestra_na(self):
        equipo = EquipoFactory(error_maximo_permisible='')
        html = _render_hoja_vida(equipo)
        assert '<strong>Error Máximo Permisible:</strong> N/A' in html

    def test_proveedor_de_lista_aparece_en_historiales(self):
        equipo = EquipoFactory()
        prov = Proveedor.objects.create(
            empresa=equipo.empresa, nombre_empresa='LAB LISTA SAS', tipo_servicio='Otro',
        )
        CalibracionFactory(equipo=equipo, proveedor=prov, nombre_proveedor='')
        MantenimientoFactory(equipo=equipo, proveedor=prov, nombre_proveedor=None)
        ComprobacionFactory(equipo=equipo, proveedor=prov, nombre_proveedor='')

        html = _render_hoja_vida(equipo)
        assert html.count('LAB LISTA SAS') == 3

    def test_proveedor_texto_libre_tiene_prioridad(self):
        equipo = EquipoFactory()
        prov = Proveedor.objects.create(
            empresa=equipo.empresa, nombre_empresa='LAB LISTA SAS', tipo_servicio='Otro',
        )
        cal = CalibracionFactory(equipo=equipo, proveedor=prov, nombre_proveedor='PINZUAR SAS')
        assert cal.proveedor_display == 'PINZUAR SAS'

    def test_sin_proveedor_devuelve_vacio(self):
        cal = CalibracionFactory(proveedor=None, nombre_proveedor='')
        assert cal.proveedor_display == ''
