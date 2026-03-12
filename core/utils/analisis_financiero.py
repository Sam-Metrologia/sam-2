# core/utils/analisis_financiero.py
# Funciones de análisis financiero para Panel de Decisiones

from django.db.models import Sum, Avg, Count, Q
from datetime import date
from ..models import Calibracion, Mantenimiento, Comprobacion, Equipo
import logging

logger = logging.getLogger('core')


def calcular_analisis_financiero_empresa(empresa, current_year, today):
    """
    1. TRAZABILIDAD DE COSTOS ACTUALES (Gasto Histórico YTD)
    Calcula los costos reales incurridos en el año fiscal actual
    """
    # Costos YTD por tipo de actividad
    # CORRECCIÓN BUG 2025-11-16: Usar Decimal explícitamente para evitar TypeError
    from decimal import Decimal

    costos_calibracion_ytd = Calibracion.objects.filter(
        equipo__empresa=empresa,
        fecha_calibracion__year=current_year,
        fecha_calibracion__lte=today
    ).aggregate(total=Sum('costo_calibracion'))['total'] or Decimal('0')

    costos_mantenimiento_ytd = Mantenimiento.objects.filter(
        equipo__empresa=empresa,
        fecha_mantenimiento__year=current_year,
        fecha_mantenimiento__lte=today
    ).aggregate(total=Sum('costo_sam_interno'))['total'] or Decimal('0')

    costos_comprobacion_ytd = Comprobacion.objects.filter(
        equipo__empresa=empresa,
        fecha_comprobacion__year=current_year,
        fecha_comprobacion__lte=today
    ).aggregate(total=Sum('costo_comprobacion'))['total'] or Decimal('0')

    # Mantener como Decimal para cálculos precisos
    total_gasto_ytd = costos_calibracion_ytd + costos_mantenimiento_ytd + costos_comprobacion_ytd

    # Calcular porcentajes de distribución
    if total_gasto_ytd > 0:
        # Convertir a float solo para el cálculo de porcentaje
        porcentaje_calibracion = round(float(costos_calibracion_ytd / total_gasto_ytd) * 100, 1)
        porcentaje_mantenimiento = round(float(costos_mantenimiento_ytd / total_gasto_ytd) * 100, 1)
        porcentaje_comprobacion = round(float(costos_comprobacion_ytd / total_gasto_ytd) * 100, 1)
    else:
        porcentaje_calibracion = porcentaje_mantenimiento = porcentaje_comprobacion = 0

    # Convertir a float solo para JSON serialization
    return {
        'gasto_ytd_total': float(total_gasto_ytd),
        'costos_calibracion_ytd': float(costos_calibracion_ytd),
        'costos_mantenimiento_ytd': float(costos_mantenimiento_ytd),
        'costos_comprobacion_ytd': float(costos_comprobacion_ytd),
        'porcentaje_calibracion': porcentaje_calibracion,
        'porcentaje_mantenimiento': porcentaje_mantenimiento,
        'porcentaje_comprobacion': porcentaje_comprobacion,
    }


def calcular_proyeccion_costos_empresa(empresa, next_year):
    """
    2. PROYECCIÓN DE COSTOS (Gasto Estimado para el Próximo Año)
    Basado en homogeneidad de equipos (Marca y Modelo) y actividades programadas
    """
    equipos_empresa = list(
        Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])
    )
    if not equipos_empresa:
        return {'proyeccion_gasto_proximo_año': 0, 'actividades_proyectadas_total': 0}

    # --- Pre-fetch de costos en bloque (6 queries en lugar de N×6) ---

    # Último costo de calibración por equipo (order desc → primer visto = más reciente)
    _ultimo_costo_cal: dict = {}
    for item in (Calibracion.objects
                 .filter(equipo__empresa=empresa, costo_calibracion__isnull=False, costo_calibracion__gt=0)
                 .order_by('equipo_id', '-fecha_calibracion')
                 .values('equipo_id', 'costo_calibracion')):
        if item['equipo_id'] not in _ultimo_costo_cal:
            _ultimo_costo_cal[item['equipo_id']] = item['costo_calibracion']

    # Promedio de calibración por (marca, modelo)
    _promedio_cal: dict = {
        (r['equipo__marca'], r['equipo__modelo']): r['promedio']
        for r in Calibracion.objects.filter(
            equipo__empresa=empresa, costo_calibracion__isnull=False, costo_calibracion__gt=0
        ).values('equipo__marca', 'equipo__modelo').annotate(promedio=Avg('costo_calibracion'))
    }

    # Último costo de mantenimiento preventivo por equipo
    _ultimo_costo_mant: dict = {}
    for item in (Mantenimiento.objects
                 .filter(equipo__empresa=empresa, tipo_mantenimiento='Preventivo',
                         costo_sam_interno__isnull=False, costo_sam_interno__gt=0)
                 .order_by('equipo_id', '-fecha_mantenimiento')
                 .values('equipo_id', 'costo_sam_interno')):
        if item['equipo_id'] not in _ultimo_costo_mant:
            _ultimo_costo_mant[item['equipo_id']] = item['costo_sam_interno']

    # Promedio de mantenimiento preventivo por (marca, modelo)
    _promedio_mant: dict = {
        (r['equipo__marca'], r['equipo__modelo']): r['promedio']
        for r in Mantenimiento.objects.filter(
            equipo__empresa=empresa, tipo_mantenimiento='Preventivo',
            costo_sam_interno__isnull=False, costo_sam_interno__gt=0
        ).values('equipo__marca', 'equipo__modelo').annotate(promedio=Avg('costo_sam_interno'))
    }

    # Último costo de comprobación por equipo
    _ultimo_costo_comp: dict = {}
    for item in (Comprobacion.objects
                 .filter(equipo__empresa=empresa, costo_comprobacion__isnull=False, costo_comprobacion__gt=0)
                 .order_by('equipo_id', '-fecha_comprobacion')
                 .values('equipo_id', 'costo_comprobacion')):
        if item['equipo_id'] not in _ultimo_costo_comp:
            _ultimo_costo_comp[item['equipo_id']] = item['costo_comprobacion']

    # Promedio de comprobación por (marca, modelo)
    _promedio_comp: dict = {
        (r['equipo__marca'], r['equipo__modelo']): r['promedio']
        for r in Comprobacion.objects.filter(
            equipo__empresa=empresa, costo_comprobacion__isnull=False, costo_comprobacion__gt=0
        ).values('equipo__marca', 'equipo__modelo').annotate(promedio=Avg('costo_comprobacion'))
    }

    proyeccion_total = 0
    actividades_proyectadas = 0

    for equipo in equipos_empresa:
        # CALIBRACIONES PROYECTADAS
        if equipo.frecuencia_calibracion_meses and int(equipo.frecuencia_calibracion_meses) > 0:
            calibraciones_anuales = 12 // int(equipo.frecuencia_calibracion_meses)
            costo_unitario = (
                _ultimo_costo_cal.get(equipo.id)
                or _promedio_cal.get((equipo.marca, equipo.modelo))
            )
            if costo_unitario is not None:
                proyeccion_total += calibraciones_anuales * float(costo_unitario)
                actividades_proyectadas += calibraciones_anuales

        # MANTENIMIENTOS PROYECTADOS
        if equipo.frecuencia_mantenimiento_meses and int(equipo.frecuencia_mantenimiento_meses) > 0:
            mantenimientos_anuales = 12 // int(equipo.frecuencia_mantenimiento_meses)
            costo_unitario = (
                _ultimo_costo_mant.get(equipo.id)
                or _promedio_mant.get((equipo.marca, equipo.modelo))
            )
            if costo_unitario is not None:
                proyeccion_total += mantenimientos_anuales * float(costo_unitario)
                actividades_proyectadas += mantenimientos_anuales

        # COMPROBACIONES PROYECTADAS
        if equipo.frecuencia_comprobacion_meses and int(equipo.frecuencia_comprobacion_meses) > 0:
            comprobaciones_anuales = 12 // int(equipo.frecuencia_comprobacion_meses)
            costo_unitario = (
                _ultimo_costo_comp.get(equipo.id)
                or _promedio_comp.get((equipo.marca, equipo.modelo))
            )
            if costo_unitario is not None:
                proyeccion_total += comprobaciones_anuales * float(costo_unitario)
                actividades_proyectadas += comprobaciones_anuales

    return {
        'proyeccion_gasto_proximo_año': round(proyeccion_total, 2),
        'actividades_proyectadas_total': actividades_proyectadas
    }


def calcular_presupuesto_mensual_detallado(empresa, year):
    """
    4. PRESUPUESTO CALENDARIO MENSUAL DETALLADO
    Genera un presupuesto mes por mes con desglose de equipos y costos

    Returns:
        {
            'presupuesto_por_mes': [
                {
                    'mes': 1,
                    'nombre_mes': 'Enero',
                    'calibraciones': [{'equipo': obj, 'costo': 100000}, ...],
                    'mantenimientos': [...],
                    'comprobaciones': [...],
                    'total_mes': 500000
                },
                ...
            ],
            'total_anual': 6000000,
            'resumen': {...}
        }
    """
    from dateutil.relativedelta import relativedelta

    meses_nombres = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    presupuesto_mensual = [
        {
            'mes': mes,
            'nombre_mes': meses_nombres[mes - 1],
            'calibraciones': [],
            'mantenimientos': [],
            'comprobaciones': [],
            'total_calibraciones': 0,
            'total_mantenimientos': 0,
            'total_comprobaciones': 0,
            'total_mes': 0,
        }
        for mes in range(1, 13)
    ]

    equipos_empresa = list(
        Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])
    )

    if not equipos_empresa:
        resumen = {
            'total_anual': 0, 'total_calibraciones': 0, 'total_mantenimientos': 0,
            'total_comprobaciones': 0, 'count_calibraciones': 0, 'count_mantenimientos': 0,
            'count_comprobaciones': 0, 'count_total_actividades': 0, 'promedio_mensual': 0,
            'mes_mas_caro': None, 'mes_mas_economico': None,
        }
        return {'presupuesto_por_mes': presupuesto_mensual, 'total_anual': 0, 'resumen': resumen, 'año': year}

    # --- Pre-fetch costos (6 queries) ---
    _ultimo_costo_cal: dict = {}
    for item in (Calibracion.objects
                 .filter(equipo__empresa=empresa, costo_calibracion__isnull=False, costo_calibracion__gt=0)
                 .order_by('equipo_id', '-fecha_calibracion')
                 .values('equipo_id', 'costo_calibracion')):
        if item['equipo_id'] not in _ultimo_costo_cal:
            _ultimo_costo_cal[item['equipo_id']] = item['costo_calibracion']

    _promedio_cal: dict = {
        (r['equipo__marca'], r['equipo__modelo']): r['promedio']
        for r in Calibracion.objects.filter(
            equipo__empresa=empresa, costo_calibracion__isnull=False, costo_calibracion__gt=0
        ).values('equipo__marca', 'equipo__modelo').annotate(promedio=Avg('costo_calibracion'))
    }

    _ultimo_costo_mant: dict = {}
    for item in (Mantenimiento.objects
                 .filter(equipo__empresa=empresa, tipo_mantenimiento='Preventivo',
                         costo_sam_interno__isnull=False, costo_sam_interno__gt=0)
                 .order_by('equipo_id', '-fecha_mantenimiento')
                 .values('equipo_id', 'costo_sam_interno')):
        if item['equipo_id'] not in _ultimo_costo_mant:
            _ultimo_costo_mant[item['equipo_id']] = item['costo_sam_interno']

    _promedio_mant: dict = {
        (r['equipo__marca'], r['equipo__modelo']): r['promedio']
        for r in Mantenimiento.objects.filter(
            equipo__empresa=empresa, tipo_mantenimiento='Preventivo',
            costo_sam_interno__isnull=False, costo_sam_interno__gt=0
        ).values('equipo__marca', 'equipo__modelo').annotate(promedio=Avg('costo_sam_interno'))
    }

    _ultimo_costo_comp: dict = {}
    for item in (Comprobacion.objects
                 .filter(equipo__empresa=empresa, costo_comprobacion__isnull=False, costo_comprobacion__gt=0)
                 .order_by('equipo_id', '-fecha_comprobacion')
                 .values('equipo_id', 'costo_comprobacion')):
        if item['equipo_id'] not in _ultimo_costo_comp:
            _ultimo_costo_comp[item['equipo_id']] = item['costo_comprobacion']

    _promedio_comp: dict = {
        (r['equipo__marca'], r['equipo__modelo']): r['promedio']
        for r in Comprobacion.objects.filter(
            equipo__empresa=empresa, costo_comprobacion__isnull=False, costo_comprobacion__gt=0
        ).values('equipo__marca', 'equipo__modelo').annotate(promedio=Avg('costo_comprobacion'))
    }

    # --- Pre-fetch última fecha de actividad por equipo para fallback de mes_inicio (3 queries) ---
    _ultima_cal_fecha: dict = {}
    for item in (Calibracion.objects.filter(equipo__empresa=empresa)
                 .order_by('equipo_id', '-fecha_calibracion')
                 .values('equipo_id', 'fecha_calibracion')):
        if item['equipo_id'] not in _ultima_cal_fecha:
            _ultima_cal_fecha[item['equipo_id']] = item['fecha_calibracion']

    _ultima_mant_fecha: dict = {}
    for item in (Mantenimiento.objects.filter(equipo__empresa=empresa)
                 .order_by('equipo_id', '-fecha_mantenimiento')
                 .values('equipo_id', 'fecha_mantenimiento')):
        if item['equipo_id'] not in _ultima_mant_fecha:
            _ultima_mant_fecha[item['equipo_id']] = item['fecha_mantenimiento']

    _ultima_comp_fecha: dict = {}
    for item in (Comprobacion.objects.filter(equipo__empresa=empresa)
                 .order_by('equipo_id', '-fecha_comprobacion')
                 .values('equipo_id', 'fecha_comprobacion')):
        if item['equipo_id'] not in _ultima_comp_fecha:
            _ultima_comp_fecha[item['equipo_id']] = item['fecha_comprobacion']

    def _mes_inicio(freq_meses, proxima, ultima_fecha, fecha_adquisicion):
        """Calcula mes de inicio en el año dado sin hacer queries a DB."""
        if not freq_meses or int(freq_meses) <= 0:
            return None
        f = int(freq_meses)
        # Si proxima es exactamente en el año calculado, usarla directamente
        if proxima and proxima.year == year:
            return proxima.month
        # Si proxima es para otro año (pasado o futuro), calcular desde ultima_fecha
        # Esto cubre el caso donde el equipo ya hizo su actividad este año
        # y proxima_X apunta al año siguiente
        ref = ultima_fecha or fecha_adquisicion
        if not ref:
            return None
        fecha = ref
        while fecha.year < year:
            fecha += relativedelta(months=f)
        return fecha.month if fecha.year == year else None

    # --- Procesar cada equipo ---
    for equipo in equipos_empresa:
        eq_info = {
            'equipo': equipo,
            'codigo': equipo.codigo_interno,
            'nombre': equipo.nombre,
            'marca': equipo.marca or 'N/A',
            'modelo': equipo.modelo or 'N/A',
        }

        # CALIBRACIONES
        if equipo.frecuencia_calibracion_meses and int(equipo.frecuencia_calibracion_meses) > 0:
            freq = int(equipo.frecuencia_calibracion_meses)
            costo = _ultimo_costo_cal.get(equipo.id) or _promedio_cal.get((equipo.marca, equipo.modelo))
            if costo:
                mes_inicio = _mes_inicio(
                    freq, equipo.proxima_calibracion,
                    _ultima_cal_fecha.get(equipo.id), equipo.fecha_adquisicion
                )
                if mes_inicio is not None:
                    mes_actual = mes_inicio
                    while mes_actual <= 12:
                        presupuesto_mensual[mes_actual - 1]['calibraciones'].append(
                            {**eq_info, 'costo': float(costo)}
                        )
                        presupuesto_mensual[mes_actual - 1]['total_calibraciones'] += float(costo)
                        mes_actual += freq

        # MANTENIMIENTOS
        if equipo.frecuencia_mantenimiento_meses and int(equipo.frecuencia_mantenimiento_meses) > 0:
            freq = int(equipo.frecuencia_mantenimiento_meses)
            costo = _ultimo_costo_mant.get(equipo.id) or _promedio_mant.get((equipo.marca, equipo.modelo))
            if costo:
                mes_inicio = _mes_inicio(
                    freq, equipo.proximo_mantenimiento,
                    _ultima_mant_fecha.get(equipo.id), equipo.fecha_adquisicion
                )
                if mes_inicio is not None:
                    mes_actual = mes_inicio
                    while mes_actual <= 12:
                        presupuesto_mensual[mes_actual - 1]['mantenimientos'].append(
                            {**eq_info, 'costo': float(costo)}
                        )
                        presupuesto_mensual[mes_actual - 1]['total_mantenimientos'] += float(costo)
                        mes_actual += freq

        # COMPROBACIONES
        if equipo.frecuencia_comprobacion_meses and int(equipo.frecuencia_comprobacion_meses) > 0:
            freq = int(equipo.frecuencia_comprobacion_meses)
            costo = _ultimo_costo_comp.get(equipo.id) or _promedio_comp.get((equipo.marca, equipo.modelo))
            if costo:
                mes_inicio = _mes_inicio(
                    freq, equipo.proxima_comprobacion,
                    _ultima_comp_fecha.get(equipo.id), equipo.fecha_adquisicion
                )
                if mes_inicio is not None:
                    mes_actual = mes_inicio
                    while mes_actual <= 12:
                        presupuesto_mensual[mes_actual - 1]['comprobaciones'].append(
                            {**eq_info, 'costo': float(costo)}
                        )
                        presupuesto_mensual[mes_actual - 1]['total_comprobaciones'] += float(costo)
                        mes_actual += freq

    # Calcular totales mensuales
    total_anual = 0
    for mes_data in presupuesto_mensual:
        mes_data['total_mes'] = (
            mes_data['total_calibraciones']
            + mes_data['total_mantenimientos']
            + mes_data['total_comprobaciones']
        )
        total_anual += mes_data['total_mes']

    # Calcular resumen
    total_calibraciones_año = sum(m['total_calibraciones'] for m in presupuesto_mensual)
    total_mantenimientos_año = sum(m['total_mantenimientos'] for m in presupuesto_mensual)
    total_comprobaciones_año = sum(m['total_comprobaciones'] for m in presupuesto_mensual)
    count_calibraciones = sum(len(m['calibraciones']) for m in presupuesto_mensual)
    count_mantenimientos = sum(len(m['mantenimientos']) for m in presupuesto_mensual)
    count_comprobaciones = sum(len(m['comprobaciones']) for m in presupuesto_mensual)

    resumen = {
        'total_anual': total_anual,
        'total_calibraciones': total_calibraciones_año,
        'total_mantenimientos': total_mantenimientos_año,
        'total_comprobaciones': total_comprobaciones_año,
        'count_calibraciones': count_calibraciones,
        'count_mantenimientos': count_mantenimientos,
        'count_comprobaciones': count_comprobaciones,
        'count_total_actividades': count_calibraciones + count_mantenimientos + count_comprobaciones,
        'promedio_mensual': total_anual / 12 if total_anual > 0 else 0,
        'mes_mas_caro': max(presupuesto_mensual, key=lambda x: x['total_mes']) if presupuesto_mensual else None,
        'mes_mas_economico': min(
            [m for m in presupuesto_mensual if m['total_mes'] > 0],
            key=lambda x: x['total_mes']
        ) if any(m['total_mes'] > 0 for m in presupuesto_mensual) else None,
    }

    return {
        'presupuesto_por_mes': presupuesto_mensual,
        'total_anual': total_anual,
        'resumen': resumen,
        'año': year,
    }


def _obtener_costo_estimado_calibracion(equipo, empresa, year):
    """Obtiene el costo estimado de calibración con actualización dinámica"""
    from decimal import Decimal

    # 1. Buscar último costo del equipo específico (puede ser del año proyectado si ya hay datos)
    ultimo_costo = Calibracion.objects.filter(
        equipo=equipo,
        costo_calibracion__isnull=False,
        costo_calibracion__gt=0
    ).order_by('-fecha_calibracion').first()

    if ultimo_costo:
        return ultimo_costo.costo_calibracion

    # 2. Buscar costo promedio por Marca y Modelo (más recientes tienen prioridad)
    costo_promedio = Calibracion.objects.filter(
        equipo__empresa=empresa,
        equipo__marca=equipo.marca,
        equipo__modelo=equipo.modelo,
        costo_calibracion__isnull=False,
        costo_calibracion__gt=0
    ).order_by('-fecha_calibracion').aggregate(promedio=Avg('costo_calibracion'))['promedio']

    return costo_promedio if costo_promedio else None


def _obtener_costo_estimado_mantenimiento(equipo, empresa, year):
    """Obtiene el costo estimado de mantenimiento con actualización dinámica"""
    from decimal import Decimal

    # 1. Buscar último costo del equipo específico (solo preventivos)
    ultimo_costo = Mantenimiento.objects.filter(
        equipo=equipo,
        tipo_mantenimiento='Preventivo',
        costo_sam_interno__isnull=False,
        costo_sam_interno__gt=0
    ).order_by('-fecha_mantenimiento').first()

    if ultimo_costo:
        return ultimo_costo.costo_sam_interno

    # 2. Buscar costo promedio por Marca y Modelo
    costo_promedio = Mantenimiento.objects.filter(
        equipo__empresa=empresa,
        equipo__marca=equipo.marca,
        equipo__modelo=equipo.modelo,
        tipo_mantenimiento='Preventivo',
        costo_sam_interno__isnull=False,
        costo_sam_interno__gt=0
    ).order_by('-fecha_mantenimiento').aggregate(promedio=Avg('costo_sam_interno'))['promedio']

    return costo_promedio if costo_promedio else None


def _obtener_costo_estimado_comprobacion(equipo, empresa, year):
    """Obtiene el costo estimado de comprobación con actualización dinámica"""
    from decimal import Decimal

    # 1. Buscar último costo del equipo específico
    ultimo_costo = Comprobacion.objects.filter(
        equipo=equipo,
        costo_comprobacion__isnull=False,
        costo_comprobacion__gt=0
    ).order_by('-fecha_comprobacion').first()

    if ultimo_costo:
        return ultimo_costo.costo_comprobacion

    # 2. Buscar costo promedio por Marca y Modelo
    costo_promedio = Comprobacion.objects.filter(
        equipo__empresa=empresa,
        equipo__marca=equipo.marca,
        equipo__modelo=equipo.modelo,
        costo_comprobacion__isnull=False,
        costo_comprobacion__gt=0
    ).order_by('-fecha_comprobacion').aggregate(promedio=Avg('costo_comprobacion'))['promedio']

    return costo_promedio if costo_promedio else None


def _calcular_mes_inicio_actividad(equipo, tipo_actividad, year):
    """
    Calcula el mes de inicio para una actividad en el año proyectado.
    Retorna el mes (1-12) si hay actividad en ese año, o None si no hay actividad.

    Basado en la última actividad realizada o la fecha de adquisición.
    SOLO incluye equipos que realmente tienen actividad programada en el año específico.
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta

    # Obtener la última actividad del tipo correspondiente
    if tipo_actividad == 'calibracion':
        ultima_actividad = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()
        fecha_proxima = equipo.proxima_calibracion
        frecuencia = equipo.frecuencia_calibracion_meses
    elif tipo_actividad == 'mantenimiento':
        ultima_actividad = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()
        fecha_proxima = equipo.proximo_mantenimiento
        frecuencia = equipo.frecuencia_mantenimiento_meses
    else:  # comprobacion
        ultima_actividad = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()
        fecha_proxima = equipo.proxima_comprobacion
        frecuencia = equipo.frecuencia_comprobacion_meses

    if not frecuencia or int(frecuencia) <= 0:
        return None  # Sin frecuencia, no se puede calcular

    frecuencia = int(frecuencia)

    # Si hay una fecha próxima programada y es en el año proyectado
    if fecha_proxima and fecha_proxima.year == year:
        return fecha_proxima.month

    # Si hay fecha próxima pero es para OTRO año, no incluir
    if fecha_proxima and fecha_proxima.year != year:
        return None

    # Si hay una última actividad, calcular la próxima basándose en ella
    if ultima_actividad:
        if tipo_actividad == 'calibracion':
            fecha_ultima = ultima_actividad.fecha_calibracion
        elif tipo_actividad == 'mantenimiento':
            fecha_ultima = ultima_actividad.fecha_mantenimiento
        else:
            fecha_ultima = ultima_actividad.fecha_comprobacion

        # Calcular cuándo sería la próxima actividad
        fecha_siguiente = fecha_ultima
        while fecha_siguiente.year < year:
            fecha_siguiente = fecha_siguiente + relativedelta(months=frecuencia)

        # SOLO retornar si cae exactamente en el año proyectado
        if fecha_siguiente.year == year:
            return fecha_siguiente.month
        else:
            return None  # La próxima actividad no es en este año

    # Si no hay datos, usar fecha de adquisición como referencia
    if equipo.fecha_adquisicion:
        fecha_ref = equipo.fecha_adquisicion
        fecha_siguiente = fecha_ref
        while fecha_siguiente.year < year:
            fecha_siguiente = fecha_siguiente + relativedelta(months=frecuencia)

        # SOLO retornar si cae exactamente en el año proyectado
        if fecha_siguiente.year == year:
            return fecha_siguiente.month
        else:
            return None  # La próxima actividad no es en este año

    # Si no hay ninguna referencia, no se puede determinar
    return None


def calcular_metricas_financieras_sam(empresas_queryset, current_year, previous_year):
    """
    3. MÉTRICAS FINANCIERAS DEL NEGOCIO SAM (Para Superusuarios)
    Análisis de ingresos, crecimiento y proyecciones del negocio
    """
    # 1. INGRESO TOTAL YTD (Año Actual)
    ingreso_ytd_actual = 0
    for empresa in empresas_queryset:
        ingreso_ytd_actual += empresa.get_ingresos_anuales_reales()

    # 2. INGRESO AÑO ANTERIOR (Para comparativa de crecimiento)
    ingreso_año_anterior = 0
    try:
        # Buscar actividades del año anterior como proxy de ingresos
        actividades_año_anterior = (
            Calibracion.objects.filter(
                equipo__empresa__in=empresas_queryset,
                fecha_calibracion__year=previous_year
            ).count() +
            Mantenimiento.objects.filter(
                equipo__empresa__in=empresas_queryset,
                fecha_mantenimiento__year=previous_year
            ).count() +
            Comprobacion.objects.filter(
                equipo__empresa__in=empresas_queryset,
                fecha_comprobacion__year=previous_year
            ).count()
        )

        # Estimación basada en actividades (proxy)
        if actividades_año_anterior > 0:
            ingreso_año_anterior = actividades_año_anterior * 500  # $500 promedio por actividad

    except Exception as e:
        logger.error(f"Error calculando ingresos año anterior: {e}", exc_info=True)

    # 3. CRECIMIENTO DE INGRESOS
    if ingreso_año_anterior > 0:
        crecimiento_ingresos = round(((ingreso_ytd_actual - ingreso_año_anterior) / ingreso_año_anterior) * 100, 1)
    else:
        crecimiento_ingresos = 0

    # 4. EMPRESAS ACTIVAS YTD
    empresas_activas_actual = empresas_queryset.filter(
        Q(equipos__isnull=False) | Q(tarifa_mensual_sam__gt=0)
    ).distinct().count()

    # 5. EMPRESAS ACTIVAS AÑO ANTERIOR
    # Usar un método más simple para empresas activas anteriores
    try:
        # Buscar empresas que tuvieron actividades el año anterior
        empresas_con_actividades_anterior = empresas_queryset.filter(
            Q(equipos__calibraciones__fecha_calibracion__year=previous_year) |
            Q(equipos__mantenimientos__fecha_mantenimiento__year=previous_year) |
            Q(equipos__comprobaciones__fecha_comprobacion__year=previous_year)
        ).distinct().count()

        empresas_activas_anterior = empresas_con_actividades_anterior
    except:
        # Fallback: usar estimación basada en empresas actuales
        empresas_activas_anterior = max(1, empresas_activas_actual - 1)

    # 6. CRECIMIENTO DE EMPRESAS
    if empresas_activas_anterior > 0:
        crecimiento_empresas = round(((empresas_activas_actual - empresas_activas_anterior) / empresas_activas_anterior) * 100, 1)
    else:
        crecimiento_empresas = 0

    # 7. PROYECCIÓN FIN DE AÑO
    mes_actual = date.today().month
    if mes_actual > 0:
        proyeccion_fin_año = round((ingreso_ytd_actual * 12) / mes_actual, 2)
    else:
        proyeccion_fin_año = ingreso_ytd_actual

    return {
        'ingreso_ytd_actual': ingreso_ytd_actual,
        'ingreso_año_anterior': ingreso_año_anterior,
        'crecimiento_ingresos_porcentaje': crecimiento_ingresos,
        'empresas_activas_actual': empresas_activas_actual,
        'empresas_activas_anterior': empresas_activas_anterior,
        'crecimiento_empresas_porcentaje': crecimiento_empresas,
        'proyeccion_fin_año': proyeccion_fin_año,
    }