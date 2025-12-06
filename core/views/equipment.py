# core/views/equipment.py
# Views relacionadas con la gestión de equipos

from .base import *


def sanitize_filename(filename):
    """Sanitiza nombres de archivo para evitar problemas de seguridad"""
    import re
    # Corrigido: guion al final para evitar interpretación como rango de caracteres
    filename = re.sub(r'[^\w\s.-]', '', filename).strip()
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename


@monitor_view
@access_check
@login_required
@permission_required('core.view_equipo', raise_exception=True)
def home(request):
    """
    Página principal: Lista todos los equipos con filtrado y paginación.
    Implementa la funcionalidad completa del home original.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q
    from django.utils import timezone
    from django.contrib import messages
    from django.shortcuts import render
    from ..models import Equipo, Empresa
    from ..optimizations import OptimizedQueries

    user = request.user
    query = request.GET.get('q')
    tipo_equipo_filter = request.GET.get('tipo_equipo')
    estado_filter = request.GET.get('estado')

    # Lógica para el filtro de empresa para superusuarios y obtener info de formato
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.filter(is_deleted=False).order_by('nombre')

    # OPTIMIZACIÓN: select_related para evitar consultas N+1 en listado de equipos
    # IMPORTANTE: Solo mostrar equipos de empresas activas (no eliminadas)
    equipos_list = Equipo.objects.select_related('empresa').filter(empresa__is_deleted=False).order_by('codigo_interno')

    current_company_format_info = None

    if not user.is_superuser:
        # Los usuarios normales solo ven datos de su propia empresa
        if user.empresa and not user.empresa.is_deleted:
            equipos_list = equipos_list.filter(empresa=user.empresa)
            selected_company_id = str(user.empresa.id)
            current_company_format_info = user.empresa
        else:
            # Si un usuario normal no tiene empresa asignada o su empresa está eliminada, no ve equipos
            equipos_list = Equipo.objects.none()
            empresas_disponibles = Empresa.objects.none()

    else: # If user is superuser
        if selected_company_id:
            try:
                # Get the selected company object for format info (solo empresas activas)
                current_company_format_info = Empresa.objects.get(pk=selected_company_id, is_deleted=False)
                equipos_list = equipos_list.filter(empresa_id=selected_company_id)
            except Empresa.DoesNotExist:
                # Handle case where selected_company_id is invalid or company is deleted
                messages.error(request, 'La empresa seleccionada no existe o está eliminada.')
                equipos_list = Equipo.objects.none()

    # Lógica de validación de límite de equipos
    limite_alcanzado = False
    empresa_para_limite = None
    if user.is_authenticated and not user.is_superuser:
        empresa_para_limite = user.empresa
    elif user.is_superuser and selected_company_id:
        try:
            empresa_para_limite = Empresa.objects.get(pk=selected_company_id)
        except Empresa.DoesNotExist:
            empresa_para_limite = None

    if empresa_para_limite:
        # Obtener el límite de equipos usando el método del modelo Empresa
        limite_equipos_empresa = empresa_para_limite.get_limite_equipos()

        if limite_equipos_empresa is not None and limite_equipos_empresa != float('inf') and limite_equipos_empresa > 0:
            equipos_actuales = Equipo.objects.filter(empresa=empresa_para_limite).count()
            if equipos_actuales >= limite_equipos_empresa:
                limite_alcanzado = True

    today = timezone.localdate()

    # Filtrar por query de búsqueda
    if query:
        equipos_list = equipos_list.filter(
            Q(codigo_interno__icontains=query) |
            Q(nombre__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query) |
            Q(numero_serie__icontains=query) |
            Q(responsable__icontains=query) |
            Q(ubicacion__icontains=query)
        )

    # Filtrar por tipo de equipo
    if tipo_equipo_filter:
        equipos_list = equipos_list.filter(tipo_equipo=tipo_equipo_filter)

    # Filtro por estado
    if estado_filter:
        equipos_list = equipos_list.filter(estado=estado_filter)
    else:
        # Por defecto, no mostrar "De Baja" a menos que se filtre explícitamente por él
        if not user.is_superuser or (user.is_superuser and not selected_company_id):
            equipos_list = equipos_list.exclude(estado='De Baja').exclude(estado='Inactivo')

    # Añadir lógica para el estado de las fechas de próxima actividad
    for equipo in equipos_list:
        # Calibración
        if equipo.proxima_calibracion and equipo.estado not in ['De Baja', 'Inactivo']:
            days_remaining = (equipo.proxima_calibracion - today).days
            if days_remaining < 0:
                equipo.proxima_calibracion_status = 'text-red-600 font-bold'
            elif days_remaining <= 15:
                equipo.proxima_calibracion_status = 'text-yellow-600 font-bold'
            elif days_remaining <= 30:
                equipo.proxima_calibracion_status = 'text-green-600'
            else:
                equipo.proxima_calibracion_status = 'text-gray-900'
        else:
            equipo.proxima_calibracion_status = 'text-gray-500'

        # Mantenimiento
        if equipo.proximo_mantenimiento and equipo.estado not in ['De Baja', 'Inactivo']:
            days_remaining = (equipo.proximo_mantenimiento - today).days
            if days_remaining < 0:
                equipo.proximo_mantenimiento_status = 'text-red-600 font-bold'
            elif days_remaining <= 15:
                equipo.proximo_mantenimiento_status = 'text-yellow-600 font-bold'
            elif days_remaining <= 30:
                equipo.proximo_mantenimiento_status = 'text-green-600'
            else:
                equipo.proximo_mantenimiento_status = 'text-gray-900'
        else:
            equipo.proximo_mantenimiento_status = 'text-gray-500'

        # Comprobación
        if equipo.proxima_comprobacion and equipo.estado not in ['De Baja', 'Inactivo']:
            days_remaining = (equipo.proxima_comprobacion - today).days
            if days_remaining < 0:
                equipo.proxima_comprobacion_status = 'text-red-600 font-bold'
            elif days_remaining <= 15:
                equipo.proxima_comprobacion_status = 'text-yellow-600 font-bold'
            elif days_remaining <= 30:
                equipo.proxima_comprobacion_status = 'text-green-600'
            else:
                equipo.proxima_comprobacion_status = 'text-gray-900'
        else:
            equipo.proxima_comprobacion_status = 'text-gray-500'

    # Paginación
    paginator = Paginator(equipos_list, settings.SAM_CONFIG['PAGINATION_SIZE'])
    page_number = request.GET.get('page')

    try:
        equipos = paginator.page(page_number)
    except PageNotAnInteger:
        equipos = paginator.page(1)
    except EmptyPage:
        equipos = paginator.page(paginator.num_pages)

    tipo_equipo_choices = Equipo.TIPO_EQUIPO_CHOICES
    estado_choices = Equipo.ESTADO_CHOICES

    # Obtener próximas actividades usando las optimizaciones
    proximas_actividades = OptimizedQueries.get_proximas_actividades(user, days_ahead=30)

    context = {
        'equipos': equipos,
        'query': query,
        'tipo_equipo_choices': tipo_equipo_choices,
        'estado_choices': estado_choices,
        'titulo_pagina': 'Listado de Equipos',
        'is_superuser': user.is_superuser,
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,
        'current_company_format_info': current_company_format_info,
        'limite_alcanzado': limite_alcanzado,
        'proximas_actividades': proximas_actividades,
    }
    return render(request, 'core/home.html', context)


@access_check
@login_required
@trial_check
@permission_required('core.add_equipo', raise_exception=True)
@monitor_view
def equipos(request):
    """
    Lista todos los equipos con filtros y paginación optimizada
    """
    user = request.user

    # Query base optimizada usando las optimizaciones
    from ..optimizations import OptimizedQueries
    equipos_queryset = OptimizedQueries.get_equipos_optimized(user=user)

    # Filtros de búsqueda
    query = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '')
    empresa_filtro = request.GET.get('empresa_id', '')

    if query:
        equipos_queryset = equipos_queryset.filter(
            Q(codigo_interno__icontains=query) |
            Q(nombre__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query) |
            Q(numero_serie__icontains=query)
        )

    if estado_filtro:
        equipos_queryset = equipos_queryset.filter(estado=estado_filtro)

    if empresa_filtro and user.is_superuser:
        equipos_queryset = equipos_queryset.filter(empresa_id=empresa_filtro)

    # Paginación optimizada
    paginator = Paginator(equipos_queryset, settings.SAM_CONFIG['PAGINATION_SIZE'])
    page_number = request.GET.get('page')
    try:
        equipos_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        equipos_page = paginator.get_page(1)
    except EmptyPage:
        equipos_page = paginator.get_page(paginator.num_pages)

    # Datos para filtros
    empresas_disponibles = Empresa.objects.all().order_by('nombre') if user.is_superuser else []

    context = {
        'equipos': equipos_page,
        'query': query,
        'estado_filtro': estado_filtro,
        'empresa_filtro': empresa_filtro,
        'estados_choices': Equipo.ESTADO_CHOICES,
        'empresas_disponibles': empresas_disponibles,
        'titulo_pagina': 'Lista de Equipos'
    }

    return render(request, 'core/equipos.html', context)


@access_check
@login_required
@trial_check
@permission_required('core.add_equipo', raise_exception=True)
@monitor_view
def añadir_equipo(request):
    """
    Añade un nuevo equipo con validaciones de límites y archivos
    """
    empresa_actual = _get_user_empresa(request.user)
    limite_alcanzado = _check_equipment_limit(empresa_actual)

    if request.method == 'POST':
        return _process_add_equipment_form(request, empresa_actual, limite_alcanzado)
    else:
        form = EquipoForm(request=request)

    context = {
        'form': form,
        'titulo_pagina': 'Añadir Nuevo Equipo',
        'limite_alcanzado': limite_alcanzado,
    }
    return render(request, 'core/añadir_equipo.html', context)


def _generar_grafica_hist_confirmaciones(calibraciones_con_datos):
    """
    Genera gráfica SVG histórica de confirmaciones metrológicas.
    Muestra múltiples calibraciones (hasta 5) con sus puntos y límites EMP.
    Incluye barras de incertidumbre (±) en cada punto.
    """
    if not calibraciones_con_datos or len(calibraciones_con_datos) == 0:
        return None

    # Colores para cada calibración
    colores = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444']

    width, height = 700, 400
    margin = {'top': 50, 'right': 20, 'bottom': 70, 'left': 70}
    plot_width = width - margin['left'] - margin['right']
    plot_height = height - margin['top'] - margin['bottom']

    # Extraer todos los puntos nominales únicos de todas las calibraciones
    nominales_unicos = set()
    for cal in calibraciones_con_datos:
        for punto in cal['puntos']:
            nominales_unicos.add(punto['nominal'])
    nominales_unicos = sorted(list(nominales_unicos))

    if len(nominales_unicos) == 0:
        return None

    # Obtener EMPs del último registro (calibración más reciente)
    ultima_cal = calibraciones_con_datos[0]
    emp_por_nominal = {}
    for punto in ultima_cal['puntos']:
        emp_por_nominal[punto['nominal']] = punto.get('emp_absoluto', 0)

    # Calcular rangos para ejes usando PORCENTAJE del nominal
    # Esto permite que puntos con diferentes nominales se vean bien
    todos_errores_porcentaje = []
    for cal in calibraciones_con_datos:
        for punto in cal['puntos']:
            nominal = punto['nominal']
            if nominal != 0:
                error_porcentaje = (punto.get('error', 0) / abs(nominal)) * 100
                todos_errores_porcentaje.append(error_porcentaje)
            else:
                todos_errores_porcentaje.append(punto.get('error', 0))

    # También incluir EMPs como porcentaje
    emps_porcentaje = []
    for nominal, emp in emp_por_nominal.items():
        if nominal != 0:
            emp_porcentaje = (emp / abs(nominal)) * 100
            emps_porcentaje.append(emp_porcentaje)
        else:
            emps_porcentaje.append(emp)

    if len(todos_errores_porcentaje) == 0:
        return None

    max_error_pct = max(todos_errores_porcentaje + emps_porcentaje + [-v for v in emps_porcentaje])
    min_error_pct = min(todos_errores_porcentaje + emps_porcentaje + [-v for v in emps_porcentaje])
    rango = max_error_pct - min_error_pct
    padding = rango * 0.20

    y_max = max_error_pct + padding
    y_min = min_error_pct - padding

    def escala_y(valor):
        return margin['top'] + plot_height - ((valor - y_min) / (y_max - y_min)) * plot_height

    def escala_x(index):
        if len(nominales_unicos) == 1:
            return margin['left'] + plot_width / 2
        return margin['left'] + (index / (len(nominales_unicos) - 1)) * plot_width

    # Comenzar SVG
    svg = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']

    # Título
    svg.append(f'<text x="{width/2}" y="25" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#2D3748">Historial de Confirmaciones Metrológicas (Últimas {len(calibraciones_con_datos)})</text>')

    # Cuadrícula y ejes Y
    num_ticks = 6
    for i in range(num_ticks + 1):
        valor = y_min + (y_max - y_min) * (i / num_ticks)
        y = escala_y(valor)
        svg.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{margin["left"] + plot_width}" y2="{y}" stroke="#E5E7EB" stroke-width="1"/>')
        svg.append(f'<text x="{margin["left"] - 5}" y="{y + 4}" text-anchor="end" font-family="Arial" font-size="9" fill="#6B7280">{valor:.3f}</text>')

    # Ejes
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_height}" stroke="#374151" stroke-width="2"/>')
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_height}" x2="{margin["left"] + plot_width}" y2="{margin["top"] + plot_height}" stroke="#374151" stroke-width="2"/>')

    # Línea de cero
    y0 = escala_y(0)
    svg.append(f'<line x1="{margin["left"]}" y1="{y0}" x2="{margin["left"] + plot_width}" y2="{y0}" stroke="#9CA3AF" stroke-width="1" stroke-dasharray="3,3"/>')

    # Límites EMP (del último registro) - convertir a porcentaje
    for i, nominal in enumerate(nominales_unicos):
        x = escala_x(i)
        emp = emp_por_nominal.get(nominal, 0)

        # Convertir EMP a porcentaje del nominal
        if nominal != 0:
            emp_pct = (emp / abs(nominal)) * 100
        else:
            emp_pct = emp

        y_sup = escala_y(emp_pct)
        y_inf = escala_y(-emp_pct)

        # Líneas verticales de límites
        svg.append(f'<line x1="{x}" y1="{y_sup}" x2="{x}" y2="{y_inf}" stroke="#dc2626" stroke-width="1" opacity="0.3"/>')

        if i < len(nominales_unicos) - 1:
            x_next = escala_x(i + 1)
            emp_next = emp_por_nominal.get(nominales_unicos[i + 1], emp)
            nominal_next = nominales_unicos[i + 1]

            if nominal_next != 0:
                emp_next_pct = (emp_next / abs(nominal_next)) * 100
            else:
                emp_next_pct = emp_next

            y_sup_next = escala_y(emp_next_pct)
            y_inf_next = escala_y(-emp_next_pct)

            # Líneas horizontales conectando límites
            svg.append(f'<line x1="{x}" y1="{y_sup}" x2="{x_next}" y2="{y_sup_next}" stroke="#dc2626" stroke-width="2" stroke-dasharray="5,5"/>')
            svg.append(f'<line x1="{x}" y1="{y_inf}" x2="{x_next}" y2="{y_inf_next}" stroke="#dc2626" stroke-width="2" stroke-dasharray="5,5"/>')

    # Dibujar líneas y puntos de cada calibración
    for idx_cal, cal in enumerate(calibraciones_con_datos):
        color = colores[idx_cal % len(colores)]

        # Organizar puntos por nominal
        puntos_por_nominal = {p['nominal']: p for p in cal['puntos']}

        # Dibujar línea conectando puntos
        path_points = []
        for i, nominal in enumerate(nominales_unicos):
            if nominal in puntos_por_nominal:
                punto = puntos_por_nominal[nominal]
                x = escala_x(i)

                # Convertir error a porcentaje del nominal
                error = punto.get('error', 0)
                if nominal != 0:
                    error_pct = (error / abs(nominal)) * 100
                else:
                    error_pct = error

                y = escala_y(error_pct)
                path_points.append(f"{x},{y}")

        if len(path_points) > 1:
            svg.append(f'<polyline points="{" ".join(path_points)}" fill="none" stroke="{color}" stroke-width="2" opacity="0.7"/>')

        # Dibujar puntos con barras de incertidumbre
        for i, nominal in enumerate(nominales_unicos):
            if nominal in puntos_por_nominal:
                punto = puntos_por_nominal[nominal]
                x = escala_x(i)
                error = punto.get('error', 0)
                incertidumbre = punto.get('incertidumbre', 0)

                # Convertir error e incertidumbre a porcentaje del nominal
                if nominal != 0:
                    error_pct = (error / abs(nominal)) * 100
                    incertidumbre_pct = (incertidumbre / abs(nominal)) * 100
                else:
                    error_pct = error
                    incertidumbre_pct = incertidumbre

                y = escala_y(error_pct)
                y_sup_inc = escala_y(error_pct + incertidumbre_pct)
                y_inf_inc = escala_y(error_pct - incertidumbre_pct)

                # Barra de incertidumbre
                if incertidumbre_pct > 0:
                    svg.append(f'<line x1="{x}" y1="{y_inf_inc}" x2="{x}" y2="{y_sup_inc}" stroke="{color}" stroke-width="1.5" opacity="0.5"/>')
                    svg.append(f'<line x1="{x-3}" y1="{y_sup_inc}" x2="{x+3}" y2="{y_sup_inc}" stroke="{color}" stroke-width="1.5" opacity="0.5"/>')
                    svg.append(f'<line x1="{x-3}" y1="{y_inf_inc}" x2="{x+3}" y2="{y_inf_inc}" stroke="{color}" stroke-width="1.5" opacity="0.5"/>')

                # Punto
                svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="white" stroke-width="2"/>')

    # Etiquetas eje X
    for i, nominal in enumerate(nominales_unicos):
        if i % max(1, len(nominales_unicos) // 8) == 0 or i == len(nominales_unicos) - 1:
            x = escala_x(i)
            svg.append(f'<text x="{x}" y="{margin["top"] + plot_height + 20}" text-anchor="middle" font-family="Arial" font-size="9" fill="#4B5563">{nominal:.2f}</text>')

    svg.append(f'<text x="{width/2}" y="{height - 15}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#374151">Valor Nominal</text>')
    svg.append(f'<text x="20" y="{height/2}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#374151" transform="rotate(-90 20 {height/2})">Error (%)</text>')

    # Leyenda debajo de la gráfica (horizontal)
    leyenda_y = height - 5
    leyenda_x_start = margin['left']
    svg.append(f'<text x="{leyenda_x_start}" y="{leyenda_y}" font-family="Arial" font-size="9" font-weight="bold" fill="#374151">Calibraciones:</text>')

    x_offset = leyenda_x_start + 70
    for idx_cal, cal in enumerate(calibraciones_con_datos):
        color = colores[idx_cal % len(colores)]
        svg.append(f'<circle cx="{x_offset}" cy="{leyenda_y - 3}" r="3" fill="{color}"/>')
        fecha_str = cal['fecha'].strftime('%d/%m/%Y') if hasattr(cal['fecha'], 'strftime') else str(cal['fecha'])
        svg.append(f'<text x="{x_offset + 8}" y="{leyenda_y}" font-family="Arial" font-size="8" fill="#4B5563">{fecha_str}</text>')
        x_offset += 90

    svg.append('</svg>')
    return ''.join(svg)


def _generar_grafica_hist_comprobaciones(comprobaciones_con_datos):
    """
    Genera gráfica SVG histórica de comprobaciones.
    Similar a confirmaciones pero sin barras de incertidumbre.
    """
    if not comprobaciones_con_datos or len(comprobaciones_con_datos) == 0:
        return None

    colores = ['#06b6d4', '#84cc16', '#f97316', '#a855f7', '#ec4899']

    width, height = 700, 400
    margin = {'top': 50, 'right': 20, 'bottom': 70, 'left': 70}
    plot_width = width - margin['left'] - margin['right']
    plot_height = height - margin['top'] - margin['bottom']

    # Extraer nominales únicos
    nominales_unicos = set()
    for comp in comprobaciones_con_datos:
        for punto in comp['puntos']:
            nominales_unicos.add(punto['nominal'])
    nominales_unicos = sorted(list(nominales_unicos))

    if len(nominales_unicos) == 0:
        return None

    # EMPs del último registro
    ultima_comp = comprobaciones_con_datos[0]
    emp_por_nominal = {}
    for punto in ultima_comp['puntos']:
        emp_por_nominal[punto['nominal']] = punto.get('emp_absoluto', 0)

    # Calcular rangos usando PORCENTAJE del nominal
    todos_errores_porcentaje = []
    for comp in comprobaciones_con_datos:
        for punto in comp['puntos']:
            nominal = punto['nominal']
            if nominal != 0:
                error_porcentaje = (punto.get('error', 0) / abs(nominal)) * 100
                todos_errores_porcentaje.append(error_porcentaje)
            else:
                todos_errores_porcentaje.append(punto.get('error', 0))

    # EMPs como porcentaje
    emps_porcentaje = []
    for nominal, emp in emp_por_nominal.items():
        if nominal != 0:
            emp_porcentaje = (emp / abs(nominal)) * 100
            emps_porcentaje.append(emp_porcentaje)
        else:
            emps_porcentaje.append(emp)

    if len(todos_errores_porcentaje) == 0:
        return None

    max_error_pct = max(todos_errores_porcentaje + emps_porcentaje + [-v for v in emps_porcentaje])
    min_error_pct = min(todos_errores_porcentaje + emps_porcentaje + [-v for v in emps_porcentaje])
    rango = max_error_pct - min_error_pct
    padding = rango * 0.20

    y_max = max_error_pct + padding
    y_min = min_error_pct - padding

    def escala_y(valor):
        return margin['top'] + plot_height - ((valor - y_min) / (y_max - y_min)) * plot_height

    def escala_x(index):
        if len(nominales_unicos) == 1:
            return margin['left'] + plot_width / 2
        return margin['left'] + (index / (len(nominales_unicos) - 1)) * plot_width

    # SVG
    svg = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    svg.append(f'<text x="{width/2}" y="25" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#2D3748">Historial de Comprobaciones (Últimas {len(comprobaciones_con_datos)})</text>')

    # Cuadrícula
    num_ticks = 6
    for i in range(num_ticks + 1):
        valor = y_min + (y_max - y_min) * (i / num_ticks)
        y = escala_y(valor)
        svg.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{margin["left"] + plot_width}" y2="{y}" stroke="#E5E7EB" stroke-width="1"/>')
        svg.append(f'<text x="{margin["left"] - 5}" y="{y + 4}" text-anchor="end" font-family="Arial" font-size="9" fill="#6B7280">{valor:.3f}</text>')

    # Ejes
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_height}" stroke="#374151" stroke-width="2"/>')
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_height}" x2="{margin["left"] + plot_width}" y2="{margin["top"] + plot_height}" stroke="#374151" stroke-width="2"/>')

    # Línea cero
    y0 = escala_y(0)
    svg.append(f'<line x1="{margin["left"]}" y1="{y0}" x2="{margin["left"] + plot_width}" y2="{y0}" stroke="#9CA3AF" stroke-width="1" stroke-dasharray="3,3"/>')

    # Límites EMP - convertir a porcentaje
    for i, nominal in enumerate(nominales_unicos):
        x = escala_x(i)
        emp = emp_por_nominal.get(nominal, 0)

        # Convertir a porcentaje
        if nominal != 0:
            emp_pct = (emp / abs(nominal)) * 100
        else:
            emp_pct = emp

        y_sup = escala_y(emp_pct)
        y_inf = escala_y(-emp_pct)

        svg.append(f'<line x1="{x}" y1="{y_sup}" x2="{x}" y2="{y_inf}" stroke="#dc2626" stroke-width="1" opacity="0.3"/>')

        if i < len(nominales_unicos) - 1:
            x_next = escala_x(i + 1)
            emp_next = emp_por_nominal.get(nominales_unicos[i + 1], emp)
            nominal_next = nominales_unicos[i + 1]

            if nominal_next != 0:
                emp_next_pct = (emp_next / abs(nominal_next)) * 100
            else:
                emp_next_pct = emp_next

            y_sup_next = escala_y(emp_next_pct)
            y_inf_next = escala_y(-emp_next_pct)

            svg.append(f'<line x1="{x}" y1="{y_sup}" x2="{x_next}" y2="{y_sup_next}" stroke="#dc2626" stroke-width="2" stroke-dasharray="5,5"/>')
            svg.append(f'<line x1="{x}" y1="{y_inf}" x2="{x_next}" y2="{y_inf_next}" stroke="#dc2626" stroke-width="2" stroke-dasharray="5,5"/>')

    # Líneas y puntos de cada comprobación
    for idx_comp, comp in enumerate(comprobaciones_con_datos):
        color = colores[idx_comp % len(colores)]
        puntos_por_nominal = {p['nominal']: p for p in comp['puntos']}

        path_points = []
        for i, nominal in enumerate(nominales_unicos):
            if nominal in puntos_por_nominal:
                punto = puntos_por_nominal[nominal]
                x = escala_x(i)

                # Convertir error a porcentaje
                error = punto.get('error', 0)
                if nominal != 0:
                    error_pct = (error / abs(nominal)) * 100
                else:
                    error_pct = error

                y = escala_y(error_pct)
                path_points.append(f"{x},{y}")

        if len(path_points) > 1:
            svg.append(f'<polyline points="{" ".join(path_points)}" fill="none" stroke="{color}" stroke-width="2" opacity="0.7"/>')

        for i, nominal in enumerate(nominales_unicos):
            if nominal in puntos_por_nominal:
                punto = puntos_por_nominal[nominal]
                x = escala_x(i)
                error = punto.get('error', 0)

                # Convertir error a porcentaje
                if nominal != 0:
                    error_pct = (error / abs(nominal)) * 100
                else:
                    error_pct = error

                y = escala_y(error_pct)
                svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="white" stroke-width="2"/>')

    # Etiquetas
    for i, nominal in enumerate(nominales_unicos):
        if i % max(1, len(nominales_unicos) // 8) == 0 or i == len(nominales_unicos) - 1:
            x = escala_x(i)
            svg.append(f'<text x="{x}" y="{margin["top"] + plot_height + 20}" text-anchor="middle" font-family="Arial" font-size="9" fill="#4B5563">{nominal:.2f}</text>')

    svg.append(f'<text x="{width/2}" y="{height - 15}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#374151">Valor Nominal</text>')
    svg.append(f'<text x="20" y="{height/2}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#374151" transform="rotate(-90 20 {height/2})">Error (%)</text>')

    # Leyenda debajo de la gráfica (horizontal)
    leyenda_y = height - 5
    leyenda_x_start = margin['left']
    svg.append(f'<text x="{leyenda_x_start}" y="{leyenda_y}" font-family="Arial" font-size="9" font-weight="bold" fill="#374151">Comprobaciones:</text>')

    x_offset = leyenda_x_start + 85
    for idx_comp, comp in enumerate(comprobaciones_con_datos):
        color = colores[idx_comp % len(colores)]
        svg.append(f'<circle cx="{x_offset}" cy="{leyenda_y - 3}" r="3" fill="{color}"/>')
        fecha_str = comp['fecha'].strftime('%d/%m/%Y') if hasattr(comp['fecha'], 'strftime') else str(comp['fecha'])
        svg.append(f'<text x="{x_offset + 8}" y="{leyenda_y}" font-family="Arial" font-size="8" fill="#4B5563">{fecha_str}</text>')
        x_offset += 90

    svg.append('</svg>')
    return ''.join(svg)


@access_check
@login_required
@monitor_view
def detalle_equipo(request, pk):
    """
    Muestra los detalles completos de un equipo con todas sus actividades
    """
    # Query optimizada con prefetch_related
    equipo = get_object_or_404(
        Equipo.objects.select_related('empresa').prefetch_related(
            Prefetch('calibraciones', queryset=Calibracion.objects.select_related('proveedor').order_by('-fecha_calibracion')),
            Prefetch('mantenimientos', queryset=Mantenimiento.objects.select_related('proveedor').order_by('-fecha_mantenimiento')),
            Prefetch('comprobaciones', queryset=Comprobacion.objects.select_related('proveedor').order_by('-fecha_comprobacion')),
            'baja_registro'
        ),
        pk=pk
    )

    # Verificar permisos
    if not request.user.is_superuser:
        if not request.user.empresa or equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permisos para ver este equipo.')
            return redirect('core:home')

    # Calcular métricas del equipo
    equipment_metrics = _calculate_equipment_metrics(equipo)

    # URLs seguras para archivos
    file_urls = _get_equipment_file_urls(equipo)

    # Próximas actividades
    next_activities = _get_next_activities(equipo)

    # Obtener información de baja si existe
    baja_registro = None
    documento_baja_url = None
    try:
        baja_registro = equipo.baja_registro
        # SOLO mostrar documento de baja si el equipo realmente está dado de baja
        if (baja_registro and baja_registro.documento_baja and
            equipo.estado == 'De Baja'):
            # Crear URL para documento de baja
            from django.core.files.storage import default_storage
            try:
                if default_storage.exists(baja_registro.documento_baja.name):
                    documento_baja_url = default_storage.url(baja_registro.documento_baja.name)
            except:
                documento_baja_url = None
    except:
        pass


    # NUEVO: Obtener equipos anterior y siguiente (2025-11-19)
    empresa = request.user.empresa if not request.user.is_superuser else equipo.empresa
    equipos_empresa = Equipo.objects.filter(empresa=empresa).order_by('codigo_interno')
    equipos_ids = list(equipos_empresa.values_list('id', flat=True))

    prev_equipo_id = None
    next_equipo_id = None
    current_position = None
    total_equipos = len(equipos_ids)

    try:
        current_index = equipos_ids.index(equipo.id)
        prev_equipo_id = equipos_ids[current_index - 1] if current_index > 0 else None
        next_equipo_id = equipos_ids[current_index + 1] if current_index < len(equipos_ids) - 1 else None
        current_position = current_index + 1
    except ValueError:
        pass

    # ========== GRÁFICAS HISTÓRICAS ==========
    # Obtener últimas 5 confirmaciones con datos JSON
    calibraciones_con_datos = []
    for cal in equipo.calibraciones.all()[:5]:
        if hasattr(cal, 'confirmacion_metrologica_datos') and cal.confirmacion_metrologica_datos and cal.confirmacion_metrologica_datos.get('puntos_medicion'):
            calibraciones_con_datos.append({
                'fecha': cal.fecha_calibracion,
                'puntos': cal.confirmacion_metrologica_datos['puntos_medicion']
            })

    # Obtener últimas 5 comprobaciones con datos JSON
    comprobaciones_con_datos = []
    for comp in equipo.comprobaciones.all()[:5]:
        if hasattr(comp, 'datos_comprobacion') and comp.datos_comprobacion and comp.datos_comprobacion.get('puntos_medicion'):
            comprobaciones_con_datos.append({
                'fecha': comp.fecha_comprobacion,
                'puntos': comp.datos_comprobacion['puntos_medicion']
            })

    # Generar gráficas SVG
    grafica_hist_confirmaciones = None
    mensaje_confirmaciones = None
    if len(calibraciones_con_datos) > 0:
        grafica_hist_confirmaciones = _generar_grafica_hist_confirmaciones(calibraciones_con_datos)
    else:
        # Verificar si hay calibraciones pero sin datos de plataforma
        total_calibraciones = equipo.calibraciones.count()
        if total_calibraciones > 0:
            mensaje_confirmaciones = f"Este equipo tiene {total_calibraciones} calibración(es) registrada(s). Para visualizar el análisis histórico, es necesario registrar las confirmaciones metrológicas utilizando el formato de la plataforma."
        else:
            mensaje_confirmaciones = "No hay confirmaciones metrológicas registradas para este equipo."

    grafica_hist_comprobaciones = None
    mensaje_comprobaciones = None
    if len(comprobaciones_con_datos) > 0:
        grafica_hist_comprobaciones = _generar_grafica_hist_comprobaciones(comprobaciones_con_datos)
    else:
        # Verificar si hay comprobaciones pero sin datos de plataforma
        total_comprobaciones = equipo.comprobaciones.count()
        if total_comprobaciones > 0:
            mensaje_comprobaciones = f"Este equipo tiene {total_comprobaciones} comprobación(es) registrada(s). Para visualizar el análisis histórico, es necesario registrar las comprobaciones utilizando el formato de la plataforma."
        else:
            mensaje_comprobaciones = "No hay comprobaciones registradas para este equipo."

    context = {
        'equipo': equipo,
        'titulo_pagina': f'Detalle del Equipo: {equipo.codigo_interno}',
        'baja_registro': baja_registro if equipo.estado == 'De Baja' else None,
        'documento_baja_url': documento_baja_url,
        # Agregar las actividades al contexto
        'calibraciones': equipo.calibraciones.all(),
        'mantenimientos': equipo.mantenimientos.all(),
        'comprobaciones': equipo.comprobaciones.all(),
        # Navegación entre equipos (NUEVO 2025-11-19)
        'prev_equipo_id': prev_equipo_id,
        'next_equipo_id': next_equipo_id,
        'current_position': current_position,
        'total_equipos': total_equipos,
        # Gráficas históricas (NUEVO 2025-12-04)
        'grafica_hist_confirmaciones': grafica_hist_confirmaciones,
        'mensaje_confirmaciones': mensaje_confirmaciones,
        'grafica_hist_comprobaciones': grafica_hist_comprobaciones,
        'mensaje_comprobaciones': mensaje_comprobaciones,
        **equipment_metrics,
        **file_urls,
        **next_activities
    }

    return render(request, 'core/detalle_equipo.html', context)


@access_check
@login_required
@trial_check
@permission_required('core.change_equipo', raise_exception=True)
@monitor_view
def editar_equipo(request, pk):
    """
    Edita un equipo existente con navegación anterior/siguiente
    """
    equipo = get_object_or_404(Equipo, pk=pk)

    # Verificar permisos
    if not request.user.is_superuser:
        if not request.user.empresa or equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permisos para editar este equipo.')
            return redirect('core:home')

    # NUEVO: Obtener equipos anterior y siguiente de la misma empresa
    empresa = request.user.empresa if not request.user.is_superuser else equipo.empresa
    equipos_empresa = Equipo.objects.filter(
        empresa=empresa
    ).order_by('codigo_interno')  # Ordenar por código interno

    # Buscar índice actual
    equipos_ids = list(equipos_empresa.values_list('id', flat=True))
    try:
        current_index = equipos_ids.index(equipo.id)

        # Equipo anterior
        prev_equipo_id = equipos_ids[current_index - 1] if current_index > 0 else None

        # Equipo siguiente
        next_equipo_id = equipos_ids[current_index + 1] if current_index < len(equipos_ids) - 1 else None

        current_position = current_index + 1
    except ValueError:
        prev_equipo_id = None
        next_equipo_id = None
        current_position = None

    if request.method == 'POST':
        # Verificar qué botón se presionó
        if 'save_and_next' in request.POST and next_equipo_id:
            # Guardar y ir al siguiente
            result = _process_edit_equipment_form(request, equipo)
            if isinstance(result, HttpResponseRedirect):
                # Si guardó correctamente, redirigir al siguiente
                return redirect('core:editar_equipo', pk=next_equipo_id)
            return result
        elif 'save_and_prev' in request.POST and prev_equipo_id:
            # Guardar y ir al anterior
            result = _process_edit_equipment_form(request, equipo)
            if isinstance(result, HttpResponseRedirect):
                # Si guardó correctamente, redirigir al anterior
                return redirect('core:editar_equipo', pk=prev_equipo_id)
            return result
        else:
            # Guardado normal
            return _process_edit_equipment_form(request, equipo)
    else:
        form = EquipoForm(instance=equipo, request=request)

    context = {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Editar Equipo: {equipo.codigo_interno}',
        # NUEVO: Datos de navegación
        'prev_equipo_id': prev_equipo_id,
        'next_equipo_id': next_equipo_id,
        'current_position': current_position,
        'total_equipos': equipos_empresa.count(),
    }

    return render(request, 'core/editar_equipo.html', context)


@access_check
@login_required
@trial_check
@monitor_view
def eliminar_equipo(request, pk):
    """
    Elimina un equipo individual.
    Solo ADMINISTRADOR, GERENCIA y SuperUsuario pueden eliminar.
    MODIFICADO 2025-11-19: Usar permisos basados en roles
    """
    # Verificar permisos usando la propiedad del modelo
    if not request.user.puede_eliminar_equipos:
        messages.error(request, 'No tienes permisos para eliminar equipos. Solo Administradores y Gerentes pueden hacerlo.')
        return redirect('core:home')

    equipo = get_object_or_404(Equipo, pk=pk)

    # Verificar que el equipo pertenece a la empresa del usuario
    if not request.user.is_superuser:
        if equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permiso para eliminar este equipo.')
            return redirect('core:home')

    if request.method == 'POST':
        try:
            codigo_interno = equipo.codigo_interno
            equipo.delete()
            messages.success(request, f'Equipo {codigo_interno} eliminado exitosamente.')
        except Exception as e:
            logger.error(f"Error eliminando equipo {equipo.codigo_interno}: {e}")
            messages.error(request, f'Error al eliminar equipo: {str(e)}')

        return redirect('core:home')

    # Vista GET - Confirmación
    return render(request, 'core/eliminar_equipo.html', {
        'equipo': equipo,
        'titulo_pagina': f'Eliminar Equipo: {equipo.codigo_interno}'
    })


@access_check
@login_required
@trial_check
@monitor_view
def dar_baja_equipo(request, equipo_pk):
    """
    Da de baja un equipo con justificación
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos
    if not request.user.is_superuser:
        if not request.user.empresa or equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permisos para dar de baja este equipo.')
            return redirect('core:home')

    if request.method == 'POST':
        return _process_baja_equipment_form(request, equipo)
    else:
        form = BajaEquipoForm()

    context = {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Dar de Baja Equipo: {equipo.codigo_interno}'
    }

    return render(request, 'core/dar_baja_equipo.html', context)


@access_check
@login_required
@trial_check
@require_POST
@monitor_view
def inactivar_equipo(request, equipo_pk):
    """
    Inactiva un equipo temporalmente
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos
    if not request.user.is_superuser:
        if not request.user.empresa or equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permisos para inactivar este equipo.')
            return redirect('core:home')

    try:
        equipo.estado = 'Inactivo'
        equipo.save()
        messages.success(request, f'Equipo {equipo.codigo_interno} inactivado exitosamente.')
    except Exception as e:
        logger.error(f"Error inactivando equipo {equipo.codigo_interno}: {e}")
        messages.error(request, f'Error al inactivar equipo: {str(e)}')

    return redirect('core:detalle_equipo', pk=equipo.pk)


@access_check
@login_required
@trial_check
@require_POST
@monitor_view
def activar_equipo(request, equipo_pk):
    """
    Activa un equipo inactivo
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos
    if not request.user.is_superuser:
        if not request.user.empresa or equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permisos para activar este equipo.')
            return redirect('core:home')

    try:
        # Si el equipo estaba dado de baja, eliminar el registro de baja
        if equipo.estado == 'De Baja':
            from core.models import BajaEquipo
            try:
                baja_registro = BajaEquipo.objects.get(equipo=equipo)
                baja_registro.delete()  # Esto activará el equipo a través de señal post_delete
                messages.success(request, f'Equipo {equipo.codigo_interno} activado exitosamente y registro de baja eliminado.')
                logger.info(f"Equipo reactivado desde baja ID: {equipo.pk} por usuario {request.user.username}")
            except BajaEquipo.DoesNotExist:
                # No había registro de baja, solo cambiar estado
                equipo.estado = 'Activo'
                equipo.save()
                messages.warning(request, f'Equipo {equipo.codigo_interno} activado. No se encontró registro de baja asociado.')
        else:
            # Equipo inactivo o en otro estado, solo cambiar estado
            equipo.estado = 'Activo'
            equipo.save()
            messages.success(request, f'Equipo {equipo.codigo_interno} activado exitosamente.')
    except Exception as e:
        logger.error(f"Error activando equipo {equipo.codigo_interno}: {e}")
        messages.error(request, f'Error al activar equipo: {str(e)}')

    return redirect('core:detalle_equipo', pk=equipo.pk)


# ============================================================================
# FUNCIONES AUXILIARES PRIVADAS
# ============================================================================

def _get_user_empresa(user):
    """Obtiene la empresa del usuario si no es superusuario"""
    if user.is_authenticated and not user.is_superuser:
        return user.empresa
    return None


def _check_equipment_limit(empresa):
    """Verifica si se ha alcanzado el límite de equipos"""
    if not empresa:
        return False

    limite_equipos = empresa.get_limite_equipos()
    if limite_equipos in [None, float('inf')] or limite_equipos <= 0:
        return False

    equipos_actuales = Equipo.objects.filter(empresa=empresa).count()
    return equipos_actuales >= limite_equipos


def _process_add_equipment_form(request, empresa_actual, limite_alcanzado):
    """Procesa el formulario de añadir equipo"""
    form = EquipoForm(request.POST, request.FILES, request=request)

    if form.is_valid():
        try:
            equipo = form.save(commit=False)

            # Validar límite de equipos
            try:
                StorageLimitValidator.validate_equipment_limit(equipo.empresa)
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'core/añadir_equipo.html', {
                    'form': form,
                    'titulo_pagina': 'Añadir Nuevo Equipo',
                    'limite_alcanzado': True,
                })

            # Validar y procesar archivos
            if not _validate_and_process_files(request, equipo):
                return render(request, 'core/añadir_equipo.html', {
                    'form': form,
                    'titulo_pagina': 'Añadir Nuevo Equipo',
                    'limite_alcanzado': limite_alcanzado,
                })

            equipo.save()
            messages.success(request, 'Equipo añadido exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)

        except Exception as e:
            logger.error(f"Error general al guardar equipo: {str(e)}")
            messages.error(request, f'Error al guardar el equipo: {str(e)}')
    else:
        _show_form_errors(request, form)

    return render(request, 'core/añadir_equipo.html', {
        'form': form,
        'titulo_pagina': 'Añadir Nuevo Equipo',
        'limite_alcanzado': limite_alcanzado,
    })


def _process_edit_equipment_form(request, equipo):
    """Procesa el formulario de editar equipo"""
    form = EquipoForm(request.POST, request.FILES, instance=equipo, request=request)

    if form.is_valid():
        try:
            # Validar y procesar archivos si hay nuevos
            has_new_files = any(field in request.FILES for field in
                              ['manual_pdf', 'archivo_compra_pdf', 'ficha_tecnica_pdf',
                               'otros_documentos_pdf', 'imagen_equipo'])

            if has_new_files:
                if not _validate_and_process_files(request, equipo, is_edit=True):
                    return render(request, 'core/editar_equipo.html', {
                        'form': form,
                        'equipo': equipo,
                        'titulo_pagina': f'Editar Equipo: {equipo.codigo_interno}'
                    })

            form.save()
            messages.success(request, f'Equipo {equipo.codigo_interno} actualizado exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)

        except Exception as e:
            logger.error(f"Error actualizando equipo {equipo.codigo_interno}: {str(e)}")
            messages.error(request, f'Error al actualizar equipo: {str(e)}')
    else:
        _show_form_errors(request, form)

    return render(request, 'core/editar_equipo.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Editar Equipo: {equipo.codigo_interno}'
    })


def _process_baja_equipment_form(request, equipo):
    """Procesa el formulario de dar de baja equipo"""
    form = BajaEquipoForm(request.POST)

    if form.is_valid():
        try:
            baja = form.save(commit=False)
            baja.equipo = equipo
            baja.usuario_baja = request.user
            baja.save()

            # Actualizar estado del equipo
            equipo.estado = 'De Baja'
            equipo.save()

            messages.success(request, f'Equipo {equipo.codigo_interno} dado de baja exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)

        except Exception as e:
            logger.error(f"Error dando de baja equipo {equipo.codigo_interno}: {str(e)}")
            messages.error(request, f'Error al dar de baja el equipo: {str(e)}')
    else:
        _show_form_errors(request, form)

    return render(request, 'core/dar_baja_equipo.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Dar de Baja Equipo: {equipo.codigo_interno}'
    })


def _validate_and_process_files(request, equipo, is_edit=False):
    """Valida y procesa archivos subidos"""
    try:
        # Calcular tamaño total de archivos nuevos
        total_file_size = 0
        archivos_campos = ['manual_pdf', 'archivo_compra_pdf', 'ficha_tecnica_pdf',
                          'otros_documentos_pdf', 'imagen_equipo']

        for campo in archivos_campos:
            if campo in request.FILES:
                archivo = request.FILES[campo]
                total_file_size += archivo.size

        # Validar límite de almacenamiento solo si hay archivos nuevos
        if total_file_size > 0:
            try:
                StorageLimitValidator.validate_storage_limit(equipo.empresa, total_file_size)
            except ValidationError as e:
                messages.error(request, str(e))
                return False

        # Procesar archivos
        archivos_config = {
            'manual_pdf': 'pdfs',
            'archivo_compra_pdf': 'pdfs',
            'ficha_tecnica_pdf': 'pdfs',
            'otros_documentos_pdf': 'pdfs',
            'imagen_equipo': 'imagenes_equipos',
        }

        for campo, carpeta_destino in archivos_config.items():
            if campo in request.FILES:
                archivo = request.FILES[campo]
                nombre_archivo = sanitize_filename(archivo.name)
                ruta_final = f"{carpeta_destino}/{nombre_archivo}"

                # Eliminar archivo anterior si existe y es edición
                if is_edit:
                    archivo_anterior = getattr(equipo, campo, None)
                    if archivo_anterior and default_storage.exists(archivo_anterior.name):
                        try:
                            default_storage.delete(archivo_anterior.name)
                        except Exception as e:
                            logger.warning(f"No se pudo eliminar archivo anterior {archivo_anterior.name}: {e}")

                # Guardar nuevo archivo
                default_storage.save(ruta_final, archivo)
                setattr(equipo, campo, ruta_final)

        return True

    except Exception as e:
        logger.error(f"Error procesando archivos: {str(e)}")
        messages.error(request, f'Error procesando archivos: {str(e)}')
        return False


def _show_form_errors(request, form):
    """Muestra errores del formulario al usuario"""
    logger.warning(f"Errores del formulario: {form.errors}")
    logger.warning(f"Errores no de campo: {form.non_field_errors()}")

    for field, errors in form.errors.items():
        for error in errors:
            messages.error(request, f'{field}: {error}')

    if form.non_field_errors():
        for error in form.non_field_errors():
            messages.error(request, str(error))


def _calculate_equipment_metrics(equipo):
    """Calcula métricas del equipo"""
    return {
        'total_calibraciones': equipo.calibraciones.count(),
        'total_mantenimientos': equipo.mantenimientos.count(),
        'total_comprobaciones': equipo.comprobaciones.count(),
        'ultima_calibracion': equipo.calibraciones.first(),
        'ultimo_mantenimiento': equipo.mantenimientos.first(),
        'ultima_comprobacion': equipo.comprobaciones.first(),
    }


def _get_equipment_file_urls(equipo):
    """Obtiene URLs seguras para archivos del equipo y sus actividades"""
    file_urls = {
        # URLs de archivos del equipo
        'manual_url': get_secure_file_url(equipo.manual_pdf),
        'archivo_compra_url': get_secure_file_url(equipo.archivo_compra_pdf),
        'ficha_tecnica_url': get_secure_file_url(equipo.ficha_tecnica_pdf),
        'otros_documentos_url': get_secure_file_url(equipo.otros_documentos_pdf),
        'imagen_url': get_secure_file_url(equipo.imagen_equipo),
    }

    # Nota: URLs de actividades se sirven ahora a través de vistas dedicadas para mayor seguridad
    return file_urls


@login_required
@monitor_view
def ver_archivo_mantenimiento(request, mantenimiento_pk):
    """Vista para servir archivos de mantenimiento de forma segura"""
    from django.http import HttpResponse, Http404
    from django.core.files.storage import default_storage
    import mimetypes

    mantenimiento = get_object_or_404(Mantenimiento, pk=mantenimiento_pk)

    # Verificar permisos
    if not request.user.is_superuser:
        if not request.user.empresa or mantenimiento.equipo.empresa != request.user.empresa:
            raise Http404("Archivo no encontrado")

    if not mantenimiento.documento_mantenimiento:
        raise Http404("Archivo no encontrado")

    try:
        # Usar la función segura para obtener URL
        file_url = get_secure_file_url(mantenimiento.documento_mantenimiento)
        if file_url:
            # Si es desarrollo (FileSystemStorage), servir el archivo directamente
            if not hasattr(default_storage, 'bucket'):  # FileSystemStorage
                file_path = mantenimiento.documento_mantenimiento.path
                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()

                    content_type, _ = mimetypes.guess_type(file_path)
                    if not content_type:
                        content_type = 'application/pdf'

                    response = HttpResponse(file_data, content_type=content_type)
                    response['Content-Disposition'] = f'inline; filename="{mantenimiento.documento_mantenimiento.name}"'
                    return response
                except FileNotFoundError:
                    raise Http404("Archivo no encontrado")
            else:  # S3Storage - redirigir a URL segura
                from django.shortcuts import redirect
                return redirect(file_url)
        else:
            raise Http404("Error al generar URL del archivo")

    except Exception as e:
        logger.error(f"Error sirviendo archivo de mantenimiento {mantenimiento_pk}: {e}")
        raise Http404("Error al acceder al archivo")


def calcular_proximas_fechas_personalizadas(equipo):
    """
    Aplica la lógica personalizada para calcular próximas fechas de actividades.

    Lógica CORRECTA por tipo de actividad:
    1. Su propia fecha anterior (fecha_ultimo_X para actividad X)
    2. fecha_ultima_calibracion (como segunda opción)
    3. fecha_adquisicion (como tercera opción)
    4. fecha_registro (como último recurso)
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta

    def obtener_fecha_base_para_actividad(fecha_propia, equipo):
        """
        Obtiene la fecha base siguiendo la jerarquía correcta para cada actividad.
        """
        if fecha_propia:
            return fecha_propia
        elif equipo.fecha_ultima_calibracion:
            return equipo.fecha_ultima_calibracion
        elif equipo.fecha_adquisicion:
            return equipo.fecha_adquisicion
        else:
            return equipo.fecha_registro.date()

    # CALIBRACIÓN: Usar su propia fecha como primera opción
    if equipo.frecuencia_calibracion_meses and equipo.frecuencia_calibracion_meses > 0:
        fecha_base_calibracion = obtener_fecha_base_para_actividad(
            equipo.fecha_ultima_calibracion, equipo
        )
        equipo.proxima_calibracion = fecha_base_calibracion + relativedelta(
            months=int(equipo.frecuencia_calibracion_meses)
        )

    # MANTENIMIENTO: Usar jerarquía específica para mantenimiento
    if equipo.frecuencia_mantenimiento_meses and equipo.frecuencia_mantenimiento_meses > 0:
        fecha_base_mantenimiento = obtener_fecha_base_para_actividad(
            equipo.fecha_ultimo_mantenimiento, equipo
        )
        equipo.proximo_mantenimiento = fecha_base_mantenimiento + relativedelta(
            months=int(equipo.frecuencia_mantenimiento_meses)
        )

    # COMPROBACIÓN: Usar jerarquía específica para comprobación
    if equipo.frecuencia_comprobacion_meses and equipo.frecuencia_comprobacion_meses > 0:
        fecha_base_comprobacion = obtener_fecha_base_para_actividad(
            equipo.fecha_ultima_comprobacion, equipo
        )
        equipo.proxima_comprobacion = fecha_base_comprobacion + relativedelta(
            months=int(equipo.frecuencia_comprobacion_meses)
        )

    # Guardar solo los campos de fechas calculadas
    equipo.save(update_fields=[
        'proxima_calibracion',
        'proximo_mantenimiento',
        'proxima_comprobacion'
    ])


def _get_next_activities(equipo):
    """Obtiene próximas actividades del equipo"""
    today = date.today()

    return {
        'calibracion_vencida': equipo.proxima_calibracion and equipo.proxima_calibracion < today,
        'mantenimiento_vencido': equipo.proximo_mantenimiento and equipo.proximo_mantenimiento < today,
        'comprobacion_vencida': equipo.proxima_comprobacion and equipo.proxima_comprobacion < today,
    }


@access_check
@login_required
@trial_check
@monitor_view
def equipos_eliminar_masivo(request):
    """
    Vista para eliminar múltiples equipos a la vez.
    Solo ADMINISTRADOR, GERENCIA y SuperUsuario pueden eliminar.
    NUEVO 2025-11-19: Eliminación masiva
    """
    # Verificar permisos
    if not request.user.puede_eliminar_equipos:
        messages.error(request, 'No tienes permisos para eliminar equipos.')
        return redirect('core:home')

    if request.method == 'POST':
        # Obtener IDs de equipos a eliminar
        equipos_ids = request.POST.getlist('equipos_ids[]')

        if not equipos_ids:
            messages.error(request, 'No se seleccionaron equipos para eliminar.')
            return redirect('core:home')

        # Verificar que todos los equipos pertenecen a la empresa del usuario
        empresa = request.user.empresa

        if request.user.is_superuser:
            equipos = Equipo.objects.filter(id__in=equipos_ids)
        else:
            equipos = Equipo.objects.filter(
                id__in=equipos_ids,
                empresa=empresa
            )

        if not request.user.is_superuser and equipos.count() != len(equipos_ids):
            messages.error(request, 'Algunos equipos no pertenecen a tu empresa.')
            return redirect('core:home')

        # Eliminar equipos
        try:
            cantidad = equipos.count()
            equipos.delete()
            messages.success(request, f'{cantidad} equipo(s) eliminado(s) correctamente.')
        except Exception as e:
            logger.error(f"Error en eliminación masiva: {e}")
            messages.error(request, f'Error al eliminar equipos: {str(e)}')

        return redirect('core:home')

    # Vista GET - Confirmación
    equipos_ids = request.GET.getlist('ids')
    empresa = request.user.empresa

    if request.user.is_superuser:
        equipos = Equipo.objects.filter(id__in=equipos_ids)
    else:
        equipos = Equipo.objects.filter(
            id__in=equipos_ids,
            empresa=empresa
        )

    return render(request, 'core/equipos_eliminar_masivo.html', {
        'equipos': equipos,
        'titulo_pagina': 'Eliminar Equipos Masivamente'
    })