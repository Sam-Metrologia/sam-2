# core/utils/decision_intelligence.py
# Funciones de inteligencia empresarial para Panel de Decisiones
# Implementa: Alertas Predictivas, ROI, Tendencias, Compliance, Optimización

from django.db.models import Sum, Avg, Count, Q, F
from datetime import date, timedelta, datetime
from collections import defaultdict, Counter
import calendar
from ..models import Calibracion, Mantenimiento, Comprobacion, Equipo


def calcular_alertas_predictivas(empresa, today):
    """
    1. SISTEMA DE ALERTAS PREDICTIVAS
    Analiza riesgos por días restantes y criticidad del equipo
    """
    equipos = Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])

    alertas = {
        'criticas': [],      # < 7 días
        'riesgo_alto': [],   # 7-15 días
        'riesgo_medio': [],  # 15-30 días
        'ok': [],            # > 30 días
        'vencidas': []       # Ya vencido
    }

    for equipo in equipos:
        # Analizar calibraciones
        if equipo.proxima_calibracion:
            dias_restantes = (equipo.proxima_calibracion - today).days
            tipo_actividad = 'Calibración'

            if dias_restantes < 0:
                alertas['vencidas'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_vencido': abs(dias_restantes),
                    'fecha_vencimiento': equipo.proxima_calibracion,
                    'nivel_riesgo': 'VENCIDA'
                })
            elif dias_restantes < 7:
                alertas['criticas'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proxima_calibracion,
                    'nivel_riesgo': 'CRÍTICO'
                })
            elif dias_restantes <= 15:
                alertas['riesgo_alto'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proxima_calibracion,
                    'nivel_riesgo': 'ALTO'
                })
            elif dias_restantes <= 30:
                alertas['riesgo_medio'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proxima_calibracion,
                    'nivel_riesgo': 'MEDIO'
                })
            else:
                alertas['ok'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proxima_calibracion,
                    'nivel_riesgo': 'OK'
                })

        # Analizar mantenimientos
        if equipo.proximo_mantenimiento:
            dias_restantes = (equipo.proximo_mantenimiento - today).days
            tipo_actividad = 'Mantenimiento'

            if dias_restantes < 0:
                alertas['vencidas'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_vencido': abs(dias_restantes),
                    'fecha_vencimiento': equipo.proximo_mantenimiento,
                    'nivel_riesgo': 'VENCIDA'
                })
            elif dias_restantes < 7:
                alertas['criticas'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proximo_mantenimiento,
                    'nivel_riesgo': 'CRÍTICO'
                })
            elif dias_restantes <= 15:
                alertas['riesgo_alto'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proximo_mantenimiento,
                    'nivel_riesgo': 'ALTO'
                })
            elif dias_restantes <= 30:
                alertas['riesgo_medio'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proximo_mantenimiento,
                    'nivel_riesgo': 'MEDIO'
                })

        # Analizar comprobaciones
        if equipo.proxima_comprobacion:
            dias_restantes = (equipo.proxima_comprobacion - today).days
            tipo_actividad = 'Comprobación'

            if dias_restantes < 0:
                alertas['vencidas'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_vencido': abs(dias_restantes),
                    'fecha_vencimiento': equipo.proxima_comprobacion,
                    'nivel_riesgo': 'VENCIDA'
                })
            elif dias_restantes < 7:
                alertas['criticas'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proxima_comprobacion,
                    'nivel_riesgo': 'CRÍTICO'
                })
            elif dias_restantes <= 15:
                alertas['riesgo_alto'].append({
                    'equipo': equipo,
                    'tipo': tipo_actividad,
                    'dias_restantes': dias_restantes,
                    'fecha_vencimiento': equipo.proxima_comprobacion,
                    'nivel_riesgo': 'ALTO'
                })

    # Calcular métricas de resumen
    total_alertas = len(alertas['vencidas']) + len(alertas['criticas']) + len(alertas['riesgo_alto'])

    # Ordenar por urgencia
    alertas['vencidas'].sort(key=lambda x: x['dias_vencido'], reverse=True)
    alertas['criticas'].sort(key=lambda x: x['dias_restantes'])
    alertas['riesgo_alto'].sort(key=lambda x: x['dias_restantes'])

    return {
        'alertas': alertas,
        'total_alertas_criticas': total_alertas,
        'nivel_riesgo_general': 'CRÍTICO' if len(alertas['vencidas']) + len(alertas['criticas']) > 0
                               else 'ALTO' if len(alertas['riesgo_alto']) > 5
                               else 'MEDIO' if len(alertas['riesgo_alto']) > 0
                               else 'BAJO'
    }


def calcular_roi_rentabilidad(empresa, current_year):
    """
    2. DASHBOARD DE ROI Y RENTABILIDAD
    Analiza costo-beneficio de mantenimiento preventivo vs correctivo
    """
    equipos = Equipo.objects.filter(empresa=empresa)

    # Mantenimientos por tipo este año
    mantenimientos_preventivos = Mantenimiento.objects.filter(
        equipo__empresa=empresa,
        fecha_mantenimiento__year=current_year,
        tipo_mantenimiento='Preventivo',
        costo_sam_interno__isnull=False,
        costo_sam_interno__gt=0
    )

    mantenimientos_correctivos = Mantenimiento.objects.filter(
        equipo__empresa=empresa,
        fecha_mantenimiento__year=current_year,
        tipo_mantenimiento='Correctivo',
        costo_sam_interno__isnull=False,
        costo_sam_interno__gt=0
    )

    costo_preventivos = mantenimientos_preventivos.aggregate(total=Sum('costo_sam_interno'))['total'] or 0
    costo_correctivos = mantenimientos_correctivos.aggregate(total=Sum('costo_sam_interno'))['total'] or 0

    count_preventivos = mantenimientos_preventivos.count()
    count_correctivos = mantenimientos_correctivos.count()

    # Calcular ROI
    if costo_preventivos > 0:
        roi_porcentaje = round(((costo_correctivos - costo_preventivos) / costo_preventivos) * 100, 1)
        ahorro_total = costo_correctivos - costo_preventivos
    else:
        roi_porcentaje = 0
        ahorro_total = 0

    # Costo promedio por tipo
    costo_promedio_preventivo = round(costo_preventivos / count_preventivos, 0) if count_preventivos > 0 else 0
    costo_promedio_correctivo = round(costo_correctivos / count_correctivos, 0) if count_correctivos > 0 else 0

    # Ratio preventivo/correctivo ideal
    total_mantenimientos = count_preventivos + count_correctivos
    ratio_preventivo = round((count_preventivos / total_mantenimientos) * 100, 1) if total_mantenimientos > 0 else 0

    # Evaluación del ratio (80/20 es ideal)
    if ratio_preventivo >= 80:
        evaluacion_ratio = 'EXCELENTE'
    elif ratio_preventivo >= 65:
        evaluacion_ratio = 'BUENO'
    elif ratio_preventivo >= 50:
        evaluacion_ratio = 'REGULAR'
    else:
        evaluacion_ratio = 'DEFICIENTE'

    return {
        'costo_preventivos': costo_preventivos,
        'costo_correctivos': costo_correctivos,
        'count_preventivos': count_preventivos,
        'count_correctivos': count_correctivos,
        'roi_porcentaje': roi_porcentaje,
        'ahorro_total': ahorro_total,
        'costo_promedio_preventivo': costo_promedio_preventivo,
        'costo_promedio_correctivo': costo_promedio_correctivo,
        'ratio_preventivo': ratio_preventivo,
        'evaluacion_ratio': evaluacion_ratio,
        'interpretacion_roi': 'Excelente retorno' if roi_porcentaje > 50
                             else 'Buen retorno' if roi_porcentaje > 20
                             else 'Retorno moderado' if roi_porcentaje > 0
                             else 'Revisar estrategia'
    }


def calcular_tendencias_historicas(empresa, current_year):
    """
    3. ANÁLISIS DE TENDENCIAS HISTÓRICAS
    Evolución mensual de gastos y cumplimiento
    """
    # Datos mensuales del año actual
    datos_mensuales = []
    total_gastos_año = 0

    for mes in range(1, 13):
        # Gastos del mes
        gastos_calibracion = Calibracion.objects.filter(
            equipo__empresa=empresa,
            fecha_calibracion__year=current_year,
            fecha_calibracion__month=mes,
            costo_calibracion__isnull=False
        ).aggregate(total=Sum('costo_calibracion'))['total'] or 0

        gastos_mantenimiento = Mantenimiento.objects.filter(
            equipo__empresa=empresa,
            fecha_mantenimiento__year=current_year,
            fecha_mantenimiento__month=mes,
            costo_sam_interno__isnull=False
        ).aggregate(total=Sum('costo_sam_interno'))['total'] or 0

        gastos_comprobacion = Comprobacion.objects.filter(
            equipo__empresa=empresa,
            fecha_comprobacion__year=current_year,
            fecha_comprobacion__month=mes,
            costo_comprobacion__isnull=False
        ).aggregate(total=Sum('costo_comprobacion'))['total'] or 0

        gasto_total_mes = gastos_calibracion + gastos_mantenimiento + gastos_comprobacion
        total_gastos_año += gasto_total_mes

        # Actividades del mes
        actividades_mes = (
            Calibracion.objects.filter(equipo__empresa=empresa, fecha_calibracion__year=current_year, fecha_calibracion__month=mes).count() +
            Mantenimiento.objects.filter(equipo__empresa=empresa, fecha_mantenimiento__year=current_year, fecha_mantenimiento__month=mes).count() +
            Comprobacion.objects.filter(equipo__empresa=empresa, fecha_comprobacion__year=current_year, fecha_comprobacion__month=mes).count()
        )

        datos_mensuales.append({
            'mes': mes,
            'nombre_mes': calendar.month_name[mes][:3],
            'gasto_total': gasto_total_mes,
            'actividades': actividades_mes,
            'gasto_calibracion': gastos_calibracion,
            'gasto_mantenimiento': gastos_mantenimiento,
            'gasto_comprobacion': gastos_comprobacion
        })

    # Calcular promedio mensual
    meses_con_datos = len([m for m in datos_mensuales if m['gasto_total'] > 0])
    promedio_mensual = total_gastos_año / meses_con_datos if meses_con_datos > 0 else 0

    # Identificar mes más caro y más barato
    mes_mas_caro = max(datos_mensuales, key=lambda x: x['gasto_total']) if datos_mensuales else None

    # Filtrar meses con gasto > 0 para el más barato
    meses_con_gastos = [m for m in datos_mensuales if m['gasto_total'] > 0]
    mes_mas_barato = min(meses_con_gastos, key=lambda x: x['gasto_total']) if meses_con_gastos else None

    # Tendencia (últimos 3 meses vs anteriores)
    mes_actual = date.today().month
    ultimos_3_meses = datos_mensuales[max(0, mes_actual-3):mes_actual]
    anteriores_3_meses = datos_mensuales[max(0, mes_actual-6):max(0, mes_actual-3)]

    promedio_reciente = sum(m['gasto_total'] for m in ultimos_3_meses) / len(ultimos_3_meses) if ultimos_3_meses else 0
    promedio_anterior = sum(m['gasto_total'] for m in anteriores_3_meses) / len(anteriores_3_meses) if anteriores_3_meses else 0

    if promedio_anterior > 0:
        tendencia_porcentaje = round(((promedio_reciente - promedio_anterior) / promedio_anterior) * 100, 1)
    else:
        tendencia_porcentaje = 0

    tendencia_direccion = 'ASCENDENTE' if tendencia_porcentaje > 10 else 'DESCENDENTE' if tendencia_porcentaje < -10 else 'ESTABLE'

    return {
        'datos_mensuales': datos_mensuales,
        'total_gastos_año': total_gastos_año,
        'promedio_mensual': promedio_mensual,
        'mes_mas_caro': mes_mas_caro,
        'mes_mas_barato': mes_mas_barato,
        'tendencia_porcentaje': tendencia_porcentaje,
        'tendencia_direccion': tendencia_direccion,
        'meses_con_datos': meses_con_datos
    }


def calcular_compliance_iso9001(empresa, today):
    """
    4. PANEL DE COMPLIANCE ISO 9001
    Monitorea cumplimiento de cláusula 7.1.5 (Recursos de seguimiento y medición)
    """
    equipos = Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])
    total_equipos = equipos.count()

    if total_equipos == 0:
        return {
            'score_iso9001': 100,
            'evaluacion': 'SIN EQUIPOS',
            'equipos_conformes': 0,
            'equipos_no_conformes': 0,
            'equipos_riesgo': 0,
            'total_equipos': 0,
            'no_conformidades': []
        }

    equipos_conformes = 0
    equipos_riesgo = 0  # Vencen en <30 días
    no_conformidades = []

    for equipo in equipos:
        conforme = True
        riesgo = False
        problemas = []

        # Verificar calibración vigente
        if equipo.proxima_calibracion:
            dias_calibracion = (equipo.proxima_calibracion - today).days
            if dias_calibracion < 0:
                conforme = False
                problemas.append(f"Calibración vencida hace {abs(dias_calibracion)} días")
            elif dias_calibracion <= 30:
                riesgo = True
                problemas.append(f"Calibración vence en {dias_calibracion} días")

        # Verificar mantenimiento vigente
        if equipo.proximo_mantenimiento:
            dias_mantenimiento = (equipo.proximo_mantenimiento - today).days
            if dias_mantenimiento < 0:
                conforme = False
                problemas.append(f"Mantenimiento vencido hace {abs(dias_mantenimiento)} días")
            elif dias_mantenimiento <= 30:
                riesgo = True
                problemas.append(f"Mantenimiento vence en {dias_mantenimiento} días")

        # Verificar estado operativo
        if equipo.estado not in ['Activo', 'Operativo']:
            conforme = False
            problemas.append(f"Estado no operativo: {equipo.estado}")

        if conforme and not riesgo:
            equipos_conformes += 1
        elif riesgo and conforme:
            equipos_riesgo += 1
        else:
            no_conformidades.append({
                'equipo': equipo,
                'problemas': problemas
            })

    equipos_no_conformes = len(no_conformidades)

    # Calcular score ISO 9001
    score_iso9001 = round((equipos_conformes / total_equipos) * 100, 1)

    # Evaluación del score
    if score_iso9001 >= 95:
        evaluacion = 'EXCELENTE'
    elif score_iso9001 >= 85:
        evaluacion = 'BUENO'
    elif score_iso9001 >= 75:
        evaluacion = 'REGULAR'
    else:
        evaluacion = 'DEFICIENTE'

    return {
        'score_iso9001': score_iso9001,
        'evaluacion': evaluacion,
        'equipos_conformes': equipos_conformes,
        'equipos_no_conformes': equipos_no_conformes,
        'equipos_riesgo': equipos_riesgo,
        'total_equipos': total_equipos,
        'no_conformidades': no_conformidades[:10]  # Limitar a 10 para UI
    }


def calcular_optimizacion_cronogramas(empresa, today):
    """
    5. OPTIMIZADOR DE CRONOGRAMAS Y EQUIPOS PROBLEMÁTICOS
    Identifica oportunidades de optimización y equipos recurrentemente problemáticos
    """
    equipos = Equipo.objects.filter(empresa=empresa).exclude(estado__in=['De Baja', 'Inactivo'])

    # A) OPTIMIZADOR DE CRONOGRAMAS
    # Agrupar actividades próximas por ubicación
    optimizaciones = defaultdict(list)

    for equipo in equipos:
        ubicacion = equipo.ubicacion or 'Sin ubicación'

        # Calibraciones próximas (próximos 15 días)
        if equipo.proxima_calibracion:
            dias_calibracion = (equipo.proxima_calibracion - today).days
            if 0 <= dias_calibracion <= 15:
                optimizaciones[ubicacion].append({
                    'equipo': equipo,
                    'tipo': 'Calibración',
                    'fecha': equipo.proxima_calibracion,
                    'dias_restantes': dias_calibracion
                })

        # Mantenimientos próximos (próximos 15 días)
        if equipo.proximo_mantenimiento:
            dias_mantenimiento = (equipo.proximo_mantenimiento - today).days
            if 0 <= dias_mantenimiento <= 15:
                optimizaciones[ubicacion].append({
                    'equipo': equipo,
                    'tipo': 'Mantenimiento',
                    'fecha': equipo.proximo_mantenimiento,
                    'dias_restantes': dias_mantenimiento
                })

    # Identificar oportunidades de optimización (2+ actividades en misma ubicación)
    oportunidades_optimizacion = []
    for ubicacion, actividades in optimizaciones.items():
        if len(actividades) >= 2:
            # Agrupar por proximidad de fechas (±7 días)
            actividades.sort(key=lambda x: x['fecha'])
            grupos = []
            grupo_actual = [actividades[0]]

            for i in range(1, len(actividades)):
                if abs((actividades[i]['fecha'] - grupo_actual[0]['fecha']).days) <= 7:
                    grupo_actual.append(actividades[i])
                else:
                    if len(grupo_actual) >= 2:
                        grupos.append(grupo_actual)
                    grupo_actual = [actividades[i]]

            if len(grupo_actual) >= 2:
                grupos.append(grupo_actual)

            for grupo in grupos:
                ahorro_estimado = (len(grupo) - 1) * 100000  # $100k ahorro por viaje evitado
                oportunidades_optimizacion.append({
                    'ubicacion': ubicacion,
                    'actividades': grupo,
                    'cantidad': len(grupo),
                    'ahorro_estimado': ahorro_estimado,
                    'fecha_sugerida': grupo[0]['fecha']
                })

    # B) EQUIPOS PROBLEMÁTICOS RECURRENTES
    # Analizar mantenimientos correctivos del último año
    year_ago = today - timedelta(days=365)

    mantenimientos_correctivos = Mantenimiento.objects.filter(
        equipo__empresa=empresa,
        tipo_mantenimiento='Correctivo',
        fecha_mantenimiento__gte=year_ago
    ).values('equipo_id').annotate(
        cantidad=Count('id'),
        costo_total=Sum('costo_sam_interno')
    ).order_by('-cantidad')

    equipos_problematicos = []
    for item in mantenimientos_correctivos:
        if item['cantidad'] >= 3:  # 3 o más correctivos = problemático
            try:
                equipo = Equipo.objects.get(id=item['equipo_id'])
                costo_total = item['costo_total'] or 0

                # Determinar nivel de problema
                if item['cantidad'] >= 6:
                    nivel_problema = 'CRÍTICO'
                elif item['cantidad'] >= 4:
                    nivel_problema = 'ALTO'
                else:
                    nivel_problema = 'MEDIO'

                # Calcular recomendación
                if costo_total > 5000000:  # >$5M en correctivos
                    recomendacion = 'Evaluar reemplazo del equipo'
                elif item['cantidad'] >= 5:
                    recomendacion = 'Aumentar frecuencia de mantenimiento preventivo'
                else:
                    recomendacion = 'Monitorear más de cerca y revisar procedimientos'

                equipos_problematicos.append({
                    'equipo': equipo,
                    'cantidad_correctivos': item['cantidad'],
                    'costo_total': costo_total,
                    'nivel_problema': nivel_problema,
                    'recomendacion': recomendacion
                })
            except Equipo.DoesNotExist:
                continue

    # Calcular ahorros potenciales totales
    ahorro_total_cronograma = sum(op['ahorro_estimado'] for op in oportunidades_optimizacion)

    return {
        'oportunidades_optimizacion': oportunidades_optimizacion[:5],  # Top 5
        'equipos_problematicos': equipos_problematicos[:10],  # Top 10
        'ahorro_total_cronograma': ahorro_total_cronograma,
        'total_oportunidades': len(oportunidades_optimizacion),
        'total_equipos_problematicos': len(equipos_problematicos)
    }