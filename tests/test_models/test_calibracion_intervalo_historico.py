"""
Cada calibración conserva su propio intervalo: ajustar el intervalo del equipo
no debe cambiar la próxima fecha que muestran las calibraciones anteriores.
"""
from datetime import date
from decimal import Decimal

import pytest

from core.models import Calibracion
from tests.factories import CalibracionFactory, EquipoFactory


@pytest.mark.django_db
class TestIntervaloHistoricoCalibracion:

    def _ajustar_intervalo(self, equipo, meses):
        equipo.frecuencia_calibracion_meses = Decimal(meses)
        equipo.save()

    def test_calibraciones_anteriores_conservan_su_intervalo(self):
        equipo = EquipoFactory(frecuencia_calibracion_meses=Decimal('12'))

        cal_2022 = CalibracionFactory(equipo=equipo, fecha_calibracion=date(2022, 12, 3))
        cal_2023 = CalibracionFactory(equipo=equipo, fecha_calibracion=date(2023, 12, 3))
        self._ajustar_intervalo(equipo, '36')
        cal_2026 = CalibracionFactory(equipo=equipo, fecha_calibracion=date(2026, 12, 3))
        self._ajustar_intervalo(equipo, '60')

        cal_2022.refresh_from_db()
        cal_2023.refresh_from_db()
        cal_2026.refresh_from_db()

        assert cal_2022.proxima_actividad_para_este_registro == date(2023, 12, 3)
        assert cal_2023.proxima_actividad_para_este_registro == date(2026, 12, 3)
        assert cal_2026.proxima_actividad_para_este_registro == date(2031, 12, 3)

        equipo.refresh_from_db()
        assert equipo.proxima_calibracion == date(2031, 12, 3)

    def test_calibracion_nueva_toma_intervalo_vigente_del_equipo(self):
        equipo = EquipoFactory(frecuencia_calibracion_meses=Decimal('24'))
        cal = CalibracionFactory(equipo=equipo, fecha_calibracion=date(2025, 1, 10))
        assert cal.frecuencia_calibracion_meses == Decimal('24')

    def test_sin_intervalo_guardado_usa_el_del_equipo(self):
        equipo = EquipoFactory(frecuencia_calibracion_meses=Decimal('12'))
        cal = CalibracionFactory(equipo=equipo, fecha_calibracion=date(2025, 1, 10))
        Calibracion.objects.filter(pk=cal.pk).update(frecuencia_calibracion_meses=None)
        cal.refresh_from_db()
        assert cal.proxima_actividad_para_este_registro == date(2026, 1, 10)
