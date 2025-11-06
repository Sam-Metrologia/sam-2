# core/views/panel_decisiones.py
# Panel de Decisiones para Gerentes de Empresa Individual
# Basado en la lógica sólida del dashboard técnico

from .base import *
from datetime import date, timedelta
from django.db.models import Sum, Avg, Count, Q
from decimal import Decimal
from ..utils.analisis_financiero import (
    calcular_analisis_financiero_empresa,
    calcular_proyeccion_costos_empresa,
    calcular_metricas_financieras_sam
)
from ..utils.decision_intelligence import (
    calcular_alertas_predictivas,
    calcular_roi_rentabilidad,
    calcular_tendencias_historicas,
    calcular_compliance_iso9001,
    calcular_optimizacion_cronogramas
)
from .dashboard import get_projected_activities_for_year
import json


def decimal_to_float(obj):
    """
    Convierte objetos Decimal a float para serialización JSON.
    Mantiene otros tipos sin cambios.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


@login_required
@monitor_view
def panel_decisiones(request):
    """
    Panel de Decisiones Unificado - Información → Decisión

    DOBLE AUDIENCIA:
    1. Gerentes de Empresa Individual (GERENCIA): Vista táctica - "Qué debo hacer hoy"
    2. Administradores SAM (SUPERUSER): Vista estratégica - "Cómo está el negocio"

    Las 3 Métricas Pilares (coherentes con dashboard técnico):
    1. Salud del Equipo = Calibración + Mantenimiento + Comprobación vigentes
    2. Cumplimiento = Actividades realizadas a tiempo vs. programadas
    3. Eficiencia Operacional = Disponibilidad + Uso efectivo
    """
    user = request.user
    today = date.today()
    current_year = today.year

    # Verificar permisos para acceder al panel de decisiones
    if not user.puede_ver_panel_decisiones():
        messages.error(request, '⛔ No tienes permisos para acceder al Panel de Decisiones. Solo usuarios con rol de Gerente o Superusuario pueden acceder.')
        return redirect('core:home')

    # Determinar perspectiva: SAM (multi-empresa) vs EMPRESA (single-empresa)
    if user.is_superuser:
        # Si el superusuario seleccionó una empresa específica, mostrar panel completo de esa empresa
        selected_company_id = request.GET.get('empresa_id')
        if selected_company_id:
            try:
                empresa = Empresa.objects.get(id=selected_company_id, is_deleted=False)
                # PERSPECTIVA EMPRESA ESPECÍFICA: Vista táctica para esa empresa
                return _panel_decisiones_empresa(request, today, current_year, empresa_override=empresa)
            except Empresa.DoesNotExist:
                messages.warning(request, 'La empresa seleccionada no existe.')
                return _panel_decisiones_sam(request, today, current_year)
        else:
            # PERSPECTIVA SAM: Vista estratégica multi-empresa
            return _panel_decisiones_sam(request, today, current_year)
    elif user.puede_ver_panel_decisiones() and user.empresa:
        # PERSPECTIVA EMPRESA: Vista táctica single-empresa
        return _panel_decisiones_empresa(request, today, current_year)
    else:
        return render(request, 'core/panel_decisiones.html', {
            'error': 'Usuario sin permisos o empresa asignada',
            'titulo_pagina': 'Panel de Decisiones - Error de Acceso'
        })


def _calcular_salud_equipo(equipos_para_dashboard, today):
    """
    PILAR 1: Salud del Equipo con Fórmula Ponderada
    Fórmula: 30% Estado del Equipo + 25% Calibraciones + 25% Mantenimientos + 20% Comprobaciones = 100%
    """
    from django.db.models import Count, Case, When, IntegerField

    total_equipos = equipos_para_dashboard.count()
    if total_equipos == 0:
        return {
            'salud_general_porcentaje': 0,
            'salud_general_estado': 'CRÍTICO',
            'equipos_saludables': 0,
            'equipos_en_riesgo': 0,
            'equipos_criticos': 0,
            'total_equipos_salud': 0,
            'chart_data': [0, 0, 0],
            'formula_detalle': {
                'peso_estado': 30,
                'peso_calibraciones': 25,
                'peso_mantenimientos': 25,
                'peso_comprobaciones': 20,
                'puntuacion_estado': 0,
                'puntuacion_calibraciones': 0,
                'puntuacion_mantenimientos': 0,
                'puntuacion_comprobaciones': 0,
                'calculo_ejemplo': '(0×30% + 0×25% + 0×25% + 0×20%) = 0%'
            }
        }

    # Variables para el cálculo ponderado
    total_puntuacion = 0
    equipos_saludables = 0
    equipos_en_riesgo = 0
    equipos_criticos = 0

    # Puntuaciones acumuladas para fórmula detallada
    puntuacion_estado_total = 0
    puntuacion_calibraciones_total = 0
    puntuacion_mantenimientos_total = 0
    puntuacion_comprobaciones_total = 0

    for equipo in equipos_para_dashboard:
        # 1. ESTADO DEL EQUIPO (30%): Activo/Operativo = 100%, otros estados = 0%
        if equipo.estado in ['Activo', 'Operativo']:
            puntuacion_estado = 100
        else:
            puntuacion_estado = 0

        # 2. CALIBRACIONES (25%): Vigente = 100%, Vencida = 0%
        if equipo.proxima_calibracion and equipo.proxima_calibracion >= today:
            puntuacion_calibraciones = 100
        else:
            puntuacion_calibraciones = 0

        # 3. MANTENIMIENTOS (25%): Vigente = 100%, Vencido = 0%
        if equipo.proximo_mantenimiento and equipo.proximo_mantenimiento >= today:
            puntuacion_mantenimientos = 100
        else:
            puntuacion_mantenimientos = 0

        # 4. COMPROBACIONES (20%): Vigente = 100%, Vencida = 0%
        if equipo.proxima_comprobacion and equipo.proxima_comprobacion >= today:
            puntuacion_comprobaciones = 100
        else:
            puntuacion_comprobaciones = 0

        # Calcular puntuación ponderada del equipo
        puntuacion_equipo = (
            puntuacion_estado * 0.30 +
            puntuacion_calibraciones * 0.25 +
            puntuacion_mantenimientos * 0.25 +
            puntuacion_comprobaciones * 0.20
        )

        # Acumular para promedio general
        total_puntuacion += puntuacion_equipo
        puntuacion_estado_total += puntuacion_estado
        puntuacion_calibraciones_total += puntuacion_calibraciones
        puntuacion_mantenimientos_total += puntuacion_mantenimientos
        puntuacion_comprobaciones_total += puntuacion_comprobaciones

        # Clasificar equipo según puntuación
        if puntuacion_equipo >= 80:
            equipos_saludables += 1
        elif puntuacion_equipo >= 40:
            equipos_en_riesgo += 1
        else:
            equipos_criticos += 1

    # Calcular porcentaje de salud general usando fórmula ponderada
    salud_porcentaje = round(total_puntuacion / total_equipos, 1)

    # Promedios por componente para mostrar en fórmula detallada
    promedio_estado = round(puntuacion_estado_total / total_equipos, 1)
    promedio_calibraciones = round(puntuacion_calibraciones_total / total_equipos, 1)
    promedio_mantenimientos = round(puntuacion_mantenimientos_total / total_equipos, 1)
    promedio_comprobaciones = round(puntuacion_comprobaciones_total / total_equipos, 1)

    # Calcular contribución ponderada de cada componente
    contribucion_estado = promedio_estado * 0.30
    contribucion_calibraciones = promedio_calibraciones * 0.25
    contribucion_mantenimientos = promedio_mantenimientos * 0.25
    contribucion_comprobaciones = promedio_comprobaciones * 0.20

    # Ejemplo de cálculo para mostrar transparencia
    calculo_ejemplo = f"({promedio_estado}×30% + {promedio_calibraciones}×25% + {promedio_mantenimientos}×25% + {promedio_comprobaciones}×20%) = {salud_porcentaje}%"

    # Determinar estado general
    if salud_porcentaje >= 80:
        estado = 'ÓPTIMO'
    elif salud_porcentaje >= 60:
        estado = 'BUENO'
    elif salud_porcentaje >= 40:
        estado = 'EN RIESGO'
    else:
        estado = 'CRÍTICO'

    return {
        'salud_general_porcentaje': salud_porcentaje,
        'salud_general_estado': estado,
        'equipos_saludables': equipos_saludables,
        'equipos_en_riesgo': equipos_en_riesgo,
        'equipos_criticos': equipos_criticos,
        'total_equipos_salud': total_equipos,
        'chart_data': [equipos_saludables, equipos_en_riesgo, equipos_criticos],
        'formula_detalle': {
            'peso_estado': 30,
            'peso_calibraciones': 25,
            'peso_mantenimientos': 25,
            'peso_comprobaciones': 20,
            'puntuacion_estado': promedio_estado,
            'puntuacion_calibraciones': promedio_calibraciones,
            'puntuacion_mantenimientos': promedio_mantenimientos,
            'puntuacion_comprobaciones': promedio_comprobaciones,
            'contribucion_estado': round(contribucion_estado, 1),
            'contribucion_calibraciones': round(contribucion_calibraciones, 1),
            'contribucion_mantenimientos': round(contribucion_mantenimientos, 1),
            'contribucion_comprobaciones': round(contribucion_comprobaciones, 1),
            'calculo_ejemplo': calculo_ejemplo
        }
    }


def _calcular_cumplimiento(equipos_para_dashboard, current_year, today):
    """
    PILAR 2: Cumplimiento
    Mide el desempeño de la gestión - ¿Actividades a tiempo?

    IMPORTANTE: Usa la MISMA lógica de proyección que Dashboard
    - Proyecciones basadas en última actividad real (no teóricas)
    - Jerarquía: última actividad → última calibración → fecha_adquisición
    """
    # Obtener actividades proyectadas usando la misma función de Dashboard
    actividades_calibracion = get_projected_activities_for_year(
        equipos_para_dashboard,
        'calibracion',
        current_year,
        today
    )

    actividades_mantenimiento = get_projected_activities_for_year(
        equipos_para_dashboard,
        'mantenimiento',
        current_year,
        today
    )

    actividades_comprobacion = get_projected_activities_for_year(
        equipos_para_dashboard,
        'comprobacion',
        current_year,
        today
    )

    # Contar actividades programadas para el año
    total_programadas = (
        len(actividades_calibracion) +
        len(actividades_mantenimiento) +
        len(actividades_comprobacion)
    )

    # Contar actividades realizadas
    total_realizadas_a_tiempo = 0

    # Calibraciones realizadas
    for actividad in actividades_calibracion:
        if actividad['status'] == 'Realizado':
            total_realizadas_a_tiempo += 1

    # Mantenimientos realizados
    for actividad in actividades_mantenimiento:
        if actividad['status'] == 'Realizado':
            total_realizadas_a_tiempo += 1

    # Comprobaciones realizadas
    for actividad in actividades_comprobacion:
        if actividad['status'] == 'Realizado':
            total_realizadas_a_tiempo += 1

    # Calcular porcentaje de cumplimiento
    if total_programadas > 0:
        cumplimiento_porcentaje = round((total_realizadas_a_tiempo / total_programadas) * 100, 1)
    else:
        cumplimiento_porcentaje = 100.0  # Sin actividades programadas = 100% cumplimiento

    # Determinar estado
    if cumplimiento_porcentaje >= 90:
        estado = 'EXCELENTE'
    elif cumplimiento_porcentaje >= 80:
        estado = 'BUENO'
    elif cumplimiento_porcentaje >= 70:
        estado = 'REGULAR'
    else:
        estado = 'DEFICIENTE'

    return {
        'cumplimiento_porcentaje': cumplimiento_porcentaje,
        'cumplimiento_estado': estado,
        'actividades_programadas': total_programadas,
        'actividades_realizadas': total_realizadas_a_tiempo,
        'actividades_pendientes': total_programadas - total_realizadas_a_tiempo,
        'chart_data': [total_realizadas_a_tiempo, total_programadas - total_realizadas_a_tiempo],
        'formula_cumplimiento': {
            'actividades_completadas': total_realizadas_a_tiempo,
            'actividades_programadas': total_programadas,
            'calculo_ejemplo': f"({total_realizadas_a_tiempo} ÷ {total_programadas}) × 100 = {cumplimiento_porcentaje}%" if total_programadas > 0 else "Sin actividades programadas = 100%"
        }
    }


def _calcular_eficiencia_operacional(equipos_queryset, equipos_para_dashboard):
    """
    PILAR 3: Eficiencia Operacional
    Combina disponibilidad con uso efectivo
    """
    total_equipos = equipos_queryset.count()
    equipos_disponibles = equipos_para_dashboard.count()  # Excluye De Baja e Inactivo

    if total_equipos == 0:
        return {
            'eficiencia_porcentaje': 0,
            'eficiencia_estado': 'CRÍTICO',
            'equipos_disponibles': 0,
            'equipos_no_disponibles': 0,
            'disponibilidad_porcentaje': 0
        }

    # Calcular disponibilidad
    disponibilidad_porcentaje = round((equipos_disponibles / total_equipos) * 100, 1)

    # Por ahora, eficiencia = disponibilidad (se puede expandir con más métricas)
    eficiencia_porcentaje = disponibilidad_porcentaje

    # Determinar estado
    if eficiencia_porcentaje >= 95:
        estado = 'ÓPTIMO'
    elif eficiencia_porcentaje >= 85:
        estado = 'BUENO'
    elif eficiencia_porcentaje >= 70:
        estado = 'REGULAR'
    else:
        estado = 'DEFICIENTE'

    return {
        'eficiencia_porcentaje': eficiencia_porcentaje,
        'eficiencia_estado': estado,
        'equipos_disponibles': equipos_disponibles,
        'equipos_no_disponibles': total_equipos - equipos_disponibles,
        'disponibilidad_porcentaje': disponibilidad_porcentaje,
        'total_equipos_eficiencia': total_equipos,
        'formula_eficiencia': {
            'equipos_disponibles': equipos_disponibles,
            'total_equipos': total_equipos,
            'equipos_activos': equipos_disponibles,  # Equipos en estado Activo/Operativo
            'equipos_baja_inactivo': total_equipos - equipos_disponibles,  # Equipos De Baja/Inactivo
            'calculo_ejemplo': f"({equipos_disponibles} ÷ {total_equipos}) × 100 = {eficiencia_porcentaje}%" if total_equipos > 0 else "Sin equipos registrados",
            'componentes': {
                'disponibilidad': {'peso': 100, 'valor': disponibilidad_porcentaje, 'descripcion': 'Equipos Activos vs Total'},
                # Para futuras expansiones se pueden agregar más componentes como:
                # 'utilizacion': {'peso': 0, 'valor': 0, 'descripcion': 'Uso efectivo de equipos'},
                # 'cronograma': {'peso': 0, 'valor': 0, 'descripcion': 'Cumplimiento de horarios'}
            }
        }
    }


def _get_actividades_criticas(equipos_para_dashboard, today):
    """
    Obtiene actividades críticas usando la misma lógica del dashboard técnico
    """
    fecha_limite_urgente = today + timedelta(days=7)  # Próximos 7 días

    # Calibraciones críticas
    cal_vencidas = equipos_para_dashboard.filter(
        proxima_calibracion__lt=today
    ).values('codigo_interno', 'nombre', 'proxima_calibracion')

    cal_urgentes = equipos_para_dashboard.filter(
        proxima_calibracion__gte=today,
        proxima_calibracion__lte=fecha_limite_urgente
    ).values('codigo_interno', 'nombre', 'proxima_calibracion')

    # Mantenimientos críticos
    mant_vencidos = equipos_para_dashboard.filter(
        proximo_mantenimiento__lt=today
    ).values('codigo_interno', 'nombre', 'proximo_mantenimiento')

    mant_urgentes = equipos_para_dashboard.filter(
        proximo_mantenimiento__gte=today,
        proximo_mantenimiento__lte=fecha_limite_urgente
    ).values('codigo_interno', 'nombre', 'proximo_mantenimiento')

    # Comprobaciones críticas
    comp_vencidas = equipos_para_dashboard.filter(
        proxima_comprobacion__lt=today
    ).values('codigo_interno', 'nombre', 'proxima_comprobacion')

    comp_urgentes = equipos_para_dashboard.filter(
        proxima_comprobacion__gte=today,
        proxima_comprobacion__lte=fecha_limite_urgente
    ).values('codigo_interno', 'nombre', 'proxima_comprobacion')

    return {
        'calibraciones_vencidas': list(cal_vencidas),
        'calibraciones_urgentes': list(cal_urgentes),
        'mantenimientos_vencidos': list(mant_vencidos),
        'mantenimientos_urgentes': list(mant_urgentes),
        'comprobaciones_vencidas': list(comp_vencidas),
        'comprobaciones_urgentes': list(comp_urgentes),
    }


def _generar_recomendaciones(salud_data, cumplimiento_data, eficiencia_data, actividades_criticas):
    """
    Genera recomendaciones específicas basadas en las métricas
    """
    recomendaciones = []

    # Recomendaciones por Salud del Equipo
    if salud_data['salud_general_porcentaje'] < 60:
        recomendaciones.append({
            'tipo': 'CRÍTICO',
            'titulo': 'Salud del Equipo Crítica',
            'descripcion': f"Solo {salud_data['equipos_saludables']} de {salud_data['total_equipos_salud']} equipos están en óptimas condiciones.",
            'accion': 'Priorizar calibraciones y mantenimientos vencidos inmediatamente.'
        })

    # Recomendaciones por Cumplimiento
    if cumplimiento_data['cumplimiento_porcentaje'] < 80:
        recomendaciones.append({
            'tipo': 'IMPORTANTE',
            'titulo': 'Bajo Cumplimiento de Actividades',
            'descripcion': f"Solo {cumplimiento_data['cumplimiento_porcentaje']}% de actividades realizadas a tiempo.",
            'accion': f"Completar {cumplimiento_data['actividades_pendientes']} actividades pendientes este período."
        })

    # Recomendaciones por Eficiencia
    if eficiencia_data['eficiencia_porcentaje'] < 85:
        recomendaciones.append({
            'tipo': 'MEJORA',
            'titulo': 'Oportunidad de Eficiencia',
            'descripcion': f"Disponibilidad operacional del {eficiencia_data['eficiencia_porcentaje']}%.",
            'accion': f"Revisar {eficiencia_data['equipos_no_disponibles']} equipos no disponibles."
        })

    # Recomendaciones por actividades críticas
    total_vencidas = (len(actividades_criticas['calibraciones_vencidas']) +
                     len(actividades_criticas['mantenimientos_vencidos']) +
                     len(actividades_criticas['comprobaciones_vencidas']))

    if total_vencidas > 0:
        recomendaciones.append({
            'tipo': 'URGENTE',
            'titulo': 'Actividades Vencidas',
            'descripcion': f"{total_vencidas} actividades críticas vencidas requieren atención inmediata.",
            'accion': 'Revisar lista de actividades vencidas y programar ejecución.'
        })

    return recomendaciones


def _panel_decisiones_empresa(request, today, current_year, empresa_override=None):
    """
    Panel de Decisiones para GERENCIA de empresa individual
    Enfoque: Táctica operacional - "Qué debo hacer hoy"

    empresa_override: Permite al superusuario ver el panel de una empresa específica
    """
    user = request.user
    empresa = empresa_override if empresa_override else user.empresa

    # Usar la misma lógica del dashboard técnico
    equipos_queryset = Equipo.objects.filter(empresa=empresa)
    equipos_para_dashboard = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

    # 1. SALUD DEL EQUIPO (Pilar 1)
    salud_equipo_data = _calcular_salud_equipo(equipos_para_dashboard, today)

    # 2. CUMPLIMIENTO (Pilar 2)
    cumplimiento_data = _calcular_cumplimiento(equipos_para_dashboard, current_year, today)

    # 3. EFICIENCIA OPERACIONAL (Pilar 3)
    eficiencia_data = _calcular_eficiencia_operacional(equipos_queryset, equipos_para_dashboard)

    # Actividades críticas (usando lógica del dashboard técnico)
    actividades_criticas = _get_actividades_criticas(equipos_para_dashboard, today)

    # Recomendaciones específicas
    recomendaciones = _generar_recomendaciones(salud_equipo_data, cumplimiento_data, eficiencia_data, actividades_criticas)

    # 4. ANÁLISIS FINANCIERO (NUEVO) - Gasto YTD y Proyección
    analisis_financiero = calcular_analisis_financiero_empresa(empresa, current_year, today)
    proyeccion_costos = calcular_proyeccion_costos_empresa(empresa, current_year + 1)

    # Calcular variación proyectada con desglose
    if analisis_financiero['gasto_ytd_total'] > 0:
        variacion_porcentaje = round(((proyeccion_costos['proyeccion_gasto_proximo_año'] / analisis_financiero['gasto_ytd_total']) * 100) - 100, 1)
        diferencia_absoluta = proyeccion_costos['proyeccion_gasto_proximo_año'] - analisis_financiero['gasto_ytd_total']
    else:
        variacion_porcentaje = 0
        diferencia_absoluta = 0

    # Fórmulas detalladas para desgloses interactivos
    formula_gastos_reales = {
        'total': analisis_financiero['gasto_ytd_total'],
        'calibraciones': analisis_financiero['costos_calibracion_ytd'],
        'mantenimientos': analisis_financiero['costos_mantenimiento_ytd'],
        'comprobaciones': analisis_financiero['costos_comprobacion_ytd'],
        'porcentaje_cal': analisis_financiero['porcentaje_calibracion'],
        'porcentaje_mant': analisis_financiero['porcentaje_mantenimiento'],
        'porcentaje_comp': analisis_financiero['porcentaje_comprobacion'],
        'periodo': f"Enero-{today.strftime('%B')} {current_year}",
        'calculo_ejemplo': f"${analisis_financiero['costos_calibracion_ytd']:,.0f} + ${analisis_financiero['costos_mantenimiento_ytd']:,.0f} + ${analisis_financiero['costos_comprobacion_ytd']:,.0f} = ${analisis_financiero['gasto_ytd_total']:,.0f} COP"
    }

    formula_presupuesto = {
        'total_proyectado': proyeccion_costos['proyeccion_gasto_proximo_año'],
        'actividades_proyectadas': proyeccion_costos['actividades_proyectadas_total'],
        'año_proyeccion': current_year + 1,
        'metodologia': 'Basado en frecuencias de equipos y costos históricos por marca/modelo',
        'calculo_ejemplo': f"{proyeccion_costos['actividades_proyectadas_total']} actividades programadas × costos históricos promedio = ${proyeccion_costos['proyeccion_gasto_proximo_año']:,.0f} COP",
        'exclusiones': 'No incluye mantenimientos correctivos no programados'
    }

    formula_variacion = {
        'proyeccion_2026': proyeccion_costos['proyeccion_gasto_proximo_año'],
        'gasto_ytd_2025': analisis_financiero['gasto_ytd_total'],
        'variacion_porcentaje': variacion_porcentaje,
        'diferencia_absoluta': diferencia_absoluta,
        'calculo_ejemplo': f"(${proyeccion_costos['proyeccion_gasto_proximo_año']:,.0f} ÷ ${analisis_financiero['gasto_ytd_total']:,.0f}) × 100 - 100 = {variacion_porcentaje}%" if analisis_financiero['gasto_ytd_total'] > 0 else "Sin datos del año actual para comparar",
        'interpretacion': 'Incremento esperado' if variacion_porcentaje > 10 else 'Reducción esperada' if variacion_porcentaje < -10 else 'Gastos similares entre años'
    }

    # 5. NUEVAS MÉTRICAS DE INTELIGENCIA EMPRESARIAL
    alertas_predictivas = calcular_alertas_predictivas(empresa, today)
    roi_rentabilidad = calcular_roi_rentabilidad(empresa, current_year)
    tendencias_historicas = calcular_tendencias_historicas(empresa, current_year)
    compliance_iso9001 = calcular_compliance_iso9001(empresa, today)
    optimizacion_cronogramas = calcular_optimizacion_cronogramas(empresa, today)

    context = {
        'titulo_pagina': f'Panel de Decisiones - {empresa.nombre}',
        'perspectiva': 'empresa',
        'empresa': empresa,
        'today': today,
        'current_year': current_year,

        # Las 3 Métricas Pilares
        **salud_equipo_data,
        **cumplimiento_data,
        **eficiencia_data,

        # Datos para acción inmediata
        'actividades_criticas': actividades_criticas,
        'recomendaciones': recomendaciones,

        # ANÁLISIS FINANCIERO (NUEVO)
        **analisis_financiero,
        **proyeccion_costos,

        # Fórmulas financieras detalladas
        'formula_gastos_reales': formula_gastos_reales,
        'formula_presupuesto': formula_presupuesto,
        'formula_variacion': formula_variacion,

        # NUEVAS MÉTRICAS DE INTELIGENCIA EMPRESARIAL
        'alertas_predictivas': alertas_predictivas,
        'roi_rentabilidad': roi_rentabilidad,
        'tendencias_historicas': tendencias_historicas,
        'compliance_iso9001': compliance_iso9001,
        'optimizacion_cronogramas': optimizacion_cronogramas,

        # Gráficos JSON
        'salud_chart_data': json.dumps(decimal_to_float(salud_equipo_data.get('chart_data', []))),
        'cumplimiento_chart_data': json.dumps(decimal_to_float(cumplimiento_data.get('chart_data', []))),
        'costos_chart_data': json.dumps(decimal_to_float([
            analisis_financiero['costos_calibracion_ytd'],
            analisis_financiero['costos_mantenimiento_ytd'],
            analisis_financiero['costos_comprobacion_ytd']
        ])),
        'tendencias_chart_data': json.dumps([{
            'mes': item['nombre_mes'],
            'gasto': float(item['gasto_total']),
            'actividades': item['actividades']
        } for item in tendencias_historicas['datos_mensuales']]),
    }

    return render(request, 'core/panel_decisiones.html', context)


def _panel_decisiones_sam(request, today, current_year):
    """
    Panel de Decisiones para SUPERUSERS SAM
    Enfoque: Estratégico multi-empresa - "Cómo está el negocio"
    """
    from django.db.models import Sum, Count, Q

    # Filtrado por empresa para superusuarios
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.filter(is_deleted=False).order_by('nombre')

    if selected_company_id:
        empresas_queryset = empresas_disponibles.filter(id=selected_company_id)
    else:
        empresas_queryset = empresas_disponibles

    # Agregaciones multi-empresa usando las mismas métricas pilares
    total_empresas = empresas_queryset.count()

    # Métricas agregadas de todas las empresas
    salud_agregada = {'equipos_saludables': 0, 'equipos_criticos': 0, 'total_equipos_salud': 0}
    cumplimiento_agregado = {'actividades_realizadas': 0, 'actividades_programadas': 0}
    eficiencia_agregada = {'equipos_disponibles': 0, 'equipos_no_disponibles': 0}

    metricas_por_empresa = []

    for empresa in empresas_queryset:
        equipos_queryset = Equipo.objects.filter(empresa=empresa)
        equipos_para_dashboard = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

        # Calcular métricas por empresa usando las mismas funciones
        salud_empresa = _calcular_salud_equipo(equipos_para_dashboard, today)
        cumplimiento_empresa = _calcular_cumplimiento(equipos_para_dashboard, current_year, today)
        eficiencia_empresa = _calcular_eficiencia_operacional(equipos_queryset, equipos_para_dashboard)

        # Agregar a totales
        salud_agregada['equipos_saludables'] += salud_empresa['equipos_saludables']
        salud_agregada['equipos_criticos'] += salud_empresa['equipos_criticos']
        salud_agregada['total_equipos_salud'] += salud_empresa['total_equipos_salud']

        cumplimiento_agregado['actividades_realizadas'] += cumplimiento_empresa['actividades_realizadas']
        cumplimiento_agregado['actividades_programadas'] += cumplimiento_empresa['actividades_programadas']

        eficiencia_agregada['equipos_disponibles'] += eficiencia_empresa['equipos_disponibles']
        eficiencia_agregada['equipos_no_disponibles'] += eficiencia_empresa['equipos_no_disponibles']

        # Guardar métricas por empresa para el detalle
        metricas_por_empresa.append({
            'empresa': empresa,
            'salud_porcentaje': salud_empresa['salud_general_porcentaje'],
            'salud_estado': salud_empresa['salud_general_estado'],
            'cumplimiento_porcentaje': cumplimiento_empresa['cumplimiento_porcentaje'],
            'cumplimiento_estado': cumplimiento_empresa['cumplimiento_estado'],
            'eficiencia_porcentaje': eficiencia_empresa['eficiencia_porcentaje'],
            'eficiencia_estado': eficiencia_empresa['eficiencia_estado'],
            'total_equipos': salud_empresa['total_equipos_salud']
        })

    # Calcular métricas consolidadas
    if salud_agregada['total_equipos_salud'] > 0:
        salud_general_porcentaje = round((salud_agregada['equipos_saludables'] / salud_agregada['total_equipos_salud']) * 100, 1)
    else:
        salud_general_porcentaje = 0

    if cumplimiento_agregado['actividades_programadas'] > 0:
        cumplimiento_general_porcentaje = round((cumplimiento_agregado['actividades_realizadas'] / cumplimiento_agregado['actividades_programadas']) * 100, 1)
    else:
        cumplimiento_general_porcentaje = 100

    total_equipos_agregado = salud_agregada['total_equipos_salud']
    if total_equipos_agregado > 0:
        eficiencia_general_porcentaje = round((eficiencia_agregada['equipos_disponibles'] / total_equipos_agregado) * 100, 1)
    else:
        eficiencia_general_porcentaje = 0

    # Datos financieros básicos
    ingresos_anuales = Decimal('0')
    costos_totales = Decimal('0')
    margen_bruto = Decimal('0')

    try:
        # Calcular ingresos reales empresa por empresa
        for empresa in empresas_queryset:
            ingresos_anuales += empresa.get_ingresos_anuales_reales()

        # Costos operativos del año
        costos_cal = Calibracion.objects.filter(
            equipo__empresa__in=empresas_queryset,
            fecha_calibracion__year=current_year
        ).aggregate(total=Sum('costo_calibracion'))['total'] or Decimal('0')

        costos_mant = Mantenimiento.objects.filter(
            equipo__empresa__in=empresas_queryset,
            fecha_mantenimiento__year=current_year
        ).aggregate(total=Sum('costo_sam_interno'))['total'] or Decimal('0')

        costos_comp = Comprobacion.objects.filter(
            equipo__empresa__in=empresas_queryset,
            fecha_comprobacion__year=current_year
        ).aggregate(total=Sum('costo_comprobacion'))['total'] or Decimal('0')

        costos_totales = costos_cal + costos_mant + costos_comp
        margen_bruto = ingresos_anuales - costos_totales

    except Exception as e:
        print(f"Error calculando datos financieros: {e}")

    # MÉTRICAS FINANCIERAS DEL NEGOCIO SAM (NUEVO)
    metricas_financieras_sam = calcular_metricas_financieras_sam(empresas_queryset, current_year, current_year - 1)

    # Crear desgloses de fórmulas para los 3 pilares (perspectiva SAM agregada)
    formula_detalle_sam = {
        'peso_estado': 30,
        'peso_calibraciones': 25,
        'peso_mantenimientos': 25,
        'peso_comprobaciones': 20,
        'puntuacion_estado': round((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100, 1),
        'puntuacion_calibraciones': round((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100, 1),  # Simplificado para vista agregada
        'puntuacion_mantenimientos': round((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100, 1),
        'puntuacion_comprobaciones': round((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100, 1),
        'contribucion_estado': round(((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100) * 0.30, 1),
        'contribucion_calibraciones': round(((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100) * 0.25, 1),
        'contribucion_mantenimientos': round(((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100) * 0.25, 1),
        'contribucion_comprobaciones': round(((salud_agregada['equipos_saludables'] / max(salud_agregada['total_equipos_salud'], 1)) * 100) * 0.20, 1),
        'calculo_ejemplo': f"Promedio ponderado de {empresas_queryset.count()} empresas = {salud_general_porcentaje}%"
    }

    formula_cumplimiento_sam = {
        'actividades_completadas': cumplimiento_agregado['actividades_realizadas'],
        'actividades_programadas': cumplimiento_agregado['actividades_programadas'],
        'calculo_ejemplo': f"({cumplimiento_agregado['actividades_realizadas']} ÷ {cumplimiento_agregado['actividades_programadas']}) × 100 = {cumplimiento_general_porcentaje}%" if cumplimiento_agregado['actividades_programadas'] > 0 else "Sin actividades programadas = 100%"
    }

    formula_eficiencia_sam = {
        'equipos_disponibles': eficiencia_agregada['equipos_disponibles'],
        'total_equipos': total_equipos_agregado,
        'equipos_activos': eficiencia_agregada['equipos_disponibles'],
        'equipos_baja_inactivo': eficiencia_agregada['equipos_no_disponibles'],
        'calculo_ejemplo': f"({eficiencia_agregada['equipos_disponibles']} ÷ {total_equipos_agregado}) × 100 = {eficiencia_general_porcentaje}%" if total_equipos_agregado > 0 else "Sin equipos registrados",
        'componentes': {
            'disponibilidad': {'peso': 100, 'valor': eficiencia_general_porcentaje, 'descripcion': 'Equipos Activos vs Total Agregado'}
        }
    }

    # Agregar desgloses de fórmulas para métricas SAM
    mes_actual = today.month
    formulas_sam = {
        'ingresos_formula': {
            'valor_total': metricas_financieras_sam['ingreso_ytd_actual'],
            'num_empresas': empresas_queryset.count(),
            'calculo_ejemplo': f"Suma de pagos recibidos de {empresas_queryset.count()} empresas activas = ${metricas_financieras_sam['ingreso_ytd_actual']:,.0f} COP",
            'periodo': f"Enero-{today.strftime('%B')} {current_year}"
        },
        'crecimiento_formula': {
            'ingreso_actual': metricas_financieras_sam['ingreso_ytd_actual'],
            'ingreso_anterior': metricas_financieras_sam['ingreso_año_anterior'],
            'diferencia': metricas_financieras_sam['ingreso_ytd_actual'] - metricas_financieras_sam['ingreso_año_anterior'],
            'calculo_ejemplo': f"(${metricas_financieras_sam['ingreso_ytd_actual']:,.0f} - ${metricas_financieras_sam['ingreso_año_anterior']:,.0f}) ÷ ${metricas_financieras_sam['ingreso_año_anterior']:,.0f} × 100 = {metricas_financieras_sam['crecimiento_ingresos_porcentaje']}%" if metricas_financieras_sam['ingreso_año_anterior'] > 0 else "Sin datos del año anterior para comparar"
        },
        'proyeccion_formula': {
            'ingreso_ytd': metricas_financieras_sam['ingreso_ytd_actual'],
            'mes_actual': mes_actual,
            'proyeccion': metricas_financieras_sam['proyeccion_fin_año'],
            'calculo_ejemplo': f"${metricas_financieras_sam['ingreso_ytd_actual']:,.0f} × (12 ÷ {mes_actual}) = ${metricas_financieras_sam['proyeccion_fin_año']:,.0f} COP" if mes_actual > 0 else "Proyección no disponible"
        }
    }

    # MÉTRICAS DE INTELIGENCIA EMPRESARIAL (usando filtro de empresa)
    # Si hay una empresa seleccionada, usar métricas de esa empresa
    # Si no, agregar métricas de todas las empresas
    if selected_company_id and empresas_queryset.count() == 1:
        # Vista filtrada por una empresa específica
        empresa_filtrada = empresas_queryset.first()
        alertas_predictivas = calcular_alertas_predictivas(empresa_filtrada, today)
        roi_rentabilidad = calcular_roi_rentabilidad(empresa_filtrada, current_year)
        tendencias_historicas = calcular_tendencias_historicas(empresa_filtrada, current_year)
        compliance_iso9001 = calcular_compliance_iso9001(empresa_filtrada, today)
        optimizacion_cronogramas = calcular_optimizacion_cronogramas(empresa_filtrada, today)
    else:
        # Vista agregada de todas las empresas
        alertas_predictivas = _calcular_alertas_predictivas_agregadas(empresas_queryset, today)
        roi_rentabilidad = _calcular_roi_rentabilidad_agregado(empresas_queryset, current_year)
        tendencias_historicas = _calcular_tendencias_historicas_agregadas(empresas_queryset, current_year)
        compliance_iso9001 = _calcular_compliance_iso9001_agregado(empresas_queryset, today)
        optimizacion_cronogramas = _calcular_optimizacion_cronogramas_agregado(empresas_queryset, today)

    # Recomendaciones estratégicas
    recomendaciones_sam = []

    if salud_general_porcentaje < 70:
        recomendaciones_sam.append({
            'tipo': 'ESTRATÉGICO',
            'titulo': 'Salud General del Parque de Equipos Crítica',
            'descripcion': f'Solo {salud_general_porcentaje}% del parque de equipos está en condiciones óptimas',
            'accion': 'Implementar programa corporativo de recuperación de equipos críticos'
        })

    if cumplimiento_general_porcentaje < 75:
        recomendaciones_sam.append({
            'tipo': 'OPERATIVO',
            'titulo': 'Oportunidad de Mejora en Cumplimiento',
            'descripcion': f'Cumplimiento general del {cumplimiento_general_porcentaje}%',
            'accion': 'Revisar procesos y capacitación del equipo técnico'
        })

    if eficiencia_general_porcentaje < 90:
        recomendaciones_sam.append({
            'tipo': 'FINANCIERO',
            'titulo': 'Optimización de Disponibilidad',
            'descripcion': f'Eficiencia operacional del {eficiencia_general_porcentaje}%',
            'accion': 'Analizar equipos no disponibles para recuperar capacidad productiva'
        })

    context = {
        'titulo_pagina': 'Panel de Decisiones SAM - Vista Estratégica',
        'perspectiva': 'sam',
        'today': today,
        'current_year': current_year,

        # Selector de empresa
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,

        # Métricas consolidadas (3 pilares)
        'salud_general_porcentaje': salud_general_porcentaje,
        'cumplimiento_general_porcentaje': cumplimiento_general_porcentaje,
        'eficiencia_general_porcentaje': eficiencia_general_porcentaje,

        # Totales agregados
        'total_empresas': total_empresas,
        'total_equipos_gestionados': total_equipos_agregado,
        'equipos_saludables_total': salud_agregada['equipos_saludables'],
        'equipos_criticos_total': salud_agregada['equipos_criticos'],
        'equipos_en_riesgo_total': salud_agregada['total_equipos_salud'] - salud_agregada['equipos_saludables'] - salud_agregada['equipos_criticos'],
        'actividades_realizadas_total': cumplimiento_agregado['actividades_realizadas'],
        'actividades_programadas_total': cumplimiento_agregado['actividades_programadas'],

        # Variables adicionales para coherencia con template
        'total_equipos_salud': total_equipos_agregado,
        'equipos_saludables': salud_agregada['equipos_saludables'],
        'equipos_criticos': salud_agregada['equipos_criticos'],
        'equipos_en_riesgo': salud_agregada['total_equipos_salud'] - salud_agregada['equipos_saludables'] - salud_agregada['equipos_criticos'],
        'actividades_realizadas': cumplimiento_agregado['actividades_realizadas'],
        'actividades_programadas': cumplimiento_agregado['actividades_programadas'],
        'cumplimiento_porcentaje': cumplimiento_general_porcentaje,
        'cumplimiento_estado': 'EXCELENTE' if cumplimiento_general_porcentaje >= 90 else 'BUENO' if cumplimiento_general_porcentaje >= 80 else 'REGULAR' if cumplimiento_general_porcentaje >= 70 else 'DEFICIENTE',
        'eficiencia_porcentaje': eficiencia_general_porcentaje,
        'eficiencia_estado': 'ÓPTIMO' if eficiencia_general_porcentaje >= 95 else 'BUENO' if eficiencia_general_porcentaje >= 85 else 'REGULAR' if eficiencia_general_porcentaje >= 70 else 'DEFICIENTE',
        'salud_general_estado': 'ÓPTIMO' if salud_general_porcentaje >= 80 else 'BUENO' if salud_general_porcentaje >= 60 else 'EN RIESGO' if salud_general_porcentaje >= 40 else 'CRÍTICO',

        # Datos financieros
        'ingresos_anuales': ingresos_anuales,
        'costos_totales': costos_totales,
        'margen_bruto': margen_bruto,
        'margen_porcentaje': round((margen_bruto / ingresos_anuales * 100), 1) if ingresos_anuales > 0 else 0,

        # Detalle por empresa
        'metricas_por_empresa': metricas_por_empresa,

        # MÉTRICAS FINANCIERAS DEL NEGOCIO SAM (NUEVO)
        **metricas_financieras_sam,

        # Fórmulas SAM para desgloses
        'formulas_sam': formulas_sam,

        # Fórmulas de los 3 pilares para SAM (agregadas)
        'formula_detalle': formula_detalle_sam,
        'formula_cumplimiento': formula_cumplimiento_sam,
        'formula_eficiencia': formula_eficiencia_sam,

        # Recomendaciones estratégicas
        'recomendaciones_sam': recomendaciones_sam,

        # MÉTRICAS DE INTELIGENCIA EMPRESARIAL
        'alertas_predictivas': alertas_predictivas,
        'roi_rentabilidad': roi_rentabilidad,
        'tendencias_historicas': tendencias_historicas,
        'compliance_iso9001': compliance_iso9001,
        'optimizacion_cronogramas': optimizacion_cronogramas,

        # Gráficos JSON
        'salud_consolidada_chart': json.dumps(decimal_to_float([salud_agregada['equipos_saludables'], salud_agregada['equipos_criticos']])),
        'cumplimiento_consolidado_chart': json.dumps(decimal_to_float([cumplimiento_agregado['actividades_realizadas'], cumplimiento_agregado['actividades_programadas'] - cumplimiento_agregado['actividades_realizadas']])),
        'crecimiento_ingresos_chart': json.dumps(decimal_to_float([metricas_financieras_sam['ingreso_año_anterior'], metricas_financieras_sam['ingreso_ytd_actual']])),
    }

    return render(request, 'core/panel_decisiones.html', context)


def _calcular_alertas_predictivas_agregadas(empresas_queryset, today):
    """Calcula alertas predictivas agregadas para múltiples empresas"""
    alertas_agregadas = {'alertas': {'vencidas': [], 'criticas': [], 'riesgo_alto': []}, 'total_alertas': 0}

    for empresa in empresas_queryset:
        alertas_empresa = calcular_alertas_predictivas(empresa, today)
        alertas_agregadas['alertas']['vencidas'].extend(alertas_empresa['alertas']['vencidas'])
        alertas_agregadas['alertas']['criticas'].extend(alertas_empresa['alertas']['criticas'])
        alertas_agregadas['alertas']['riesgo_alto'].extend(alertas_empresa['alertas']['riesgo_alto'])

    alertas_agregadas['total_alertas'] = (
        len(alertas_agregadas['alertas']['vencidas']) +
        len(alertas_agregadas['alertas']['criticas']) +
        len(alertas_agregadas['alertas']['riesgo_alto'])
    )

    return alertas_agregadas


def _calcular_roi_rentabilidad_agregado(empresas_queryset, current_year):
    """Calcula ROI y rentabilidad agregado para múltiples empresas"""
    total_preventivos = 0
    total_correctivos = 0
    costo_preventivos_total = 0
    costo_correctivos_total = 0

    for empresa in empresas_queryset:
        roi_empresa = calcular_roi_rentabilidad(empresa, current_year)
        total_preventivos += roi_empresa['count_preventivos']
        total_correctivos += roi_empresa['count_correctivos']
        costo_preventivos_total += roi_empresa['costo_preventivos']
        costo_correctivos_total += roi_empresa['costo_correctivos']

    # Calcular ROI agregado
    if costo_preventivos_total > 0:
        roi_porcentaje = round(((costo_correctivos_total - costo_preventivos_total) / costo_preventivos_total) * 100, 1)
        ahorro_total = costo_correctivos_total - costo_preventivos_total
    else:
        roi_porcentaje = 0
        ahorro_total = 0

    # Calcular ratio preventivo
    total_mantenimientos = total_preventivos + total_correctivos
    ratio_preventivo = round((total_preventivos / total_mantenimientos * 100), 1) if total_mantenimientos > 0 else 0

    # Evaluación del ratio
    if ratio_preventivo >= 80:
        evaluacion_ratio = 'EXCELENTE'
    elif ratio_preventivo >= 65:
        evaluacion_ratio = 'BUENO'
    elif ratio_preventivo >= 50:
        evaluacion_ratio = 'REGULAR'
    else:
        evaluacion_ratio = 'DEFICIENTE'

    return {
        'roi_porcentaje': roi_porcentaje,
        'ahorro_total': ahorro_total,
        'count_preventivos': total_preventivos,
        'count_correctivos': total_correctivos,
        'costo_preventivos': costo_preventivos_total,
        'costo_correctivos': costo_correctivos_total,
        'costo_promedio_preventivo': round(costo_preventivos_total / total_preventivos, 2) if total_preventivos > 0 else 0,
        'costo_promedio_correctivo': round(costo_correctivos_total / total_correctivos, 2) if total_correctivos > 0 else 0,
        'ratio_preventivo': ratio_preventivo,
        'evaluacion_ratio': evaluacion_ratio,
        'interpretacion_roi': 'Excelente retorno' if roi_porcentaje > 100 else 'Buen retorno' if roi_porcentaje > 50 else 'Revisar estrategia'
    }


def _calcular_tendencias_historicas_agregadas(empresas_queryset, current_year):
    """Calcula tendencias históricas agregadas para múltiples empresas"""
    from collections import defaultdict

    datos_mensuales_agregados = defaultdict(lambda: {'gasto_total': 0, 'actividades': 0})

    for empresa in empresas_queryset:
        tendencias_empresa = calcular_tendencias_historicas(empresa, current_year)
        for mes_data in tendencias_empresa['datos_mensuales']:
            mes_key = mes_data['nombre_mes']
            datos_mensuales_agregados[mes_key]['gasto_total'] += mes_data['gasto_total']
            datos_mensuales_agregados[mes_key]['actividades'] += mes_data['actividades']

    # Convertir a lista
    datos_mensuales = [
        {'nombre_mes': mes, 'gasto_total': data['gasto_total'], 'actividades': data['actividades']}
        for mes, data in sorted(datos_mensuales_agregados.items())
    ]

    # Calcular promedios y tendencias
    gastos = [d['gasto_total'] for d in datos_mensuales if d['gasto_total'] > 0]
    promedio_mensual = sum(gastos) / len(gastos) if gastos else 0

    # Mes más caro y más barato
    mes_mas_caro = max(datos_mensuales, key=lambda x: x['gasto_total']) if datos_mensuales else None
    datos_con_gasto = [d for d in datos_mensuales if d['gasto_total'] > 0]
    mes_mas_barato = min(datos_con_gasto, key=lambda x: x['gasto_total']) if datos_con_gasto else None

    # Calcular tendencia (últimos 3 meses vs promedio)
    if len(gastos) >= 3:
        ultimos_3_meses = gastos[-3:]
        promedio_ultimos_3 = sum(ultimos_3_meses) / 3
        tendencia_porcentaje = round(((promedio_ultimos_3 - promedio_mensual) / promedio_mensual) * 100, 1) if promedio_mensual > 0 else 0
        tendencia_direccion = 'ASCENDENTE' if tendencia_porcentaje > 10 else 'DESCENDENTE' if tendencia_porcentaje < -10 else 'ESTABLE'
    else:
        tendencia_porcentaje = 0
        tendencia_direccion = 'ESTABLE'

    return {
        'datos_mensuales': datos_mensuales,
        'promedio_mensual': promedio_mensual,
        'mes_mas_caro': mes_mas_caro,
        'mes_mas_barato': mes_mas_barato,
        'meses_con_datos': len(gastos),
        'tendencia_porcentaje': tendencia_porcentaje,
        'tendencia_direccion': tendencia_direccion
    }


def _calcular_compliance_iso9001_agregado(empresas_queryset, today):
    """Calcula compliance ISO 9001 agregado para múltiples empresas"""
    total_equipos = 0
    equipos_conformes = 0
    equipos_riesgo = 0
    equipos_no_conformes = 0
    no_conformidades_todas = []

    for empresa in empresas_queryset:
        compliance_empresa = calcular_compliance_iso9001(empresa, today)
        total_equipos += compliance_empresa['total_equipos']
        equipos_conformes += compliance_empresa['equipos_conformes']
        equipos_riesgo += compliance_empresa['equipos_riesgo']
        equipos_no_conformes += compliance_empresa['equipos_no_conformes']
        if compliance_empresa.get('no_conformidades'):
            no_conformidades_todas.extend(compliance_empresa['no_conformidades'])

    # Calcular score
    score_iso9001 = round((equipos_conformes / total_equipos * 100), 1) if total_equipos > 0 else 0

    # Evaluación
    if score_iso9001 >= 90:
        evaluacion = 'EXCELENTE'
    elif score_iso9001 >= 75:
        evaluacion = 'BUENO'
    elif score_iso9001 >= 60:
        evaluacion = 'REGULAR'
    else:
        evaluacion = 'DEFICIENTE'

    return {
        'score_iso9001': score_iso9001,
        'evaluacion': evaluacion,
        'total_equipos': total_equipos,
        'equipos_conformes': equipos_conformes,
        'equipos_riesgo': equipos_riesgo,
        'equipos_no_conformes': equipos_no_conformes,
        'no_conformidades': no_conformidades_todas[:10]  # Limitar a 10 para no sobrecargar
    }


def _calcular_optimizacion_cronogramas_agregado(empresas_queryset, today):
    """Calcula optimización de cronogramas agregado para múltiples empresas"""
    oportunidades_todas = []
    equipos_problematicos_todos = []
    ahorro_total = 0

    for empresa in empresas_queryset:
        optimizacion_empresa = calcular_optimizacion_cronogramas(empresa, today)
        if optimizacion_empresa.get('oportunidades_optimizacion'):
            oportunidades_todas.extend(optimizacion_empresa['oportunidades_optimizacion'])
            ahorro_total += optimizacion_empresa.get('ahorro_total_cronograma', 0)
        if optimizacion_empresa.get('equipos_problematicos'):
            equipos_problematicos_todos.extend(optimizacion_empresa['equipos_problematicos'])

    # Ordenar por ahorro (oportunidades) y por nivel de problema (equipos)
    oportunidades_todas.sort(key=lambda x: x.get('ahorro_estimado', 0), reverse=True)
    equipos_problematicos_todos.sort(key=lambda x: x.get('cantidad_correctivos', 0), reverse=True)

    return {
        'oportunidades_optimizacion': oportunidades_todas[:10],  # Top 10
        'equipos_problematicos': equipos_problematicos_todos[:10],  # Top 10
        'ahorro_total_cronograma': ahorro_total
    }


@login_required
@monitor_view
def get_equipos_salud_detalles(request):
    """
    API endpoint para obtener detalles de equipos clasificados por salud.
    Retorna equipos CRÍTICOS primero, luego EN RIESGO, luego SALUDABLES.
    """
    from django.http import JsonResponse

    user = request.user
    today = date.today()

    # Obtener empresa seleccionada
    empresa_id = request.GET.get('empresa_id')

    if not user.is_superuser:
        if not user.empresa:
            return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=400)
        empresa = user.empresa
    else:
        if not empresa_id:
            return JsonResponse({'error': 'empresa_id requerido'}, status=400)
        try:
            empresa = Empresa.objects.get(id=empresa_id, is_deleted=False)
        except Empresa.DoesNotExist:
            return JsonResponse({'error': 'Empresa no encontrada'}, status=404)

    # Obtener equipos
    equipos_queryset = Equipo.objects.filter(empresa=empresa)
    equipos_para_dashboard = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

    # Calcular puntuación de cada equipo
    equipos_detalles = []

    for equipo in equipos_para_dashboard:
        # 1. ESTADO DEL EQUIPO (30%)
        if equipo.estado in ['Activo', 'Operativo']:
            puntuacion_estado = 100
        else:
            puntuacion_estado = 0

        # 2. CALIBRACIONES (25%)
        if equipo.proxima_calibracion and equipo.proxima_calibracion >= today:
            puntuacion_calibraciones = 100
            estado_calibracion = 'Vigente'
        else:
            puntuacion_calibraciones = 0
            if equipo.proxima_calibracion:
                dias_vencida = (today - equipo.proxima_calibracion).days
                estado_calibracion = f'Vencida ({dias_vencida} días)'
            else:
                estado_calibracion = 'Sin programar'

        # 3. MANTENIMIENTOS (25%)
        if equipo.proximo_mantenimiento and equipo.proximo_mantenimiento >= today:
            puntuacion_mantenimientos = 100
            estado_mantenimiento = 'Vigente'
        else:
            puntuacion_mantenimientos = 0
            if equipo.proximo_mantenimiento:
                dias_vencido = (today - equipo.proximo_mantenimiento).days
                estado_mantenimiento = f'Vencido ({dias_vencido} días)'
            else:
                estado_mantenimiento = 'Sin programar'

        # 4. COMPROBACIONES (20%)
        if equipo.proxima_comprobacion and equipo.proxima_comprobacion >= today:
            puntuacion_comprobaciones = 100
            estado_comprobacion = 'Vigente'
        else:
            puntuacion_comprobaciones = 0
            if equipo.proxima_comprobacion:
                dias_vencida = (today - equipo.proxima_comprobacion).days
                estado_comprobacion = f'Vencida ({dias_vencida} días)'
            else:
                estado_comprobacion = 'Sin programar'

        # Calcular puntuación ponderada total
        puntuacion_total = (
            puntuacion_estado * 0.30 +
            puntuacion_calibraciones * 0.25 +
            puntuacion_mantenimientos * 0.25 +
            puntuacion_comprobaciones * 0.20
        )

        # Clasificar equipo
        if puntuacion_total >= 80:
            clasificacion = 'SALUDABLE'
            nivel_orden = 3
        elif puntuacion_total >= 40:
            clasificacion = 'EN RIESGO'
            nivel_orden = 2
        else:
            clasificacion = 'CRÍTICO'
            nivel_orden = 1

        equipos_detalles.append({
            'codigo_interno': equipo.codigo_interno,
            'nombre': equipo.nombre,
            'marca': equipo.marca or 'N/A',
            'modelo': equipo.modelo or 'N/A',
            'estado': equipo.estado,
            'puntuacion_total': round(puntuacion_total, 1),
            'clasificacion': clasificacion,
            'nivel_orden': nivel_orden,
            'detalles': {
                'estado_equipo': {
                    'puntuacion': puntuacion_estado,
                    'peso': 30,
                    'contribucion': round(puntuacion_estado * 0.30, 1)
                },
                'calibracion': {
                    'puntuacion': puntuacion_calibraciones,
                    'peso': 25,
                    'contribucion': round(puntuacion_calibraciones * 0.25, 1),
                    'estado': estado_calibracion,
                    'proxima_fecha': equipo.proxima_calibracion.strftime('%d/%m/%Y') if equipo.proxima_calibracion else 'N/A'
                },
                'mantenimiento': {
                    'puntuacion': puntuacion_mantenimientos,
                    'peso': 25,
                    'contribucion': round(puntuacion_mantenimientos * 0.25, 1),
                    'estado': estado_mantenimiento,
                    'proxima_fecha': equipo.proximo_mantenimiento.strftime('%d/%m/%Y') if equipo.proximo_mantenimiento else 'N/A'
                },
                'comprobacion': {
                    'puntuacion': puntuacion_comprobaciones,
                    'peso': 20,
                    'contribucion': round(puntuacion_comprobaciones * 0.20, 1),
                    'estado': estado_comprobacion,
                    'proxima_fecha': equipo.proxima_comprobacion.strftime('%d/%m/%Y') if equipo.proxima_comprobacion else 'N/A'
                }
            }
        })

    # Ordenar: CRÍTICOS primero (nivel_orden 1), luego EN RIESGO (2), luego SALUDABLES (3)
    # Dentro de cada nivel, ordenar por puntuación ascendente (los peores primero)
    equipos_detalles.sort(key=lambda x: (x['nivel_orden'], x['puntuacion_total']))

    return JsonResponse({
        'equipos': equipos_detalles,
        'totales': {
            'criticos': sum(1 for e in equipos_detalles if e['clasificacion'] == 'CRÍTICO'),
            'en_riesgo': sum(1 for e in equipos_detalles if e['clasificacion'] == 'EN RIESGO'),
            'saludables': sum(1 for e in equipos_detalles if e['clasificacion'] == 'SALUDABLE'),
            'total': len(equipos_detalles)
        }
    })