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
    equipos_empresa = Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])

    proyeccion_total = 0
    actividades_proyectadas = 0

    for equipo in equipos_empresa:
        # CALIBRACIONES PROYECTADAS
        if equipo.frecuencia_calibracion_meses and int(equipo.frecuencia_calibracion_meses) > 0:
            calibraciones_anuales = 12 // int(equipo.frecuencia_calibracion_meses)

            # Buscar último costo conocido para este equipo específico
            ultimo_costo_cal = Calibracion.objects.filter(
                equipo=equipo,
                costo_calibracion__isnull=False,
                costo_calibracion__gt=0
            ).order_by('-fecha_calibracion').first()

            if ultimo_costo_cal:
                costo_unitario = ultimo_costo_cal.costo_calibracion
            else:
                # Buscar costo promedio por Marca y Modelo en la empresa
                costo_promedio = Calibracion.objects.filter(
                    equipo__empresa=empresa,
                    equipo__marca=equipo.marca,
                    equipo__modelo=equipo.modelo,
                    costo_calibracion__isnull=False,
                    costo_calibracion__gt=0
                ).aggregate(promedio=Avg('costo_calibracion'))['promedio']

                costo_unitario = costo_promedio if costo_promedio else None

            # Solo proyectar si tenemos datos históricos reales
            if costo_unitario is not None:
                proyeccion_total += calibraciones_anuales * float(costo_unitario)
                actividades_proyectadas += calibraciones_anuales

        # MANTENIMIENTOS PROYECTADOS
        if equipo.frecuencia_mantenimiento_meses and int(equipo.frecuencia_mantenimiento_meses) > 0:
            mantenimientos_anuales = 12 // int(equipo.frecuencia_mantenimiento_meses)

            # Buscar último costo conocido para mantenimientos preventivos
            ultimo_costo_mant = Mantenimiento.objects.filter(
                equipo=equipo,
                tipo_mantenimiento='Preventivo',
                costo_sam_interno__isnull=False,
                costo_sam_interno__gt=0
            ).order_by('-fecha_mantenimiento').first()

            if ultimo_costo_mant:
                costo_unitario = ultimo_costo_mant.costo_sam_interno
            else:
                # Buscar costo promedio por Marca y Modelo en la empresa
                costo_promedio = Mantenimiento.objects.filter(
                    equipo__empresa=empresa,
                    equipo__marca=equipo.marca,
                    equipo__modelo=equipo.modelo,
                    tipo_mantenimiento='Preventivo',
                    costo_sam_interno__isnull=False,
                    costo_sam_interno__gt=0
                ).aggregate(promedio=Avg('costo_sam_interno'))['promedio']

                costo_unitario = costo_promedio if costo_promedio else None

            # Solo proyectar si tenemos datos históricos reales
            if costo_unitario is not None:
                proyeccion_total += mantenimientos_anuales * float(costo_unitario)
                actividades_proyectadas += mantenimientos_anuales

        # COMPROBACIONES PROYECTADAS
        if equipo.frecuencia_comprobacion_meses and int(equipo.frecuencia_comprobacion_meses) > 0:
            comprobaciones_anuales = 12 // int(equipo.frecuencia_comprobacion_meses)

            # Buscar último costo conocido para este equipo específico
            ultimo_costo_comp = Comprobacion.objects.filter(
                equipo=equipo,
                costo_comprobacion__isnull=False,
                costo_comprobacion__gt=0
            ).order_by('-fecha_comprobacion').first()

            if ultimo_costo_comp:
                costo_unitario = ultimo_costo_comp.costo_comprobacion
            else:
                # Buscar costo promedio por Marca y Modelo en la empresa
                costo_promedio = Comprobacion.objects.filter(
                    equipo__empresa=empresa,
                    equipo__marca=equipo.marca,
                    equipo__modelo=equipo.modelo,
                    costo_comprobacion__isnull=False,
                    costo_comprobacion__gt=0
                ).aggregate(promedio=Avg('costo_comprobacion'))['promedio']

                costo_unitario = costo_promedio if costo_promedio else None

            # Solo proyectar si tenemos datos históricos reales
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
    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    equipos_empresa = Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])

    # Estructura para almacenar el presupuesto mensual
    presupuesto_mensual = []
    meses_nombres = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    # Inicializar estructura para cada mes
    for mes in range(1, 13):
        presupuesto_mensual.append({
            'mes': mes,
            'nombre_mes': meses_nombres[mes - 1],
            'calibraciones': [],
            'mantenimientos': [],
            'comprobaciones': [],
            'total_calibraciones': 0,
            'total_mantenimientos': 0,
            'total_comprobaciones': 0,
            'total_mes': 0
        })

    # Procesar cada equipo
    for equipo in equipos_empresa:
        # CALIBRACIONES
        if equipo.frecuencia_calibracion_meses and int(equipo.frecuencia_calibracion_meses) > 0:
            frecuencia_meses = int(equipo.frecuencia_calibracion_meses)

            # Obtener costo estimado
            costo_calibracion = _obtener_costo_estimado_calibracion(equipo, empresa, year)

            if costo_calibracion:
                # Determinar mes de inicio basado en la última calibración o fecha de adquisición
                mes_inicio = _calcular_mes_inicio_actividad(equipo, 'calibracion', year)

                # Proyectar calibraciones a lo largo del año
                mes_actual = mes_inicio
                while mes_actual <= 12:
                    presupuesto_mensual[mes_actual - 1]['calibraciones'].append({
                        'equipo': equipo,
                        'codigo': equipo.codigo_interno,
                        'nombre': equipo.nombre,
                        'marca': equipo.marca or 'N/A',
                        'modelo': equipo.modelo or 'N/A',
                        'costo': float(costo_calibracion)
                    })
                    presupuesto_mensual[mes_actual - 1]['total_calibraciones'] += float(costo_calibracion)
                    mes_actual += frecuencia_meses

        # MANTENIMIENTOS
        if equipo.frecuencia_mantenimiento_meses and int(equipo.frecuencia_mantenimiento_meses) > 0:
            frecuencia_meses = int(equipo.frecuencia_mantenimiento_meses)

            # Obtener costo estimado
            costo_mantenimiento = _obtener_costo_estimado_mantenimiento(equipo, empresa, year)

            if costo_mantenimiento:
                # Determinar mes de inicio
                mes_inicio = _calcular_mes_inicio_actividad(equipo, 'mantenimiento', year)

                # Proyectar mantenimientos a lo largo del año
                mes_actual = mes_inicio
                while mes_actual <= 12:
                    presupuesto_mensual[mes_actual - 1]['mantenimientos'].append({
                        'equipo': equipo,
                        'codigo': equipo.codigo_interno,
                        'nombre': equipo.nombre,
                        'marca': equipo.marca or 'N/A',
                        'modelo': equipo.modelo or 'N/A',
                        'costo': float(costo_mantenimiento)
                    })
                    presupuesto_mensual[mes_actual - 1]['total_mantenimientos'] += float(costo_mantenimiento)
                    mes_actual += frecuencia_meses

        # COMPROBACIONES
        if equipo.frecuencia_comprobacion_meses and int(equipo.frecuencia_comprobacion_meses) > 0:
            frecuencia_meses = int(equipo.frecuencia_comprobacion_meses)

            # Obtener costo estimado
            costo_comprobacion = _obtener_costo_estimado_comprobacion(equipo, empresa, year)

            if costo_comprobacion:
                # Determinar mes de inicio
                mes_inicio = _calcular_mes_inicio_actividad(equipo, 'comprobacion', year)

                # Proyectar comprobaciones a lo largo del año
                mes_actual = mes_inicio
                while mes_actual <= 12:
                    presupuesto_mensual[mes_actual - 1]['comprobaciones'].append({
                        'equipo': equipo,
                        'codigo': equipo.codigo_interno,
                        'nombre': equipo.nombre,
                        'marca': equipo.marca or 'N/A',
                        'modelo': equipo.modelo or 'N/A',
                        'costo': float(costo_comprobacion)
                    })
                    presupuesto_mensual[mes_actual - 1]['total_comprobaciones'] += float(costo_comprobacion)
                    mes_actual += frecuencia_meses

    # Calcular totales mensuales
    total_anual = 0
    for mes_data in presupuesto_mensual:
        mes_data['total_mes'] = (
            mes_data['total_calibraciones'] +
            mes_data['total_mantenimientos'] +
            mes_data['total_comprobaciones']
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
        'mes_mas_economico': min([m for m in presupuesto_mensual if m['total_mes'] > 0],
                                  key=lambda x: x['total_mes']) if any(m['total_mes'] > 0 for m in presupuesto_mensual) else None
    }

    return {
        'presupuesto_por_mes': presupuesto_mensual,
        'total_anual': total_anual,
        'resumen': resumen,
        'año': year
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
    Calcula el mes de inicio para una actividad en el año proyectado
    Basado en la última actividad realizada o la fecha de adquisición
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
        return 1  # Default: enero

    frecuencia = int(frecuencia)

    # Si hay una fecha próxima programada y es en el año proyectado
    if fecha_proxima and fecha_proxima.year == year:
        return fecha_proxima.month

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

        if fecha_siguiente.year == year:
            return fecha_siguiente.month

    # Si no hay datos, usar fecha de adquisición como referencia
    if equipo.fecha_adquisicion:
        fecha_ref = equipo.fecha_adquisicion
        fecha_siguiente = fecha_ref
        while fecha_siguiente.year < year:
            fecha_siguiente = fecha_siguiente + relativedelta(months=frecuencia)

        if fecha_siguiente.year == year:
            return fecha_siguiente.month

    # Default: distribuir uniformemente a lo largo del año
    # Usar un offset basado en el ID del equipo para evitar que todo caiga en enero
    return ((equipo.id - 1) % 12) + 1


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