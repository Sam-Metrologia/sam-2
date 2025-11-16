# core/utils/analisis_financiero.py
# Funciones de análisis financiero para Panel de Decisiones

from django.db.models import Sum, Avg, Count, Q
from datetime import date
from ..models import Calibracion, Mantenimiento, Comprobacion, Equipo


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
        print(f"Error calculando ingresos año anterior: {e}")

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