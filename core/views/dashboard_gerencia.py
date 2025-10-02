# core/views/dashboard_gerencia.py
# Dashboard de Gerencia Ejecutiva para SAM
# Sistema separado del dashboard operativo

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import Extract
from datetime import date, datetime, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import json

from ..models import (
    Empresa, Equipo, Calibracion, Mantenimiento,
    Comprobacion, CustomUser
)


def management_permission_required(view_func):
    """
    Decorador personalizado para verificar permisos de gestión.
    Solo permite acceso a superusers o usuarios con is_management_user=True
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')

        if not (request.user.is_superuser or request.user.is_management_user):
            messages.error(request, "No tienes permisos para acceder al Dashboard de Gerencia.")
            return redirect('core:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@management_permission_required
def dashboard_gerencia(request):
    """
    Dashboard de Gerencia Ejecutiva - Dos perspectivas:
    1. Superuser: Análisis de negocio SAM
    2. Management User: Análisis de valor para su empresa
    """
    user = request.user
    today = date.today()
    current_year = today.year
    previous_year = current_year - 1

    # Determinar perspectiva
    if user.is_superuser:
        # Vista SAM - Análisis de todos los clientes
        context = _get_sam_perspective_data(request, today, current_year, previous_year)
        template = 'core/dashboard_gerencia_sam.html'
    else:
        # Vista Cliente - Análisis de su empresa
        context = _get_client_perspective_data(request, today, current_year, previous_year)
        template = 'core/dashboard_gerencia_cliente.html'

    return render(request, template, context)


def _get_sam_perspective_data(request, today, current_year, previous_year):
    """
    Datos para perspectiva SAM (Superuser)
    """
    # Filtro de empresa opcional para superuser
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.filter(is_deleted=False).order_by('nombre')

    # Base queryset de empresas
    empresas_queryset = empresas_disponibles
    if selected_company_id:
        empresas_queryset = empresas_queryset.filter(id=selected_company_id)

    # Métricas financieras SAM
    ingresos_data = _calculate_sam_revenue_metrics(empresas_queryset, current_year, previous_year)

    # Análisis operativo SAM
    operational_data = _calculate_sam_operational_metrics(empresas_queryset, current_year, previous_year)

    # Análisis de clientes
    client_analysis = _calculate_sam_client_analysis(empresas_queryset)

    # Datos para gráficos
    charts_data = _get_sam_charts_data(empresas_queryset, current_year, previous_year)

    return {
        'titulo_pagina': 'Dashboard Gerencia SAM',
        'perspective': 'sam',
        'today': today,
        'now': timezone.now(),
        'current_year': current_year,
        'previous_year': previous_year,
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,
        **ingresos_data,
        **operational_data,
        **client_analysis,
        **charts_data
    }


def _get_client_perspective_data(request, today, current_year, previous_year):
    """
    Datos para perspectiva Cliente (Management User)
    """
    empresa = request.user.empresa
    if not empresa:
        return {
            'error': 'Usuario sin empresa asignada',
            'titulo_pagina': 'Dashboard Gerencia - Error'
        }

    # Métricas de inversión de la empresa
    investment_data = _calculate_client_investment_metrics(empresa, current_year, previous_year)

    # Análisis de valor del programa
    value_analysis = _calculate_client_value_analysis(empresa, current_year, previous_year)

    # Estado de compliance
    compliance_data = _calculate_client_compliance_metrics(empresa, today)

    # Datos para gráficos
    charts_data = _get_client_charts_data(empresa, current_year, previous_year)

    return {
        'titulo_pagina': f'Dashboard Gerencia - {empresa.nombre}',
        'perspective': 'client',
        'empresa': empresa,
        'today': today,
        'now': timezone.now(),
        'current_year': current_year,
        'previous_year': previous_year,
        **investment_data,
        **value_analysis,
        **compliance_data,
        **charts_data
    }


def _calculate_sam_revenue_metrics(empresas_queryset, current_year, previous_year):
    """
    Calcula métricas de ingresos para SAM
    """
    # Debug información
    print(f"DEBUG: Calculando métricas para {empresas_queryset.count()} empresas")

    # Ingresos anuales estimados
    ingresos_result = empresas_queryset.aggregate(total_anual=Sum('tarifa_mensual_sam'))
    print(f"DEBUG: Ingresos result: {ingresos_result}")

    ingresos_actuales = ingresos_result['total_anual'] or 0
    ingresos_actuales = float(ingresos_actuales) * 12  # Anualizar

    # Análisis de costos por actividad
    costos_calibracion = Calibracion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_calibracion__year=current_year
    ).aggregate(total=Sum('costo_calibracion'))['total'] or 0

    costos_mantenimiento = Mantenimiento.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_mantenimiento__year=current_year
    ).aggregate(
        total_cliente=Sum('costo'),
        total_sam=Sum('costo_sam_interno')
    )

    costos_comprobacion = Comprobacion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_comprobacion__year=current_year
    ).aggregate(total=Sum('costo_comprobacion'))['total'] or 0

    # Calcular márgenes
    costos_totales = (costos_calibracion +
                     (costos_mantenimiento['total_sam'] or 0) +
                     costos_comprobacion)

    margen_bruto = ingresos_actuales - costos_totales if ingresos_actuales > 0 else 0
    margen_porcentaje = (margen_bruto / ingresos_actuales * 100) if ingresos_actuales > 0 else 0

    # Comparación año anterior
    costos_previos = _get_previous_year_costs(empresas_queryset, previous_year)
    variacion_costos = ((costos_totales - costos_previos) / costos_previos * 100) if costos_previos > 0 else 0

    return {
        'ingresos_anuales': ingresos_actuales,
        'costos_calibracion': costos_calibracion,
        'costos_mantenimiento': costos_mantenimiento['total_cliente'] or 0,
        'costos_mantenimiento_sam': costos_mantenimiento['total_sam'] or 0,
        'costos_comprobacion': costos_comprobacion,
        'costos_totales': costos_totales,
        'margen_bruto': margen_bruto,
        'margen_porcentaje': round(margen_porcentaje, 1),
        'variacion_costos_porcentaje': round(variacion_costos, 1),
        'num_empresas_activas': empresas_queryset.count()
    }


def _calculate_sam_operational_metrics(empresas_queryset, current_year, previous_year):
    """
    Calcula métricas operativas para SAM
    """
    # Total de equipos gestionados
    total_equipos = Equipo.objects.filter(
        empresa__in=empresas_queryset,
        empresa__is_deleted=False
    ).count()

    # Productividad técnicos
    actividades_año = (
        Calibracion.objects.filter(
            equipo__empresa__in=empresas_queryset,
            fecha_calibracion__year=current_year
        ).count() +
        Mantenimiento.objects.filter(
            equipo__empresa__in=empresas_queryset,
            fecha_mantenimiento__year=current_year
        ).count() +
        Comprobacion.objects.filter(
            equipo__empresa__in=empresas_queryset,
            fecha_comprobacion__year=current_year
        ).count()
    )

    # Tiempo promedio por actividad
    tiempo_promedio = _calculate_average_time_per_activity(empresas_queryset, current_year)

    # Cumplimiento general
    cumplimiento_data = _calculate_compliance_metrics(empresas_queryset)

    return {
        'total_equipos_gestionados': total_equipos,
        'actividades_realizadas_año': actividades_año,
        'tiempo_promedio_actividad': tiempo_promedio,
        **cumplimiento_data
    }


def _calculate_client_investment_metrics(empresa, current_year, previous_year):
    """
    Calcula métricas de inversión para cliente
    """
    # Inversión total en metrología este año
    inversion_actual = 0
    if empresa.tarifa_mensual_sam:
        meses_transcurridos = date.today().month
        inversion_actual = float(empresa.tarifa_mensual_sam) * meses_transcurridos

    # Inversión año anterior (estimada)
    inversion_anterior = float(empresa.tarifa_mensual_sam or 0) * 12

    # Costos por tipo de actividad
    equipos_empresa = Equipo.objects.filter(empresa=empresa)

    costos_calibracion = Calibracion.objects.filter(
        equipo__in=equipos_empresa,
        fecha_calibracion__year=current_year
    ).aggregate(total=Sum('costo_calibracion'))['total'] or 0

    costos_mantenimiento = Mantenimiento.objects.filter(
        equipo__in=equipos_empresa,
        fecha_mantenimiento__year=current_year
    ).aggregate(total=Sum('costo'))['total'] or 0

    costos_comprobacion = Comprobacion.objects.filter(
        equipo__in=equipos_empresa,
        fecha_comprobacion__year=current_year
    ).aggregate(total=Sum('costo_comprobacion'))['total'] or 0

    # Costo promedio por equipo
    num_equipos = equipos_empresa.count()
    costo_por_equipo = (costos_calibracion + costos_mantenimiento + costos_comprobacion) / num_equipos if num_equipos > 0 else 0

    # Variación año a año
    variacion_inversion = ((inversion_actual - inversion_anterior) / inversion_anterior * 100) if inversion_anterior > 0 else 0

    return {
        'inversion_actual': inversion_actual,
        'inversion_anterior': inversion_anterior,
        'variacion_inversion': round(variacion_inversion, 1),
        'costos_calibracion_cliente': costos_calibracion,
        'costos_mantenimiento_cliente': costos_mantenimiento,
        'costos_comprobacion_cliente': costos_comprobacion,
        'costo_promedio_por_equipo': round(costo_por_equipo, 2),
        'num_equipos_empresa': num_equipos
    }


def _calculate_client_value_analysis(empresa, current_year, previous_year):
    """
    Calcula análisis de valor para cliente
    """
    equipos_empresa = Equipo.objects.filter(empresa=empresa)

    # Cumplimiento y eficiencia
    cumplimiento_calibracion = _get_compliance_percentage(equipos_empresa, 'calibracion')
    cumplimiento_mantenimiento = _get_compliance_percentage(equipos_empresa, 'mantenimiento')
    cumplimiento_comprobacion = _get_compliance_percentage(equipos_empresa, 'comprobacion')

    cumplimiento_general = (cumplimiento_calibracion + cumplimiento_mantenimiento + cumplimiento_comprobacion) / 3

    # Análisis de equipos críticos
    equipos_criticos = equipos_empresa.filter(
        Q(proxima_calibracion__lt=date.today()) |
        Q(proxima_mantenimiento__lt=date.today()) |
        Q(proxima_comprobacion__lt=date.today())
    ).count()

    equipos_operativos = equipos_empresa.exclude(estado__in=['De Baja', 'Inactivo']).count()
    porcentaje_operativo = (equipos_operativos / equipos_empresa.count() * 100) if equipos_empresa.count() > 0 else 0

    return {
        'cumplimiento_calibracion': round(cumplimiento_calibracion, 1),
        'cumplimiento_mantenimiento': round(cumplimiento_mantenimiento, 1),
        'cumplimiento_comprobacion': round(cumplimiento_comprobacion, 1),
        'cumplimiento_general': round(cumplimiento_general, 1),
        'equipos_criticos': equipos_criticos,
        'equipos_operativos': equipos_operativos,
        'porcentaje_operativo': round(porcentaje_operativo, 1),
        'tipo_organismo': empresa.tipo_organismo,
        'normas_aplicables': empresa.normas_aplicables
    }


def _get_previous_year_costs(empresas_queryset, previous_year):
    """
    Obtiene costos del año anterior para comparación
    """
    costos_cal_prev = Calibracion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_calibracion__year=previous_year
    ).aggregate(total=Sum('costo_calibracion'))['total'] or 0

    costos_mant_prev = Mantenimiento.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_mantenimiento__year=previous_year
    ).aggregate(total=Sum('costo_sam_interno'))['total'] or 0

    costos_comp_prev = Comprobacion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_comprobacion__year=previous_year
    ).aggregate(total=Sum('costo_comprobacion'))['total'] or 0

    return costos_cal_prev + costos_mant_prev + costos_comp_prev


def _calculate_average_time_per_activity(empresas_queryset, current_year):
    """
    Calcula tiempo promedio por actividad
    """
    tiempo_cal = Calibracion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_calibracion__year=current_year,
        tiempo_empleado_horas__isnull=False
    ).aggregate(promedio=Avg('tiempo_empleado_horas'))['promedio'] or 0

    tiempo_mant = Mantenimiento.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_mantenimiento__year=current_year,
        tiempo_empleado_horas__isnull=False
    ).aggregate(promedio=Avg('tiempo_empleado_horas'))['promedio'] or 0

    tiempo_comp = Comprobacion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_comprobacion__year=current_year,
        tiempo_empleado_horas__isnull=False
    ).aggregate(promedio=Avg('tiempo_empleado_horas'))['promedio'] or 0

    return {
        'calibracion': round(float(tiempo_cal), 1),
        'mantenimiento': round(float(tiempo_mant), 1),
        'comprobacion': round(float(tiempo_comp), 1)
    }


def _calculate_compliance_metrics(empresas_queryset):
    """
    Calcula métricas de cumplimiento general
    """
    equipos = Equipo.objects.filter(empresa__in=empresas_queryset, empresa__is_deleted=False)
    total_equipos = equipos.count()

    if total_equipos == 0:
        return {
            'cumplimiento_general': 0,
            'equipos_al_dia': 0,
            'equipos_vencidos': 0
        }

    today = date.today()
    equipos_al_dia = equipos.filter(
        Q(proxima_calibracion__gte=today) | Q(proxima_calibracion__isnull=True),
        Q(proximo_mantenimiento__gte=today) | Q(proximo_mantenimiento__isnull=True),
        Q(proxima_comprobacion__gte=today) | Q(proxima_comprobacion__isnull=True)
    ).count()

    equipos_vencidos = total_equipos - equipos_al_dia
    cumplimiento = (equipos_al_dia / total_equipos * 100) if total_equipos > 0 else 0

    return {
        'cumplimiento_general': round(cumplimiento, 1),
        'equipos_al_dia': equipos_al_dia,
        'equipos_vencidos': equipos_vencidos
    }


def _get_compliance_percentage(equipos_queryset, activity_type):
    """
    Obtiene porcentaje de cumplimiento para un tipo de actividad
    """
    total = equipos_queryset.count()
    if total == 0:
        return 100

    today = date.today()

    if activity_type == 'calibracion':
        al_dia = equipos_queryset.filter(
            Q(proxima_calibracion__gte=today) | Q(proxima_calibracion__isnull=True)
        ).count()
    elif activity_type == 'mantenimiento':
        al_dia = equipos_queryset.filter(
            Q(proximo_mantenimiento__gte=today) | Q(proximo_mantenimiento__isnull=True)
        ).count()
    elif activity_type == 'comprobacion':
        al_dia = equipos_queryset.filter(
            Q(proxima_comprobacion__gte=today) | Q(proxima_comprobacion__isnull=True)
        ).count()
    else:
        return 0

    return (al_dia / total * 100) if total > 0 else 100


def _calculate_sam_client_analysis(empresas_queryset):
    """
    Análisis de cartera de clientes para SAM
    """
    # Distribución por tipo de organismo
    tipos_organismo = empresas_queryset.values('tipo_organismo').annotate(
        count=Count('id')
    ).order_by('-count')

    # Clientes más rentables (por tarifa)
    top_clientes = empresas_queryset.filter(
        tarifa_mensual_sam__isnull=False
    ).order_by('-tarifa_mensual_sam')[:5]

    # Análisis de retención (clientes con contratos)
    clientes_con_contrato = empresas_queryset.filter(
        fecha_inicio_contrato_sam__isnull=False
    ).count()

    return {
        'tipos_organismo_data': list(tipos_organismo),
        'top_clientes': top_clientes,
        'clientes_con_contrato': clientes_con_contrato,
        'total_clientes': empresas_queryset.count()
    }


def _calculate_client_compliance_metrics(empresa, today):
    """
    Métricas de compliance específicas para cliente
    """
    equipos = Equipo.objects.filter(empresa=empresa)

    # Equipos próximos a vencer (30 días)
    proximos_30_dias = today + timedelta(days=30)

    equipos_proximos = equipos.filter(
        Q(proxima_calibracion__gte=today, proxima_calibracion__lte=proximos_30_dias) |
        Q(proximo_mantenimiento__gte=today, proximo_mantenimiento__lte=proximos_30_dias) |
        Q(proxima_comprobacion__gte=today, proxima_comprobacion__lte=proximos_30_dias)
    ).count()

    # Estado de trazabilidad
    equipos_trazables = equipos.exclude(estado='De Baja').count()
    equipos_sin_calibrar = equipos.filter(proxima_calibracion__isnull=True).count()

    trazabilidad_porcentaje = ((equipos_trazables - equipos_sin_calibrar) / equipos_trazables * 100) if equipos_trazables > 0 else 0

    return {
        'equipos_proximos_vencer': equipos_proximos,
        'trazabilidad_porcentaje': round(trazabilidad_porcentaje, 1),
        'equipos_sin_calibrar': equipos_sin_calibrar
    }


def _get_sam_charts_data(empresas_queryset, current_year, previous_year):
    """
    Datos para gráficos perspectiva SAM
    """
    # Evolución mensual de ingresos
    monthly_data = []
    for month in range(1, 13):
        ingresos_mes = empresas_queryset.aggregate(
            total=Sum('tarifa_mensual_sam')
        )['total'] or 0
        monthly_data.append(float(ingresos_mes))

    # Distribución de costos
    costos_cal = Calibracion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_calibracion__year=current_year
    ).aggregate(total=Sum('costo_calibracion'))['total'] or 0

    costos_mant = Mantenimiento.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_mantenimiento__year=current_year
    ).aggregate(total=Sum('costo_sam_interno'))['total'] or 0

    costos_comp = Comprobacion.objects.filter(
        equipo__empresa__in=empresas_queryset,
        fecha_comprobacion__year=current_year
    ).aggregate(total=Sum('costo_comprobacion'))['total'] or 0

    return {
        'monthly_revenue_data': json.dumps(monthly_data),
        'cost_distribution': json.dumps([
            float(costos_cal), float(costos_mant), float(costos_comp)
        ]),
        'cost_labels': json.dumps(['Calibraciones', 'Mantenimientos', 'Comprobaciones'])
    }


def _get_client_charts_data(empresa, current_year, previous_year):
    """
    Datos para gráficos perspectiva Cliente
    """
    equipos_empresa = Equipo.objects.filter(empresa=empresa)

    # Evolución mensual de actividades
    monthly_activities = []
    for month in range(1, 13):
        actividades_mes = (
            Calibracion.objects.filter(
                equipo__in=equipos_empresa,
                fecha_calibracion__year=current_year,
                fecha_calibracion__month=month
            ).count() +
            Mantenimiento.objects.filter(
                equipo__in=equipos_empresa,
                fecha_mantenimiento__year=current_year,
                fecha_mantenimiento__month=month
            ).count() +
            Comprobacion.objects.filter(
                equipo__in=equipos_empresa,
                fecha_comprobacion__year=current_year,
                fecha_comprobacion__month=month
            ).count()
        )
        monthly_activities.append(actividades_mes)

    # Estado de equipos
    estados_count = equipos_empresa.values('estado').annotate(
        count=Count('id')
    )

    estados_data = []
    estados_labels = []
    for estado in estados_count:
        estados_labels.append(estado['estado'])
        estados_data.append(estado['count'])

    return {
        'monthly_activities_data': json.dumps(monthly_activities),
        'equipment_status_data': json.dumps(estados_data),
        'equipment_status_labels': json.dumps(estados_labels),
        'months_labels': json.dumps([
            'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
            'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
        ])
    }