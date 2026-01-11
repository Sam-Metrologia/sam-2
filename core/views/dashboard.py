# core/views/dashboard.py
# Views relacionadas con el dashboard y métricas generales

from .base import *
import json
from django.core.cache import cache


def get_justificacion_incumplimiento(equipo, status):
    """
    Obtiene la justificación del incumplimiento según el estado del equipo y el status de la actividad.

    Lógica:
    - Si estado_equipo == 'Inactivo' → equipo.observaciones
    - Si estado_equipo == 'De Baja' → baja_registro.razon_baja + observaciones
    - Si estado_equipo == 'Activo' AND status == 'No Cumplido' → equipo.observaciones
    """
    justificacion = ""

    # Solo agregar justificación si no se cumplió
    if status != 'No Cumplido':
        return justificacion

    estado = equipo.estado

    if estado == 'Inactivo':
        justificacion = equipo.observaciones or "Equipo inactivo sin observaciones registradas"

    elif estado == 'De Baja':
        # Buscar registro de baja
        if hasattr(equipo, 'baja_registro') and equipo.baja_registro:
            baja = equipo.baja_registro
            justificacion = f"BAJA: {baja.razon_baja}"
            if baja.observaciones:
                justificacion += f" | {baja.observaciones}"
        else:
            justificacion = "Equipo dado de baja sin registro detallado"

    elif estado == 'Activo':
        justificacion = equipo.observaciones or "Equipo activo - no cumplió sin observaciones registradas"

    else:
        # Otros estados (En Calibración, En Mantenimiento, etc.)
        justificacion = equipo.observaciones or f"Estado: {estado}"

    return justificacion


def get_projected_activities_for_year(equipos_queryset, activity_type, year, today):
    """
    Obtiene las actividades proyectadas para el año especificado

    Jerarquía de fechas:
    1. Última actividad del tipo específico
    2. Última calibración (si no hay actividad del tipo)
    3. Fecha de adquisición
    4. NUNCA fecha de registro
    """
    projected_activities = []

    for equipo in equipos_queryset:
        if activity_type == 'calibracion' and equipo.frecuencia_calibracion_meses:
            freq = int(equipo.frecuencia_calibracion_meses)
            activity_model = Calibracion
            date_field = 'fecha_calibracion'
            # Usar la última calibración REAL
            latest_activity = equipo.calibraciones.order_by('-fecha_calibracion').first()
            if latest_activity:
                plan_start_date = latest_activity.fecha_calibracion
            elif equipo.fecha_adquisicion:
                plan_start_date = equipo.fecha_adquisicion
            else:
                continue  # Sin fecha válida, saltar este equipo

        elif activity_type == 'comprobacion' and equipo.frecuencia_comprobacion_meses:
            freq = int(equipo.frecuencia_comprobacion_meses)
            activity_model = Comprobacion
            date_field = 'fecha_comprobacion'
            # Jerarquía: última comprobación -> última calibración -> adquisición
            latest_activity = equipo.comprobaciones.order_by('-fecha_comprobacion').first()
            if latest_activity:
                plan_start_date = latest_activity.fecha_comprobacion
            else:
                # Si no hay comprobación, usar última calibración
                latest_calibracion = equipo.calibraciones.order_by('-fecha_calibracion').first()
                if latest_calibracion:
                    plan_start_date = latest_calibracion.fecha_calibracion
                elif equipo.fecha_adquisicion:
                    plan_start_date = equipo.fecha_adquisicion
                else:
                    continue  # Sin fecha válida, saltar este equipo
        else:
            continue

        if freq <= 0:
            continue

        # Calcular fechas programadas en el año
        current_date = plan_start_date
        while current_date.year < year:
            current_date += relativedelta(months=freq)

        while current_date.year == year:
            # Verificar si se realizó la actividad
            realizadas = activity_model.objects.filter(
                equipo=equipo,
                **{f"{date_field}__year": year,
                   f"{date_field}__month": current_date.month}
            ).exists()

            if realizadas:
                status = 'Realizado'
            elif current_date < today:
                status = 'No Cumplido'
            else:
                status = 'Pendiente/Programado'

            projected_activities.append({
                'equipo': equipo,
                'fecha_programada': current_date,
                'status': status
            })

            current_date += relativedelta(months=freq)

    return projected_activities


def get_projected_maintenance_compliance_for_year(equipos_queryset, year, today):
    """
    Obtiene el cumplimiento de mantenimientos proyectados para el año

    Jerarquía de fechas:
    1. Último mantenimiento
    2. Última calibración (si no hay mantenimiento)
    3. Fecha de adquisición
    4. NUNCA fecha de registro
    """
    projected_maintenances = []

    for equipo in equipos_queryset:
        if not equipo.frecuencia_mantenimiento_meses:
            continue

        # Jerarquía: último mantenimiento -> última calibración -> adquisición
        latest_mantenimiento = equipo.mantenimientos.order_by('-fecha_mantenimiento').first()
        if latest_mantenimiento:
            plan_start_date = latest_mantenimiento.fecha_mantenimiento
        else:
            # Si no hay mantenimiento, usar última calibración
            latest_calibracion = equipo.calibraciones.order_by('-fecha_calibracion').first()
            if latest_calibracion:
                plan_start_date = latest_calibracion.fecha_calibracion
            elif equipo.fecha_adquisicion:
                plan_start_date = equipo.fecha_adquisicion
            else:
                continue  # Sin fecha válida, saltar este equipo

        freq = int(equipo.frecuencia_mantenimiento_meses)
        if freq <= 0:
            continue

        current_date = plan_start_date
        while current_date.year < year:
            current_date += relativedelta(months=freq)

        while current_date.year == year:
            # Verificar si se realizó el mantenimiento
            realizados = Mantenimiento.objects.filter(
                equipo=equipo,
                fecha_mantenimiento__year=year,
                fecha_mantenimiento__month=current_date.month
            ).exists()

            if realizados:
                status = 'Realizado'
            elif current_date < today:
                status = 'No Cumplido'
            else:
                status = 'Pendiente/Programado'

            projected_maintenances.append({
                'equipo': equipo,
                'fecha_programada': current_date,
                'status': status
            })

            current_date += relativedelta(months=freq)

    return projected_maintenances


@login_required
@monitor_view
def dashboard(request):
    """
    Dashboard principal con métricas clave y gráficos

    Con cache inteligente (TTL: 5 minutos)
    - Primera carga: <1s (optimizaciones de queries)
    - Cargas subsecuentes: <50ms (cache)
    - Invalidación automática al modificar datos

    Esta función ha sido refactorizada para mejor mantenibilidad.
    La lógica compleja se ha dividido en funciones auxiliares.
    """
    user = request.user
    today = date.today()
    current_year = today.year

    # Filtrado por empresa para superusuarios (solo empresas activas)
    selected_company_id = request.GET.get('empresa_id')

    # CACHE: Generar cache key único por usuario y empresa
    cache_key = f"dashboard_{user.id}_{selected_company_id or 'all'}"

    # CACHE: Intentar obtener datos del cache
    cached_context = cache.get(cache_key)
    if cached_context:
        # Cache hit: retornar datos cacheados inmediatamente
        return render(request, 'core/dashboard.html', cached_context)

    # Cache miss: ejecutar lógica normal
    empresas_disponibles = Empresa.objects.filter(is_deleted=False).order_by('nombre')

    # Obtener queryset de equipos según permisos
    equipos_queryset = _get_equipos_queryset(user, selected_company_id, empresas_disponibles)

    # Equipos para dashboard (excluir De Baja e Inactivo para estadísticas y vencimientos)
    equipos_para_dashboard = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

    # Equipos para proyecciones anuales (TODOS los equipos, incluso inactivos/dados de baja)
    # Si un equipo se dio de baja durante el año, sus actividades programadas siguen contando
    equipos_para_proyecciones = equipos_queryset

    # Estadísticas principales
    estadisticas_equipos = _get_estadisticas_equipos(equipos_queryset)

    # Datos de almacenamiento y límites
    storage_data = _get_storage_data(user, selected_company_id)
    equipment_limits_data = _get_equipment_limits_data(user, selected_company_id, equipos_queryset)

    # Información del plan
    plan_info_data = _get_plan_info(user, selected_company_id)

    # Actividades vencidas y próximas
    actividades_data = _get_actividades_data(equipos_para_dashboard, today)

    # Datos para gráficos
    graficos_data = _get_graficos_data(equipos_queryset, equipos_para_dashboard, equipos_para_proyecciones, current_year, today)

    # Generar datos JSON para gráficos
    chart_json_data = _get_chart_json_data(graficos_data)

    # Chart data generado correctamente

    # Mantenimientos correctivos recientes
    latest_corrective_maintenances = _get_latest_corrective_maintenances(user, selected_company_id)

    # Datos de préstamos de equipos (NUEVO)
    prestamos_data = _get_prestamos_data(user, selected_company_id)

    # Construir contexto
    context = {
        'titulo_pagina': 'Panel de Control de Metrología',
        'today': today,
        'is_superuser': user.is_superuser,
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,
        'latest_corrective_maintenances': latest_corrective_maintenances,

        # Merge all data dictionaries
        **estadisticas_equipos,
        **storage_data,
        **equipment_limits_data,
        **plan_info_data,
        **actividades_data,
        **graficos_data,
        **chart_json_data,
        **prestamos_data  # AGREGAR ESTA LÍNEA
    }

    # CACHE: Guardar contexto en cache con TTL de 5 minutos (300 segundos)
    cache.set(cache_key, context, 300)

    return render(request, 'core/dashboard.html', context)


def _get_equipos_queryset(user, selected_company_id, empresas_disponibles):
    """
    Obtiene el queryset de equipos con optimización de queries mediante prefetch.

    Optimización: Reduce N+1 queries usando select_related y prefetch_related.
    - select_related para ForeignKey (empresa)
    - prefetch_related para relaciones inversas (calibraciones, mantenimientos, comprobaciones)
    - to_attr para acceso directo a datos prefetched
    """
    from django.db.models import Prefetch

    # Solo equipos de empresas activas (no eliminadas)
    equipos_queryset = Equipo.objects.filter(
        empresa__is_deleted=False
    ).select_related(
        'empresa'  # Evita query adicional al acceder equipo.empresa
    ).prefetch_related(
        # Prefetch calibraciones ordenadas (última primero)
        Prefetch(
            'calibraciones',
            queryset=Calibracion.objects.select_related('proveedor').order_by('-fecha_calibracion'),
            to_attr='calibraciones_prefetched'
        ),
        # Prefetch mantenimientos ordenados (último primero)
        Prefetch(
            'mantenimientos',
            queryset=Mantenimiento.objects.order_by('-fecha_mantenimiento'),
            to_attr='mantenimientos_prefetched'
        ),
        # Prefetch comprobaciones ordenadas (última primero)
        Prefetch(
            'comprobaciones',
            queryset=Comprobacion.objects.order_by('-fecha_comprobacion'),
            to_attr='comprobaciones_prefetched'
        )
    )

    if not user.is_superuser:
        if user.empresa and not user.empresa.is_deleted:
            equipos_queryset = equipos_queryset.filter(empresa=user.empresa)
            selected_company_id = str(user.empresa.id)
        else:
            # Si el usuario no tiene empresa o su empresa está eliminada, no ve equipos
            equipos_queryset = Equipo.objects.none()
            empresas_disponibles = Empresa.objects.none()

    if selected_company_id:
        equipos_queryset = equipos_queryset.filter(empresa_id=selected_company_id)

    return equipos_queryset


def _get_estadisticas_equipos(equipos_queryset):
    """Obtiene estadísticas agregadas de equipos"""
    from django.db.models import Count, Case, When, IntegerField

    estadisticas = equipos_queryset.aggregate(
        total_equipos=Count('id'),
        equipos_activos=Count(Case(When(estado='Activo', then=1), output_field=IntegerField())),
        equipos_inactivos=Count(Case(When(estado='Inactivo', then=1), output_field=IntegerField())),
        equipos_de_baja=Count(Case(When(estado='De Baja', then=1), output_field=IntegerField()))
    )

    return estadisticas


def _get_storage_data(user, selected_company_id):
    """Obtiene datos de almacenamiento"""
    storage_data = {
        'storage_usage_mb': 0,
        'storage_limit_mb': 0,
        'storage_percentage': 0,
        'storage_status_class': 'text-gray-700 bg-gray-100',
        'storage_empresa_nombre': 'N/A'
    }

    empresa_objetivo = None

    if user.is_superuser and selected_company_id:
        try:
            empresa_objetivo = Empresa.objects.get(id=selected_company_id)
        except Empresa.DoesNotExist:
            pass
    elif user.empresa:
        empresa_objetivo = user.empresa

    if empresa_objetivo:
        storage_usage_mb = empresa_objetivo.get_total_storage_used_mb()
        storage_limit_mb = empresa_objetivo.limite_almacenamiento_mb

        # Formatear para mostrar en GB cuando sea apropiado
        if storage_usage_mb >= 1000:
            storage_usage_display = f"{storage_usage_mb / 1000:.1f} GB"
        else:
            storage_usage_display = f"{storage_usage_mb} MB"

        if storage_limit_mb >= 1000:
            storage_limit_display = f"{storage_limit_mb / 1000:.1f} GB"
        else:
            storage_limit_display = f"{storage_limit_mb} MB"

        storage_data.update({
            'storage_usage_mb': storage_usage_mb,
            'storage_limit_mb': storage_limit_mb,
            'storage_usage_display': storage_usage_display,
            'storage_limit_display': storage_limit_display,
            'storage_percentage': empresa_objetivo.get_storage_usage_percentage(),
            'storage_status_class': empresa_objetivo.get_storage_status_class(),
            'storage_empresa_nombre': empresa_objetivo.nombre
        })

    return storage_data


def _get_equipment_limits_data(user, selected_company_id, equipos_queryset):
    """Obtiene datos de límites de equipos"""
    limits_data = {
        'equipos_limite': 0,
        'equipos_actuales_count': 0,
        'equipos_disponibles': 0,
        'equipos_limite_percentage': 0,
        'equipos_limite_warning': False,
        'equipos_limite_critical': False
    }

    empresa_objetivo = None

    if user.is_superuser and selected_company_id:
        try:
            empresa_objetivo = Empresa.objects.get(id=selected_company_id)
        except Empresa.DoesNotExist:
            pass
    elif user.empresa:
        empresa_objetivo = user.empresa

    if empresa_objetivo:
        equipos_limite = empresa_objetivo.get_limite_equipos()
        equipos_actuales_count = equipos_queryset.count()

        limits_data.update({
            'equipos_limite': equipos_limite,
            'equipos_actuales_count': equipos_actuales_count
        })

        if equipos_limite != float('inf'):
            equipos_disponibles = max(0, equipos_limite - equipos_actuales_count)
            equipos_limite_percentage = (equipos_actuales_count / equipos_limite) * 100 if equipos_limite > 0 else 0

            limits_data.update({
                'equipos_disponibles': equipos_disponibles,
                'equipos_limite_percentage': equipos_limite_percentage,
                'equipos_limite_warning': equipos_limite_percentage >= 80,
                'equipos_limite_critical': equipos_actuales_count >= equipos_limite
            })

    return limits_data


def _get_actividades_data(equipos_para_dashboard, today):
    """Obtiene datos de actividades vencidas y próximas"""
    from datetime import timedelta
    from django.db.models import Count, Case, When, IntegerField

    fecha_limite_proximas = today + timedelta(days=30)

    # Estadísticas de actividades con una sola consulta agregada
    estadisticas_actividades = equipos_para_dashboard.aggregate(
        calibraciones_vencidas=Count(
            Case(When(
                proxima_calibracion__isnull=False,
                proxima_calibracion__lt=today,
                then=1
            ), output_field=IntegerField())
        ),
        calibraciones_proximas=Count(
            Case(When(
                proxima_calibracion__isnull=False,
                proxima_calibracion__gte=today,
                proxima_calibracion__lte=fecha_limite_proximas,
                then=1
            ), output_field=IntegerField())
        ),
        mantenimientos_vencidos=Count(
            Case(When(
                proximo_mantenimiento__isnull=False,
                proximo_mantenimiento__lt=today,
                then=1
            ), output_field=IntegerField())
        ),
        mantenimientos_proximas=Count(
            Case(When(
                proximo_mantenimiento__isnull=False,
                proximo_mantenimiento__gte=today,
                proximo_mantenimiento__lte=fecha_limite_proximas,
                then=1
            ), output_field=IntegerField())
        ),
        comprobaciones_vencidas=Count(
            Case(When(
                proxima_comprobacion__isnull=False,
                proxima_comprobacion__lt=today,
                then=1
            ), output_field=IntegerField())
        ),
        comprobaciones_proximas=Count(
            Case(When(
                proxima_comprobacion__isnull=False,
                proxima_comprobacion__gte=today,
                proxima_comprobacion__lte=fecha_limite_proximas,
                then=1
            ), output_field=IntegerField())
        )
    )

    # OPTIMIZACIÓN: Códigos de equipos vencidos en 1 query en lugar de 3
    # Obtener todos los equipos vencidos con sus campos de vencimiento en una sola query
    equipos_vencidos = equipos_para_dashboard.filter(
        Q(proxima_calibracion__lt=today) |
        Q(proximo_mantenimiento__lt=today) |
        Q(proxima_comprobacion__lt=today)
    ).values_list('codigo_interno', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion')

    # Separar por tipo en Python (más rápido que 3 queries SQL)
    vencidos_calibracion_codigos = []
    vencidos_mantenimiento_codigos = []
    vencidos_comprobacion_codigos = []

    for codigo, prox_cal, prox_mant, prox_comp in equipos_vencidos:
        if prox_cal and prox_cal < today:
            vencidos_calibracion_codigos.append(codigo)
        if prox_mant and prox_mant < today:
            vencidos_mantenimiento_codigos.append(codigo)
        if prox_comp and prox_comp < today:
            vencidos_comprobacion_codigos.append(codigo)

    estadisticas_actividades.update({
        'vencidos_calibracion_codigos': vencidos_calibracion_codigos,
        'vencidos_mantenimiento_codigos': vencidos_mantenimiento_codigos,
        'vencidos_comprobacion_codigos': vencidos_comprobacion_codigos,
    })

    return estadisticas_actividades


def _get_graficos_data(equipos_queryset, equipos_para_dashboard, equipos_para_proyecciones, current_year, today):
    """Obtiene todos los datos para gráficos del dashboard"""

    # Datos para gráficas de línea (12 meses)
    # Realizadas: todos los equipos | Programadas: solo activos
    line_data = _get_line_chart_data(equipos_para_dashboard, equipos_para_proyecciones, today)

    # Datos para gráficas de torta - usar equipos para proyecciones (TODOS)
    pie_data = _get_pie_chart_data(equipos_queryset, equipos_para_proyecciones, current_year, today)

    return {**line_data, **pie_data}


def _get_line_chart_data(equipos_activos, equipos_todos, today):
    """
    Obtiene datos para gráficos de línea (programadas vs realizadas)

    equipos_activos: solo equipos activos (para calcular programadas)
    equipos_todos: todos los equipos (para calcular realizadas)
    """

    # Calcular rango de fechas (6 meses antes y después)
    start_date_range = today - relativedelta(months=6)
    start_date_range = start_date_range.replace(day=1)

    # Labels para los meses
    line_chart_labels = []
    for i in range(12):
        target_date = start_date_range + relativedelta(months=i)
        line_chart_labels.append(f"{calendar.month_abbr[target_date.month]}. {target_date.year}")

    # Inicializar arrays de datos
    line_data = {
        'line_chart_labels': line_chart_labels,
        'programmed_calibrations_line_data': [0] * 12,
        'programmed_mantenimientos_line_data': [0] * 12,
        'programmed_comprobaciones_line_data': [0] * 12,
        'realized_calibrations_line_data': [0] * 12,
        'realized_preventive_mantenimientos_line_data': [0] * 12,
        'realized_corrective_mantenimientos_line_data': [0] * 12,
        'realized_other_mantenimientos_line_data': [0] * 12,
        'realized_predictive_mantenimientos_line_data': [0] * 12,
        'realized_inspection_mantenimientos_line_data': [0] * 12,
        'realized_comprobaciones_line_data': [0] * 12,
    }

    # Calcular actividades realizadas (TODOS los equipos - incluso dados de baja)
    _calculate_realized_activities(equipos_todos, start_date_range, line_data)

    # Calcular actividades programadas (SOLO equipos activos)
    _calculate_programmed_activities(equipos_activos, start_date_range, line_data)

    return line_data


def _calculate_realized_activities(equipos_para_dashboard, start_date_range, line_data):
    """Calcula actividades realizadas para gráficos de línea"""

    end_date_range = start_date_range + relativedelta(months=12, days=-1)

    # Calibraciones realizadas
    calibraciones = Calibracion.objects.select_related('equipo').filter(
        equipo__in=equipos_para_dashboard,
        fecha_calibracion__gte=start_date_range,
        fecha_calibracion__lte=end_date_range
    )

    for cal in calibraciones:
        month_index = ((cal.fecha_calibracion.year - start_date_range.year) * 12 +
                      cal.fecha_calibracion.month - start_date_range.month)
        if 0 <= month_index < 12:
            line_data['realized_calibrations_line_data'][month_index] += 1

    # Mantenimientos realizados
    mantenimientos = Mantenimiento.objects.select_related('equipo').filter(
        equipo__in=equipos_para_dashboard,
        fecha_mantenimiento__gte=start_date_range,
        fecha_mantenimiento__lte=end_date_range
    )

    for mant in mantenimientos:
        month_index = ((mant.fecha_mantenimiento.year - start_date_range.year) * 12 +
                      mant.fecha_mantenimiento.month - start_date_range.month)
        if 0 <= month_index < 12:
            if mant.tipo_mantenimiento == 'Preventivo':
                line_data['realized_preventive_mantenimientos_line_data'][month_index] += 1
            elif mant.tipo_mantenimiento == 'Correctivo':
                line_data['realized_corrective_mantenimientos_line_data'][month_index] += 1
            elif mant.tipo_mantenimiento == 'Predictivo':
                line_data['realized_predictive_mantenimientos_line_data'][month_index] += 1
            elif mant.tipo_mantenimiento == 'Inspección':
                line_data['realized_inspection_mantenimientos_line_data'][month_index] += 1
            else:
                line_data['realized_other_mantenimientos_line_data'][month_index] += 1

    # Comprobaciones realizadas
    comprobaciones = Comprobacion.objects.select_related('equipo').filter(
        equipo__in=equipos_para_dashboard,
        fecha_comprobacion__gte=start_date_range,
        fecha_comprobacion__lte=end_date_range
    )

    for comp in comprobaciones:
        month_index = ((comp.fecha_comprobacion.year - start_date_range.year) * 12 +
                      comp.fecha_comprobacion.month - start_date_range.month)
        if 0 <= month_index < 12:
            line_data['realized_comprobaciones_line_data'][month_index] += 1


def _calculate_programmed_activities(equipos_para_dashboard, start_date_range, line_data):
    """
    Calcula actividades programadas para gráficos de línea usando datos prefetched.

    OPTIMIZACIÓN: Usa datos prefetched para evitar N+1 queries.
    En lugar de equipo.calibraciones.order_by().first() (QUERY),
    usa getattr(equipo, 'calibraciones_prefetched', [])[0] (SIN QUERY).

    Jerarquía de fechas:
    1. Última actividad del tipo específico
    2. Última calibración (si no hay actividad del tipo)
    3. Fecha de adquisición
    4. NUNCA fecha de registro
    """

    for equipo in equipos_para_dashboard:
        # Calcular calibraciones programadas
        if equipo.frecuencia_calibracion_meses and equipo.frecuencia_calibracion_meses > 0:
            try:
                freq_months = int(equipo.frecuencia_calibracion_meses)
                if freq_months > 0:
                    # OPTIMIZACIÓN: Usar datos prefetched en lugar de query
                    calibraciones_list = getattr(equipo, 'calibraciones_prefetched', [])
                    latest_calibracion = calibraciones_list[0] if calibraciones_list else None

                    if latest_calibracion:
                        start_date_cal = latest_calibracion.fecha_calibracion
                    elif equipo.fecha_adquisicion:
                        start_date_cal = equipo.fecha_adquisicion
                    else:
                        continue  # Sin fecha válida, saltar

                    _add_programmed_activity_to_chart(
                        start_date_cal, freq_months,
                        start_date_range, line_data['programmed_calibrations_line_data']
                    )
            except (ValueError, TypeError):
                pass

        # Calcular mantenimientos programados
        if equipo.frecuencia_mantenimiento_meses and equipo.frecuencia_mantenimiento_meses > 0:
            try:
                freq_months = int(equipo.frecuencia_mantenimiento_meses)
                if freq_months > 0:
                    # OPTIMIZACIÓN: Usar datos prefetched en lugar de queries
                    mantenimientos_list = getattr(equipo, 'mantenimientos_prefetched', [])
                    latest_mantenimiento = mantenimientos_list[0] if mantenimientos_list else None

                    if latest_mantenimiento:
                        start_date_mant = latest_mantenimiento.fecha_mantenimiento
                    else:
                        # Jerarquía: usar última calibración si no hay mantenimiento
                        calibraciones_list = getattr(equipo, 'calibraciones_prefetched', [])
                        latest_calibracion = calibraciones_list[0] if calibraciones_list else None
                        if latest_calibracion:
                            start_date_mant = latest_calibracion.fecha_calibracion
                        elif equipo.fecha_adquisicion:
                            start_date_mant = equipo.fecha_adquisicion
                        else:
                            continue  # Sin fecha válida, saltar

                    _add_programmed_activity_to_chart(
                        start_date_mant, freq_months,
                        start_date_range, line_data['programmed_mantenimientos_line_data']
                    )
            except (ValueError, TypeError):
                pass

        # Calcular comprobaciones programadas
        if equipo.frecuencia_comprobacion_meses and equipo.frecuencia_comprobacion_meses > 0:
            try:
                freq_months = int(equipo.frecuencia_comprobacion_meses)
                if freq_months > 0:
                    # OPTIMIZACIÓN: Usar datos prefetched en lugar de queries
                    comprobaciones_list = getattr(equipo, 'comprobaciones_prefetched', [])
                    latest_comprobacion = comprobaciones_list[0] if comprobaciones_list else None

                    if latest_comprobacion:
                        start_date_comp = latest_comprobacion.fecha_comprobacion
                    else:
                        # Jerarquía: usar última calibración si no hay comprobación
                        calibraciones_list = getattr(equipo, 'calibraciones_prefetched', [])
                        latest_calibracion = calibraciones_list[0] if calibraciones_list else None
                        if latest_calibracion:
                            start_date_comp = latest_calibracion.fecha_calibracion
                        elif equipo.fecha_adquisicion:
                            start_date_comp = equipo.fecha_adquisicion
                        else:
                            continue  # Sin fecha válida, saltar

                    _add_programmed_activity_to_chart(
                        start_date_comp, freq_months,
                        start_date_range, line_data['programmed_comprobaciones_line_data']
                    )
            except (ValueError, TypeError):
                pass


def _add_programmed_activity_to_chart(plan_start_date, freq_months, start_date_range, data_array):
    """Añade actividades programadas al array de datos del gráfico"""

    # Validar freq_months para evitar división por cero
    if freq_months <= 0:
        return

    # Calcular primera fecha de actividad en el rango
    diff_months = ((start_date_range.year - plan_start_date.year) * 12 +
                   start_date_range.month - plan_start_date.month)
    num_intervals = max(0, (diff_months + freq_months - 1) // freq_months)

    current_plan_date = plan_start_date + relativedelta(months=num_intervals * freq_months)
    end_date = start_date_range + relativedelta(months=12)

    # Añadir fechas programadas al array
    max_iterations = 12 + freq_months  # Límite de seguridad
    iteration = 0

    while (current_plan_date < end_date and iteration < max_iterations):
        if start_date_range <= current_plan_date < end_date:
            month_index = ((current_plan_date.year - start_date_range.year) * 12 +
                          current_plan_date.month - start_date_range.month)
            if 0 <= month_index < 12:
                data_array[month_index] += 1

        try:
            current_plan_date += relativedelta(months=freq_months)
        except OverflowError:
            break

        iteration += 1


def _get_pie_chart_data(equipos_queryset, equipos_para_dashboard, current_year, today):
    """Obtiene datos para gráficos de torta"""
    from collections import defaultdict

    pie_data = {}

    # Estados de equipos
    estado_equipos_counts = defaultdict(int)
    for equipo in equipos_queryset.all():
        estado_equipos_counts[equipo.estado] += 1

    pie_data.update({
        'estado_equipos_labels': list(estado_equipos_counts.keys()),
        'estado_equipos_data': list(estado_equipos_counts.values())
    })

    # Calibraciones (cumplimiento anual) - Solo equipos activos
    projected_calibraciones = get_projected_activities_for_year(equipos_para_dashboard, 'calibracion', current_year, today)
    cal_data = _process_projected_activities_for_pie(projected_calibraciones, 'cal')
    pie_data.update(cal_data)

    # Comprobaciones (cumplimiento anual) - Solo equipos activos
    projected_comprobaciones = get_projected_activities_for_year(equipos_para_dashboard, 'comprobacion', current_year, today)
    comp_data = _process_projected_activities_for_pie(projected_comprobaciones, 'comp')
    pie_data.update(comp_data)

    # Mantenimientos (cumplimiento anual) - Solo equipos activos
    projected_mantenimientos = get_projected_maintenance_compliance_for_year(equipos_para_dashboard, current_year, today)
    mant_data = _process_projected_activities_for_pie(projected_mantenimientos, 'mant')
    pie_data.update(mant_data)

    # Mantenimientos por tipo
    mantenimientos_tipo_counts = defaultdict(int)
    for mant in Mantenimiento.objects.filter(equipo__in=equipos_para_dashboard):
        mantenimientos_tipo_counts[mant.tipo_mantenimiento] += 1

    pie_data.update({
        'mantenimientos_tipo_labels': list(mantenimientos_tipo_counts.keys()),
        'mantenimientos_tipo_data': list(mantenimientos_tipo_counts.values()),
        'pie_chart_colors_mant_types': ['#ffc107', '#dc3545', '#17a2b8', '#6c757d', '#8672cb']
    })

    return pie_data


def _get_chart_json_data(graficos_data):
    """Genera datos JSON para los gráficos del dashboard"""
    chart_json_data = {}

    # Datos para gráficos de torta de calibraciones
    cal_labels = ['Realizadas', 'No Cumplidas', 'Pendientes/Programadas']
    cal_data = [
        graficos_data.get('cal_realized_anual', 0),
        graficos_data.get('cal_no_cumplido_anual', 0),
        graficos_data.get('cal_pendiente_anual', 0)
    ]
    cal_colors = ['#28a745', '#dc3545', '#ffc107']  # Verde, Rojo, Amarillo

    chart_json_data.update({
        'calibraciones_torta_labels_json': json.dumps(cal_labels),
        'calibraciones_torta_data_json': json.dumps(cal_data),
        'pie_chart_colors_cal_json': json.dumps(cal_colors)
    })

    # Datos para gráficos de torta de mantenimientos (cumplimiento)
    mant_labels = ['Realizados', 'No Cumplidos', 'Pendientes/Programados']
    mant_data = [
        graficos_data.get('mant_realized_anual', 0),
        graficos_data.get('mant_no_cumplido_anual', 0),
        graficos_data.get('mant_pendiente_anual', 0)
    ]
    mant_colors = ['#28a745', '#dc3545', '#ffc107']

    chart_json_data.update({
        'mantenimientos_cumplimiento_torta_labels_json': json.dumps(mant_labels),
        'mantenimientos_cumplimiento_torta_data_json': json.dumps(mant_data),
        'pie_chart_colors_mant_compliance_json': json.dumps(mant_colors)
    })

    # Datos para gráficos de torta de mantenimientos por tipo
    mant_tipo_labels = graficos_data.get('mantenimientos_tipo_labels', [])
    mant_tipo_data = graficos_data.get('mantenimientos_tipo_data', [])
    mant_tipo_colors = graficos_data.get('pie_chart_colors_mant_types', ['#ffc107', '#dc3545', '#17a2b8', '#6c757d', '#8672cb'])

    chart_json_data.update({
        'mantenimientos_tipo_labels_json': json.dumps(mant_tipo_labels),
        'mantenimientos_tipo_data_json': json.dumps(mant_tipo_data),
        'pie_chart_colors_mant_types_json': json.dumps(mant_tipo_colors)
    })

    # Datos para gráficos de torta de comprobaciones
    comp_labels = ['Realizadas', 'No Cumplidas', 'Pendientes/Programadas']
    comp_data = [
        graficos_data.get('comp_realized_anual', 0),
        graficos_data.get('comp_no_cumplido_anual', 0),
        graficos_data.get('comp_pendiente_anual', 0)
    ]
    comp_colors = ['#28a745', '#dc3545', '#ffc107']

    chart_json_data.update({
        'comprobaciones_torta_labels_json': json.dumps(comp_labels),
        'comprobaciones_torta_data_json': json.dumps(comp_data),
        'pie_chart_colors_comp_json': json.dumps(comp_colors)
    })

    # Datos para gráficos de línea
    chart_json_data.update({
        'line_chart_labels_json': json.dumps(graficos_data.get('line_chart_labels', [])),
        'programmed_calibrations_line_data_json': json.dumps(graficos_data.get('programmed_calibrations_line_data', [])),
        'realized_calibrations_line_data_json': json.dumps(graficos_data.get('realized_calibrations_line_data', [])),
        'programmed_mantenimientos_line_data_json': json.dumps(graficos_data.get('programmed_mantenimientos_line_data', [])),
        'realized_preventive_mantenimientos_line_data_json': json.dumps(graficos_data.get('realized_preventive_mantenimientos_line_data', [])),
        'realized_corrective_mantenimientos_line_data_json': json.dumps(graficos_data.get('realized_corrective_mantenimientos_line_data', [])),
        'realized_other_mantenimientos_line_data_json': json.dumps(graficos_data.get('realized_other_mantenimientos_line_data', [])),
        'realized_predictive_mantenimientos_line_data_json': json.dumps(graficos_data.get('realized_predictive_mantenimientos_line_data', [])),
        'realized_inspection_mantenimientos_line_data_json': json.dumps(graficos_data.get('realized_inspection_mantenimientos_line_data', [])),
        'programmed_comprobaciones_line_data_json': json.dumps(graficos_data.get('programmed_comprobaciones_line_data', [])),
        'realized_comprobaciones_line_data_json': json.dumps(graficos_data.get('realized_comprobaciones_line_data', []))
    })

    return chart_json_data


def _process_projected_activities_for_pie(projected_activities, prefix):
    """Procesa actividades proyectadas para gráficos de torta"""

    total_programmed = len(projected_activities)
    realized = sum(1 for act in projected_activities if act['status'] == 'Realizado')
    no_cumplido = sum(1 for act in projected_activities if act['status'] == 'No Cumplido')
    pendiente = sum(1 for act in projected_activities if act['status'] == 'Pendiente/Programado')

    if total_programmed == 0:
        return {
            f'{prefix}_total_programmed_anual': 0,
            f'{prefix}_realized_anual': 0,
            f'{prefix}_no_cumplido_anual': 0,
            f'{prefix}_pendiente_anual': 0,
            f'{prefix}_realized_anual_percent': 0,
            f'{prefix}_no_cumplido_anual_percent': 0,
            f'{prefix}_pendiente_anual_percent': 0,
        }

    return {
        f'{prefix}_total_programmed_anual': total_programmed,
        f'{prefix}_realized_anual': realized,
        f'{prefix}_no_cumplido_anual': no_cumplido,
        f'{prefix}_pendiente_anual': pendiente,
        f'{prefix}_realized_anual_percent': round((realized / total_programmed) * 100),
        f'{prefix}_no_cumplido_anual_percent': round((no_cumplido / total_programmed) * 100),
        f'{prefix}_pendiente_anual_percent': round((pendiente / total_programmed) * 100),
    }


def _get_latest_corrective_maintenances(user, selected_company_id):
    """Obtiene los mantenimientos correctivos más recientes"""

    query = Mantenimiento.objects.filter(tipo_mantenimiento='Correctivo').order_by('-fecha_mantenimiento')

    if not user.is_superuser:
        if user.empresa:
            query = query.filter(equipo__empresa=user.empresa)
        else:
            query = Mantenimiento.objects.none()
    elif selected_company_id:
        query = query.filter(equipo__empresa_id=selected_company_id)

    return query[:5]  # Últimos 5


def _get_plan_info(user, selected_company_id):
    """Obtiene información del plan de la empresa"""
    empresa = None

    if not user.is_superuser:
        empresa = user.empresa
    elif selected_company_id:
        try:
            empresa = Empresa.objects.get(id=selected_company_id)
        except Empresa.DoesNotExist:
            empresa = None

    if not empresa:
        return {'plan_info': None}

    plan_actual = empresa.get_plan_actual()
    dias_restantes = empresa.get_dias_restantes_plan()

    # Convertir almacenamiento a formato legible
    almacenamiento_mb = empresa.get_limite_almacenamiento()
    if almacenamiento_mb >= 1000:
        almacenamiento_display = f"{almacenamiento_mb / 1000:.1f} GB".replace(".0", "")
    else:
        almacenamiento_display = f"{almacenamiento_mb} MB"

    plan_info = {
        'plan_actual': plan_actual,
        'limite_equipos_actual': empresa.get_limite_equipos(),
        'limite_almacenamiento_actual': almacenamiento_mb,
        'limite_almacenamiento_display': almacenamiento_display,
        'dias_restantes': dias_restantes if dias_restantes != float('inf') else 'inf'
    }

    return {'plan_info': plan_info}


def _get_prestamos_data(user, selected_company_id):
    """
    Obtiene datos de préstamos de equipos (NUEVO - NO modifica lógica existente)

    Esta función es completamente independiente y solo agrega nuevas estadísticas
    al dashboard sin afectar ninguna funcionalidad existente.
    """
    from core.models import PrestamoEquipo
    from datetime import timedelta

    # Filtrar préstamos según permisos del usuario
    prestamos_queryset = PrestamoEquipo.objects.select_related('equipo', 'empresa')

    if not user.is_superuser:
        if user.empresa:
            prestamos_queryset = prestamos_queryset.filter(empresa=user.empresa)
        else:
            prestamos_queryset = PrestamoEquipo.objects.none()
    elif selected_company_id:
        prestamos_queryset = prestamos_queryset.filter(empresa_id=selected_company_id)

    # Estadísticas de préstamos
    prestamos_activos = prestamos_queryset.filter(
        estado_prestamo='ACTIVO',
        fecha_devolucion_real__isnull=True
    )

    total_prestamos_activos = prestamos_activos.count()

    # Préstamos vencidos
    today = date.today()
    prestamos_vencidos_count = prestamos_activos.filter(
        fecha_devolucion_programada__isnull=False,
        fecha_devolucion_programada__lt=today
    ).count()

    # Devoluciones próximas (próximos 7 días)
    fecha_limite_proximas = today + timedelta(days=7)
    devoluciones_proximas_count = prestamos_activos.filter(
        fecha_devolucion_programada__isnull=False,
        fecha_devolucion_programada__gte=today,
        fecha_devolucion_programada__lte=fecha_limite_proximas
    ).count()

    return {
        'total_prestamos_activos': total_prestamos_activos,
        'prestamos_vencidos_count': prestamos_vencidos_count,
        'devoluciones_proximas_count': devoluciones_proximas_count,
    }


@login_required
@monitor_view
def get_chart_details(request):
    """
    API endpoint para obtener detalles de equipos en gráficas

    Parámetros:
    - chart_type: 'pie' o 'line'
    - activity_type: 'calibracion', 'mantenimiento', 'comprobacion'
    - status: 'Realizado', 'No Cumplido', 'Pendiente/Programado' (para pie)
    - month_index: 0-11 (para line)
    - data_type: 'programmed' o 'realized' (para line)
    """
    user = request.user
    today = date.today()
    current_year = today.year

    chart_type = request.GET.get('chart_type')
    activity_type = request.GET.get('activity_type')
    status_filter = request.GET.get('status')
    month_index = request.GET.get('month_index')
    data_type = request.GET.get('data_type')  # 'programmed' o 'realized'

    # Filtrado por empresa
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.filter(is_deleted=False)
    equipos_queryset = _get_equipos_queryset(user, selected_company_id, empresas_disponibles)

    # Para proyecciones anuales (tortas): incluir TODOS los equipos
    # Optimización: Prefetch del registro de baja para evitar N+1 queries
    equipos_para_proyecciones = equipos_queryset.select_related('baja_registro')

    # Para actividades programadas en líneas: solo equipos activos
    equipos_activos = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

    result = []

    if chart_type == 'pie':
        # Obtener actividades proyectadas del año (TODOS los equipos)
        if activity_type == 'calibracion':
            projected_activities = get_projected_activities_for_year(equipos_para_proyecciones, 'calibracion', current_year, today)
        elif activity_type == 'mantenimiento':
            projected_activities = get_projected_maintenance_compliance_for_year(equipos_para_proyecciones, current_year, today)
        elif activity_type == 'comprobacion':
            projected_activities = get_projected_activities_for_year(equipos_para_proyecciones, 'comprobacion', current_year, today)
        else:
            return JsonResponse({'error': 'Tipo de actividad inválido'}, status=400)

        # DEBUG: Log de actividades proyectadas
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"=== API CHART DETAILS DEBUG ===")
        logger.info(f"Activity type: {activity_type}")
        logger.info(f"Current year: {current_year}")
        logger.info(f"Today: {today}")
        logger.info(f"Equipos queryset count: {equipos_queryset.count()}")
        logger.info(f"Equipos para proyecciones count: {equipos_para_proyecciones.count()}")
        logger.info(f"Total projected activities: {len(projected_activities)}")
        logger.info(f"Status filter received: {status_filter}")

        # Contar por status y mostrar detalle
        status_counts = {}
        for act in projected_activities:
            status = act['status']
            status_counts[status] = status_counts.get(status, 0) + 1
            logger.info(f"  - {act['equipo'].codigo_interno}: {act['fecha_programada']} -> {status}")
        logger.info(f"Status distribution: {status_counts}")

        # Normalizar el status_filter para manejar plural/singular
        # Los labels de las gráficas están en plural pero los estados en singular
        status_map = {
            'Realizadas': 'Realizado',
            'No Cumplidas': 'No Cumplido',
            'Pendientes/Programadas': 'Pendiente/Programado',
            'Realizados': 'Realizado',
            'No Cumplidos': 'No Cumplido',
            'Pendientes/Programados': 'Pendiente/Programado'
        }

        # Inicializar normalized_status
        normalized_status = None

        # Si no hay status_filter o es "all", devolver todas
        if not status_filter or status_filter.lower() == 'all' or status_filter == 'Todas':
            filtered = projected_activities
            logger.info(f"Returning all activities: {len(filtered)}")
        else:
            normalized_status = status_map.get(status_filter, status_filter)
            logger.info(f"Normalized status: {normalized_status}")

            # Filtrar por estado
            filtered = [act for act in projected_activities if act['status'] == normalized_status]
            logger.info(f"Filtered activities count: {len(filtered)}")

        # Formatear para respuesta
        for act in filtered:
            justificacion = get_justificacion_incumplimiento(act['equipo'], act['status'])
            result.append({
                'codigo': act['equipo'].codigo_interno,
                'nombre': act['equipo'].nombre,
                'estado_equipo': act['equipo'].estado,
                'fecha_programada': act['fecha_programada'].strftime('%d/%m/%Y'),
                'status': act['status'],
                'justificacion': justificacion
            })

    elif chart_type == 'line':
        # Calcular rango de fechas (6 meses antes y después)
        start_date_range = today - relativedelta(months=6)
        start_date_range = start_date_range.replace(day=1)

        try:
            month_idx = int(month_index)
            target_month_date = start_date_range + relativedelta(months=month_idx)
            target_year = target_month_date.year
            target_month = target_month_date.month
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Índice de mes inválido'}, status=400)

        if data_type == 'programmed':
            # Obtener equipos con actividades programadas en ese mes (SOLO equipos activos)
            for equipo in equipos_activos:
                if activity_type == 'calibracion' and equipo.frecuencia_calibracion_meses:
                    latest_cal = equipo.calibraciones.order_by('-fecha_calibracion').first()
                    start_date = latest_cal.fecha_calibracion if latest_cal else equipo.fecha_adquisicion
                    freq = int(equipo.frecuencia_calibracion_meses)
                elif activity_type == 'mantenimiento' and equipo.frecuencia_mantenimiento_meses:
                    latest_mant = equipo.mantenimientos.order_by('-fecha_mantenimiento').first()
                    if latest_mant:
                        start_date = latest_mant.fecha_mantenimiento
                    else:
                        latest_cal = equipo.calibraciones.order_by('-fecha_calibracion').first()
                        start_date = latest_cal.fecha_calibracion if latest_cal else equipo.fecha_adquisicion
                    freq = int(equipo.frecuencia_mantenimiento_meses)
                elif activity_type == 'comprobacion' and equipo.frecuencia_comprobacion_meses:
                    latest_comp = equipo.comprobaciones.order_by('-fecha_comprobacion').first()
                    if latest_comp:
                        start_date = latest_comp.fecha_comprobacion
                    else:
                        latest_cal = equipo.calibraciones.order_by('-fecha_calibracion').first()
                        start_date = latest_cal.fecha_calibracion if latest_cal else equipo.fecha_adquisicion
                    freq = int(equipo.frecuencia_comprobacion_meses)
                else:
                    continue

                if not start_date or freq <= 0:
                    continue

                # Calcular si este equipo tiene actividad programada en el mes objetivo
                current_date = start_date
                while current_date.year < target_year or (current_date.year == target_year and current_date.month < target_month):
                    current_date += relativedelta(months=freq)

                if current_date.year == target_year and current_date.month == target_month:
                    result.append({
                        'codigo': equipo.codigo_interno,
                        'nombre': equipo.nombre,
                        'estado_equipo': equipo.estado,
                        'fecha_programada': current_date.strftime('%d/%m/%Y'),
                        'status': 'Programada'
                    })

        elif data_type == 'realized':
            # Obtener actividades realizadas en ese mes (TODOS los equipos)
            if activity_type == 'calibracion':
                actividades = Calibracion.objects.filter(
                    equipo__in=equipos_para_proyecciones,
                    fecha_calibracion__year=target_year,
                    fecha_calibracion__month=target_month
                ).select_related('equipo', 'equipo__empresa')

                for act in actividades:
                    result.append({
                        'codigo': act.equipo.codigo_interno,
                        'nombre': act.equipo.nombre,
                        'estado_equipo': act.equipo.estado,
                        'fecha_realizada': act.fecha_calibracion.strftime('%d/%m/%Y'),
                        'status': 'Realizada'
                    })

            elif activity_type == 'mantenimiento':
                actividades = Mantenimiento.objects.filter(
                    equipo__in=equipos_para_proyecciones,
                    fecha_mantenimiento__year=target_year,
                    fecha_mantenimiento__month=target_month
                ).select_related('equipo', 'equipo__empresa')

                for act in actividades:
                    result.append({
                        'codigo': act.equipo.codigo_interno,
                        'nombre': act.equipo.nombre,
                        'estado_equipo': act.equipo.estado,
                        'fecha_realizada': act.fecha_mantenimiento.strftime('%d/%m/%Y'),
                        'tipo': act.tipo_mantenimiento,
                        'status': 'Realizada'
                    })

            elif activity_type == 'comprobacion':
                actividades = Comprobacion.objects.filter(
                    equipo__in=equipos_para_proyecciones,
                    fecha_comprobacion__year=target_year,
                    fecha_comprobacion__month=target_month
                ).select_related('equipo', 'equipo__empresa')

                for act in actividades:
                    result.append({
                        'codigo': act.equipo.codigo_interno,
                        'nombre': act.equipo.nombre,
                        'estado_equipo': act.equipo.estado,
                        'fecha_realizada': act.fecha_comprobacion.strftime('%d/%m/%Y'),
                        'status': 'Realizada'
                    })

    else:
        return JsonResponse({'error': 'Tipo de gráfica inválido'}, status=400)

    # Información de debug
    debug_info = {
        'chart_type': chart_type,
        'activity_type': activity_type,
        'status_filter': status_filter if chart_type == 'pie' else None,
        'data_type': data_type if chart_type == 'line' else None,
        'equipos_queryset_count': equipos_queryset.count(),
        'equipos_para_proyecciones_count': equipos_para_proyecciones.count(),
        'equipos_activos_count': equipos_activos.count()
    }

    if chart_type == 'pie':
        debug_info['total_projected'] = len(projected_activities)
        debug_info['status_distribution'] = status_counts
        debug_info['normalized_status'] = normalized_status
        debug_info['filtered_count'] = len(filtered)

    return JsonResponse({
        'success': True,
        'data': result,
        'count': len(result),
        'debug': debug_info
    })