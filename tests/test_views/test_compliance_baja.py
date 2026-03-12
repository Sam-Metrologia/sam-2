"""
Tests para cumplimiento anual con equipos dados de baja / inactivos.

Verifica que las tortas de cumplimiento incluyen equipos De Baja/Inactivos
del año actual, con la lógica correcta según norma metrológica.
"""
import pytest
from datetime import date, timedelta
from core.constants import ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_DE_BAJA
from core.models import Equipo, Calibracion, Mantenimiento, Comprobacion, BajaEquipo
from core.views.dashboard import (
    get_projected_activities_for_year,
    get_projected_maintenance_compliance_for_year,
)


# ---------------------------------------------------------------------------
# Helpers de creación
# ---------------------------------------------------------------------------

def _make_equipo(empresa, estado=ESTADO_ACTIVO, freq_cal=6, freq_mant=None, freq_comp=None, **kwargs):
    counter = Equipo.objects.count() + 1
    equipo = Equipo.objects.create(
        empresa=empresa,
        codigo_interno=f'EQ-BAJA-{counter:04d}',
        nombre=f'Equipo Baja Test {counter}',
        tipo_equipo='Equipo de Medición',
        estado=estado,
        frecuencia_calibracion_meses=freq_cal,
        frecuencia_mantenimiento_meses=freq_mant,
        frecuencia_comprobacion_meses=freq_comp,
        **kwargs,
    )
    return equipo


def _make_calibracion(equipo, fecha):
    return Calibracion.objects.create(
        equipo=equipo,
        fecha_calibracion=fecha,
        nombre_proveedor='Lab Test',
        resultado='Aprobado',
        numero_certificado=f'CERT-{fecha}',
    )


def _make_mantenimiento(equipo, fecha):
    return Mantenimiento.objects.create(
        equipo=equipo,
        fecha_mantenimiento=fecha,
        tipo_mantenimiento='Preventivo',
        nombre_proveedor='Taller Test',
        responsable='Técnico Test',
        descripcion='Mantenimiento test',
    )


def _make_baja(equipo, fecha_baja, razon='Baja por test'):
    """Crea el BajaEquipo y cambia el estado del equipo."""
    Equipo.objects.filter(pk=equipo.pk).update(estado=ESTADO_DE_BAJA)
    equipo.refresh_from_db()
    return BajaEquipo.objects.create(
        equipo=equipo,
        fecha_baja=fecha_baja,
        razon_baja=razon,
    )


# ---------------------------------------------------------------------------
# Tests: Equipos De Baja
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEquipoBajaEnTorta:
    """El equipo dado de baja ESTE AÑO debe aparecer en la torta de cumplimiento."""

    def test_equipo_baja_en_año_actual_incluido_en_torta(self, empresa_factory):
        """Un equipo dado de baja en el año actual debe aparecer en la proyección."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        # Equipo con calibración cada 6 meses, dado de baja en junio
        equipo = _make_equipo(empresa, freq_cal=6)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        fecha_baja = date(year, 6, 15)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        # Debe haber al menos 1 actividad proyectada (no excluido por ser año actual)
        assert len(resultado) >= 1

    def test_equipo_baja_año_anterior_excluido(self, empresa_factory):
        """Un equipo dado de baja en un año anterior no debe aparecer en la proyección del año actual."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_cal=6)
        fecha_inicio = date(year - 2, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        # Dar de baja en el año pasado
        fecha_baja = date(year - 1, 6, 15)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        # No debe aparecer: se dio de baja antes del año calculado
        assert len(resultado) == 0

    def test_actividades_antes_baja_son_normales(self, empresa_factory):
        """
        Las actividades programadas ANTES de la fecha de baja siguen lógica normal
        (Realizado si se hizo, No Cumplido si es pasada, Pendiente si es futura).
        """
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        # Fecha de adquisición = enero del año actual, frecuencia 6 meses → julio
        equipo = _make_equipo(empresa, freq_cal=6)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        # Calibración realizada en enero (la primera)
        _make_calibracion(equipo, date(year, 1, 15))

        # Dar de baja en diciembre (después de las actividades programadas)
        fecha_baja = date(year, 12, 1)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        # Actividad realizada en enero debería ser 'Realizado'
        realizadas = [a for a in resultado if a['status'] == 'Realizado']
        assert len(realizadas) >= 1

    def test_actividades_desde_baja_son_no_cumplido(self, empresa_factory):
        """
        Las actividades programadas DESDE la fecha de baja (inclusive) deben ser 'No Cumplido'.
        """
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        # Equipo con calibración cada 3 meses → enero, abril, julio, octubre
        equipo = _make_equipo(empresa, freq_cal=3)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        # Dar de baja en junio → actividades de julio/oct deben ser No Cumplido
        fecha_baja = date(year, 6, 1)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        # Actividades desde fecha_baja deben ser 'No Cumplido'
        desde_baja = [a for a in resultado if a['fecha_programada'] >= fecha_baja]
        for actividad in desde_baja:
            assert actividad['status'] == 'No Cumplido', (
                f"Actividad en {actividad['fecha_programada']} debería ser 'No Cumplido', "
                f"pero es '{actividad['status']}'"
            )

    def test_justificacion_incluye_razon_baja(self, empresa_factory):
        """La justificación para actividades No Cumplido de un equipo De Baja incluye la razón."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_cal=3)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        fecha_baja = date(year, 4, 1)
        razon = 'Equipo obsoleto por prueba'
        _make_baja(equipo, fecha_baja, razon=razon)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        # Al menos una actividad No Cumplido con justificación de baja
        no_cumplidas = [a for a in resultado if a['status'] == 'No Cumplido']
        assert len(no_cumplidas) >= 1
        for actividad in no_cumplidas:
            assert 'justificacion' in actividad
            assert razon in actividad['justificacion'], (
                f"Justificación esperaba '{razon}', obtuvo '{actividad['justificacion']}'"
            )

    def test_equipo_baja_sin_baja_registro_excluido(self, empresa_factory):
        """Un equipo con estado 'De Baja' pero sin BajaEquipo asociado debe ser excluido."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_cal=6)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(
            fecha_adquisicion=fecha_inicio,
            estado=ESTADO_DE_BAJA,
        )
        equipo.refresh_from_db()

        # NO crear BajaEquipo
        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        assert len(resultado) == 0


# ---------------------------------------------------------------------------
# Tests: Equipos Inactivos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEquipoInactivoEnTorta:
    """Los equipos Inactivos deben tener todas las actividades no realizadas como No Cumplido."""

    def test_equipo_inactivo_pasadas_son_no_cumplido_futuras_son_pendiente(self, empresa_factory):
        """
        Para un equipo Inactivo:
        - Fechas pasadas no realizadas → No Cumplido
        - Fechas futuras no realizadas → Pendiente/Programado (puede reactivarse)
        """
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, estado=ESTADO_INACTIVO, freq_cal=6)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        assert len(resultado) >= 1
        for actividad in resultado:
            if actividad['status'] == 'Realizado':
                continue
            if actividad['fecha_programada'] < today:
                assert actividad['status'] == 'No Cumplido', (
                    f"Fecha pasada inactiva {actividad['fecha_programada']} debería ser 'No Cumplido'"
                )
            else:
                assert actividad['status'] == 'Pendiente/Programado', (
                    f"Fecha futura inactiva {actividad['fecha_programada']} debería ser 'Pendiente/Programado'"
                )

    def test_justificacion_inactivo_usa_observaciones(self, empresa_factory):
        """La justificación para un equipo Inactivo incluye sus observaciones."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        obs = 'Fuera de uso por renovación de laboratorio'
        equipo = _make_equipo(empresa, estado=ESTADO_INACTIVO, freq_cal=6)
        Equipo.objects.filter(pk=equipo.pk).update(
            fecha_adquisicion=date(year, 1, 1),
            observaciones=obs,
        )
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        no_cumplidas = [a for a in resultado if a['status'] == 'No Cumplido']
        assert len(no_cumplidas) >= 1
        for actividad in no_cumplidas:
            assert obs in actividad['justificacion'], (
                f"Justificación esperaba '{obs}', obtuvo '{actividad['justificacion']}'"
            )

    def test_equipo_inactivo_actividad_realizada_es_realizado(self, empresa_factory):
        """Si se realizó una actividad (antes de quedar inactivo), debe ser 'Realizado'."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, estado=ESTADO_INACTIVO, freq_cal=6)
        fecha_cal = date(year, 1, 15)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=date(year, 1, 1))
        equipo.refresh_from_db()

        # Registrar calibración realizada
        _make_calibracion(equipo, fecha_cal)

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        realizadas = [a for a in resultado if a['status'] == 'Realizado']
        assert len(realizadas) >= 1


# ---------------------------------------------------------------------------
# Tests: Mantenimientos con baja/inactivo
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMantenimientoBajaInactivo:
    """Verificar la función get_projected_maintenance_compliance_for_year."""

    def test_mantenimiento_equipo_baja_en_año_actual(self, empresa_factory):
        """Mantenimientos de equipo dado de baja este año se incluyen en la proyección."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_mant=6, freq_cal=None)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        fecha_baja = date(year, 8, 1)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_maintenance_compliance_for_year(qs, year, today)

        assert len(resultado) >= 1

    def test_mantenimiento_desde_baja_es_no_cumplido(self, empresa_factory):
        """Mantenimientos programados DESDE la fecha de baja son No Cumplido."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_mant=3, freq_cal=None)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        # Dado de baja en junio
        fecha_baja = date(year, 6, 1)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_maintenance_compliance_for_year(qs, year, today)

        desde_baja = [a for a in resultado if a['fecha_programada'] >= fecha_baja]
        for actividad in desde_baja:
            assert actividad['status'] == 'No Cumplido'

    def test_mantenimiento_equipo_inactivo_pasadas_no_cumplido_futuras_pendiente(self, empresa_factory):
        """Para equipo Inactivo: pasadas → No Cumplido; futuras → Pendiente/Programado."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, estado=ESTADO_INACTIVO, freq_mant=6, freq_cal=None)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=date(year, 1, 1))
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_maintenance_compliance_for_year(qs, year, today)

        assert len(resultado) >= 1
        for actividad in resultado:
            if actividad['status'] == 'Realizado':
                continue
            if actividad['fecha_programada'] < today:
                assert actividad['status'] == 'No Cumplido'
            else:
                assert actividad['status'] == 'Pendiente/Programado'


# ---------------------------------------------------------------------------
# Tests: Comprobaciones con baja
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComprobacionBajaInactivo:
    """Verificar la función get_projected_activities_for_year con comprobaciones."""

    def test_comprobacion_equipo_baja_en_año_actual(self, empresa_factory):
        """Comprobaciones de equipo dado de baja este año se incluyen."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_cal=6, freq_comp=3)
        fecha_inicio = date(year, 1, 1)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_inicio)
        equipo.refresh_from_db()

        # Dar una calibración para que haya fecha de referencia para comprobaciones
        _make_calibracion(equipo, date(year, 1, 5))

        fecha_baja = date(year, 9, 1)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'comprobacion', year, today)

        assert len(resultado) >= 1

    def test_comprobacion_desde_baja_es_no_cumplido(self, empresa_factory):
        """Comprobaciones desde fecha_baja son No Cumplido."""
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, freq_cal=6, freq_comp=3)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=date(year, 1, 1))
        equipo.refresh_from_db()

        # Dar una calibración de referencia
        _make_calibracion(equipo, date(year, 1, 5))

        fecha_baja = date(year, 6, 1)
        _make_baja(equipo, fecha_baja)
        equipo.refresh_from_db()

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'comprobacion', year, today)

        desde_baja = [a for a in resultado if a['fecha_programada'] >= fecha_baja]
        for actividad in desde_baja:
            assert actividad['status'] == 'No Cumplido'


# ---------------------------------------------------------------------------
# Tests: Tabla de comportamiento esperado (integración)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTablaComportamiento:
    """
    Verifica la tabla completa del plan:
    - Equipo activo, actividad realizada → Realizado
    - Equipo activo, actividad futura → Pendiente/Programado
    - Equipo activo, actividad pasada no realizada → No Cumplido
    - Equipo Inactivo, actividad no realizada → No Cumplido
    - Equipo De Baja (este año), actividad ANTES de fecha_baja → lógica normal
    - Equipo De Baja (este año), actividad DESDE fecha_baja → No Cumplido
    - Equipo De Baja (año anterior) → No aparece
    """

    def test_equipo_activo_actividad_realizada(self, empresa_factory):
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        equipo = _make_equipo(empresa, estado=ESTADO_ACTIVO, freq_cal=6)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=date(year, 1, 1))
        equipo.refresh_from_db()
        _make_calibracion(equipo, date(year, 1, 15))

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        realizadas = [a for a in resultado if a['status'] == 'Realizado']
        assert len(realizadas) >= 1

    def test_equipo_activo_actividad_futura(self, empresa_factory):
        empresa = empresa_factory()
        today = date.today()
        year = today.year

        # Calibración cuya próxima fecha es en el futuro
        equipo = _make_equipo(empresa, estado=ESTADO_ACTIVO, freq_cal=6)
        # Usar fecha de adquisición reciente para que la próxima esté en el futuro
        fecha_ref = today - timedelta(days=30)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=fecha_ref)
        equipo.refresh_from_db()
        _make_calibracion(equipo, fecha_ref)

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        pendientes = [a for a in resultado if a['status'] == 'Pendiente/Programado']
        # Puede haber pendientes si la próxima cae después de today
        # El test simplemente verifica que el status es Pendiente cuando la fecha es futura
        for actividad in resultado:
            if actividad['fecha_programada'] > today:
                assert actividad['status'] == 'Pendiente/Programado'

    def test_equipo_activo_actividad_pasada_no_realizada(self, empresa_factory):
        empresa = empresa_factory()
        year = date.today().year
        today = date.today()

        # Equipo con actividad pasada que no fue realizada
        equipo = _make_equipo(empresa, estado=ESTADO_ACTIVO, freq_cal=12)
        Equipo.objects.filter(pk=equipo.pk).update(fecha_adquisicion=date(year, 1, 1))
        equipo.refresh_from_db()
        # NO registrar ninguna calibración

        qs = Equipo.objects.filter(pk=equipo.pk).select_related('baja_registro')
        resultado = get_projected_activities_for_year(qs, 'calibracion', year, today)

        pasadas_no_realizadas = [
            a for a in resultado
            if a['fecha_programada'] < today and a['status'] != 'Realizado'
        ]
        for actividad in pasadas_no_realizadas:
            assert actividad['status'] == 'No Cumplido'
