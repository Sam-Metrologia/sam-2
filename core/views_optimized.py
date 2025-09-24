# core/views_optimized.py
# Funciones optimizadas para las views principales

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Case, When, IntegerField, Q
from datetime import date, timedelta
from .models import Empresa, Equipo
from .optimizations import OptimizedQueries, CacheHelpers
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard_optimized(request):
    """
    Dashboard optimizado con queries mejoradas y cache
    """
    user = request.user
    today = date.today()
    current_year = today.year

    # Filtrado por empresa para superusuarios
    selected_company_id = request.GET.get('empresa_id')

    # Query optimizada para empresas disponibles (solo si es necesario)
    if user.is_superuser:
        empresas_disponibles = OptimizedQueries.get_empresas_with_stats()
    else:
        empresas_disponibles = Empresa.objects.none()

    # Query base optimizada
    equipos_queryset, _ = OptimizedQueries.get_dashboard_equipos(user, selected_company_id)

    # Excluir equipos de baja e inactivos para dashboard
    equipos_para_dashboard = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

    # Estadísticas optimizadas con una sola query
    estadisticas_equipos = equipos_queryset.aggregate(
        total_equipos=Count('id'),
        equipos_activos=Count(Case(When(estado='Activo', then=1), output_field=IntegerField())),
        equipos_inactivos=Count(Case(When(estado='Inactivo', then=1), output_field=IntegerField())),
        equipos_de_baja=Count(Case(When(estado='De Baja', then=1), output_field=IntegerField())),
        equipos_mantenimiento=Count(Case(When(estado='En Mantenimiento', then=1), output_field=IntegerField()))
    )

    # Datos de almacenamiento y límites optimizados
    storage_data = _get_storage_data_optimized(user, selected_company_id)
    equipment_limit_data = _get_equipment_limit_data_optimized(user, selected_company_id)

    # Actividades próximas optimizadas
    proximas_actividades = OptimizedQueries.get_proximas_actividades(user, days_ahead=30)

    # Actividades vencidas (optimizadas)
    actividades_vencidas = _get_actividades_vencidas_optimized(equipos_para_dashboard, today)

    # Datos para gráficos optimizados
    graficos_data = _get_graficos_data_optimized(equipos_para_dashboard, current_year)

    context = {
        'user': user,
        'today': today,

        # Estadísticas principales
        'total_equipos': estadisticas_equipos['total_equipos'],
        'equipos_activos': estadisticas_equipos['equipos_activos'],
        'equipos_inactivos': estadisticas_equipos['equipos_inactivos'],
        'equipos_de_baja': estadisticas_equipos['equipos_de_baja'],
        'equipos_mantenimiento': estadisticas_equipos['equipos_mantenimiento'],

        # Datos de almacenamiento
        **storage_data,

        # Datos de límites de equipos
        **equipment_limit_data,

        # Actividades próximas y vencidas
        'calibraciones_proximas': list(proximas_actividades['calibraciones'][:10]),
        'mantenimientos_proximos': list(proximas_actividades['mantenimientos'][:10]),
        'comprobaciones_proximas': list(proximas_actividades['comprobaciones'][:10]),
        'actividades_vencidas': actividades_vencidas,

        # Datos para gráficos
        **graficos_data,

        # Filtros
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,

        'titulo_pagina': 'Dashboard - SAM Metrología'
    }

    logger.info(f"Dashboard cargado para usuario {user.username} - Empresa: {selected_company_id or 'N/A'}")

    return render(request, 'dashboard.html', context)


def _get_storage_data_optimized(user, selected_company_id):
    """
    Obtiene datos de almacenamiento de forma optimizada usando cache
    """
    storage_data = {
        'storage_usage_mb': 0,
        'storage_limit_mb': 0,
        'storage_percentage': 0,
        'storage_status_class': 'text-gray-700 bg-gray-100',
        'storage_empresa_nombre': 'N/A'
    }

    empresa_id = None

    if user.is_superuser and selected_company_id:
        empresa_id = selected_company_id
    elif user.empresa:
        empresa_id = user.empresa.id

    if empresa_id:
        # Usar cache para obtener estadísticas
        stats = CacheHelpers.get_cached_empresa_stats(empresa_id)

        if stats:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                storage_data.update({
                    'storage_usage_mb': stats['storage_used'],
                    'storage_limit_mb': stats['storage_limit'],
                    'storage_percentage': empresa.get_storage_usage_percentage(),
                    'storage_status_class': empresa.get_storage_status_class(),
                    'storage_empresa_nombre': empresa.nombre
                })
            except Empresa.DoesNotExist:
                pass

    return storage_data


def _get_equipment_limit_data_optimized(user, selected_company_id):
    """
    Obtiene datos de límites de equipos de forma optimizada
    """
    limit_data = {
        'equipos_limite': 0,
        'equipos_actuales_count': 0,
        'equipos_disponibles': 0,
        'equipos_limite_percentage': 0,
        'equipos_limite_warning': False,
        'equipos_limite_critical': False
    }

    empresa_id = None

    if user.is_superuser and selected_company_id:
        empresa_id = selected_company_id
    elif user.empresa:
        empresa_id = user.empresa.id

    if empresa_id:
        # Usar cache para obtener conteo
        equipos_actuales_count = OptimizedQueries.get_empresa_equipment_count(empresa_id)

        try:
            empresa = Empresa.objects.get(id=empresa_id)
            equipos_limite = empresa.get_limite_equipos()

            limit_data.update({
                'equipos_limite': equipos_limite,
                'equipos_actuales_count': equipos_actuales_count
            })

            if equipos_limite != float('inf'):
                equipos_disponibles = max(0, equipos_limite - equipos_actuales_count)
                equipos_limite_percentage = (equipos_actuales_count / equipos_limite) * 100 if equipos_limite > 0 else 0

                limit_data.update({
                    'equipos_disponibles': equipos_disponibles,
                    'equipos_limite_percentage': equipos_limite_percentage,
                    'equipos_limite_warning': equipos_limite_percentage >= 80,
                    'equipos_limite_critical': equipos_actuales_count >= equipos_limite
                })

        except Empresa.DoesNotExist:
            pass

    return limit_data


def _get_actividades_vencidas_optimized(equipos_queryset, today):
    """
    Obtiene actividades vencidas de forma optimizada
    """
    # Una sola query para todas las actividades vencidas
    actividades_vencidas = equipos_queryset.filter(
        Q(proxima_calibracion__lt=today, proxima_calibracion__isnull=False) |
        Q(proximo_mantenimiento__lt=today, proximo_mantenimiento__isnull=False) |
        Q(proxima_comprobacion__lt=today, proxima_comprobacion__isnull=False)
    ).select_related('empresa').distinct()

    return list(actividades_vencidas[:20])  # Limitar para performance


def _get_graficos_data_optimized(equipos_queryset, current_year):
    """
    Obtiene datos para gráficos de forma optimizada
    """
    # Actividades por mes (optimizado con aggregation)
    actividades_por_mes = equipos_queryset.filter(
        Q(calibraciones__fecha_calibracion__year=current_year) |
        Q(mantenimientos__fecha_mantenimiento__year=current_year) |
        Q(comprobaciones__fecha_comprobacion__year=current_year)
    ).extra(
        select={'mes': "strftime('%m', date(COALESCE("
                      "core_calibracion.fecha_calibracion, "
                      "core_mantenimiento.fecha_mantenimiento, "
                      "core_comprobacion.fecha_comprobacion)))"}
    ).values('mes').annotate(
        total=Count('id')
    ).order_by('mes')

    # Equipos por estado (ya se calculó en estadísticas principales)
    equipos_por_estado = equipos_queryset.values('estado').annotate(
        count=Count('id')
    ).order_by('estado')

    return {
        'actividades_por_mes': list(actividades_por_mes),
        'equipos_por_estado': list(equipos_por_estado),
        'labels_meses': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    }


@login_required
def lista_equipos_optimized(request):
    """
    Lista de equipos optimizada con prefetch y paginación eficiente
    """
    user = request.user

    # Query base optimizada
    equipos_queryset = OptimizedQueries.get_equipos_optimized(user=user)

    # Filtros
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    if query:
        equipos_queryset = equipos_queryset.filter(
            Q(codigo_interno__icontains=query) |
            Q(nombre__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query)
        )

    if estado:
        equipos_queryset = equipos_queryset.filter(estado=estado)

    # Paginación optimizada
    from django.core.paginator import Paginator
    paginator = Paginator(equipos_queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'equipos': page_obj,
        'query': query,
        'estado_selected': estado,
        'estados_choices': Equipo.ESTADO_CHOICES,
        'titulo_pagina': 'Lista de Equipos'
    }

    return render(request, 'equipos_list.html', context)


# Funciones helper para optimización de queries existentes
def optimize_existing_queries():
    """
    Función para optimizar queries existentes sin romper funcionalidad
    """

    # Patches para aplicar a views existentes
    patches = {
        # Dashboard
        'dashboard_equipos_query': lambda user, selected_id: OptimizedQueries.get_dashboard_equipos(user, selected_id)[0],

        # Lista equipos
        'equipos_with_relations': lambda empresa=None, user=None: OptimizedQueries.get_equipos_optimized(empresa, user),

        # Conteo equipos
        'equipment_count': lambda empresa_id: OptimizedQueries.get_empresa_equipment_count(empresa_id),
    }

    return patches