# core/views/prestamos.py
"""
Vistas para el sistema de préstamos de equipos.
Incluye gestión de préstamos, devoluciones y dashboard de seguimiento.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from django.http import HttpResponseForbidden

from ..models import PrestamoEquipo, AgrupacionPrestamo, Equipo
from ..forms import PrestamoEquipoForm, DevolucionEquipoForm
from ..constants import (
    ESTADO_ACTIVO, ESTADO_DE_BAJA,
    PRESTAMO_ACTIVO, PRESTAMO_DEVUELTO, PRESTAMO_VENCIDO, PRESTAMO_CANCELADO,
)


@login_required
@permission_required('core.can_view_prestamo', raise_exception=True)
def listar_prestamos(request):
    """
    Lista todos los préstamos de la empresa del usuario.
    Incluye filtros por estado y búsqueda.
    """
    # Base queryset filtrado por empresa - EXCLUYE DEVUELTOS
    # Los devueltos ya están en el historial del equipo
    prestamos = PrestamoEquipo.objects.select_related(
        'equipo', 'empresa', 'prestado_por', 'recibido_por'
    ).filter(empresa=request.user.empresa).exclude(estado_prestamo=PRESTAMO_DEVUELTO)

    # Filtro por estado
    estado_filter = request.GET.get('estado')
    if estado_filter:
        prestamos = prestamos.filter(estado_prestamo=estado_filter)

    # Búsqueda
    search_query = request.GET.get('search')
    if search_query:
        prestamos = prestamos.filter(
            Q(equipo__codigo_interno__icontains=search_query) |
            Q(equipo__nombre__icontains=search_query) |
            Q(nombre_prestatario__icontains=search_query) |
            Q(cedula_prestatario__icontains=search_query)
        )

    # Ordenar por fecha más reciente
    prestamos = prestamos.order_by('-fecha_prestamo')

    # Paginación
    paginator = Paginator(prestamos, 25)
    page = request.GET.get('page')
    prestamos_page = paginator.get_page(page)

    # Estadísticas
    total_prestamos = prestamos.count()
    prestamos_activos = prestamos.filter(estado_prestamo=PRESTAMO_ACTIVO).count()
    prestamos_vencidos = prestamos.filter(
        estado_prestamo=PRESTAMO_ACTIVO,
        fecha_devolucion_programada__lt=timezone.now().date()
    ).count()

    context = {
        'prestamos': prestamos_page,
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos,
        'prestamos_vencidos': prestamos_vencidos,
        'estado_filter': estado_filter,
        'search_query': search_query,
        'titulo_pagina': 'Gestión de Préstamos de Equipos',
    }
    return render(request, 'core/prestamos/listar.html', context)


@login_required
@permission_required('core.can_add_prestamo', raise_exception=True)
def crear_prestamo(request):
    """
    Crea un nuevo préstamo de equipo.
    Soporta préstamo de múltiples equipos simultáneamente.
    """
    # Verificar que el usuario tenga empresa asignada
    if not request.user.empresa:
        messages.error(request, 'Tu usuario no tiene una empresa asignada. Contacta al administrador.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = PrestamoEquipoForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            # Obtener equipos seleccionados
            equipos_seleccionados = form.cleaned_data.get('equipos', [])
            equipo_individual = form.cleaned_data.get('equipo')

            # Determinar si es préstamo múltiple o individual
            if equipos_seleccionados and len(equipos_seleccionados) > 0:
                # PRÉSTAMO MÚLTIPLE - Crear agrupación
                agrupacion = AgrupacionPrestamo.objects.create(
                    nombre=f"Préstamo múltiple - {form.cleaned_data.get('nombre_prestatario')}",
                    prestatario_nombre=form.cleaned_data.get('nombre_prestatario'),
                    empresa=request.user.empresa
                )

                # Crear préstamos individuales para cada equipo
                # CADA EQUIPO TIENE SU PROPIA VERIFICACIÓN CON MEDICIONES ESPECÍFICAS
                prestamos_creados = []
                for equipo in equipos_seleccionados:
                    # Obtener verificación de salida específica para este equipo
                    verificacion_salida_data = form.get_verificacion_salida_por_equipo(
                        request.user,
                        equipo.id,
                        request.POST
                    )

                    prestamo = PrestamoEquipo(
                        equipo=equipo,
                        empresa=request.user.empresa,
                        agrupacion=agrupacion,
                        nombre_prestatario=form.cleaned_data.get('nombre_prestatario'),
                        cedula_prestatario=form.cleaned_data.get('cedula_prestatario', ''),
                        cargo_prestatario=form.cleaned_data.get('cargo_prestatario', ''),
                        email_prestatario=form.cleaned_data.get('email_prestatario', ''),
                        telefono_prestatario=form.cleaned_data.get('telefono_prestatario', ''),
                        fecha_devolucion_programada=form.cleaned_data.get('fecha_devolucion_programada'),
                        observaciones_prestamo=form.cleaned_data.get('observaciones_prestamo', ''),
                        prestado_por=request.user,
                        estado_prestamo=PRESTAMO_ACTIVO,
                        verificacion_salida=verificacion_salida_data
                    )
                    prestamo.save()
                    prestamos_creados.append(prestamo)

                messages.success(
                    request,
                    f'Se crearon {len(prestamos_creados)} préstamos exitosamente para {agrupacion.prestatario_nombre}. '
                    f'Equipos: {", ".join([p.equipo.codigo_interno for p in prestamos_creados])}'
                )
                return redirect('core:listar_prestamos')

            elif equipo_individual:
                # PRÉSTAMO INDIVIDUAL - Usar el flujo original
                prestamo = form.save(commit=False)
                prestamo.empresa = request.user.empresa
                prestamo.prestado_por = request.user

                # Verificación funcional de salida
                prestamo.verificacion_salida = form.get_verificacion_salida_data(request.user)

                prestamo.save()

                messages.success(
                    request,
                    f'Préstamo de {prestamo.equipo.codigo_interno} creado exitosamente. '
                    f'Prestatario: {prestamo.nombre_prestatario}'
                )
                return redirect('core:detalle_prestamo', pk=prestamo.pk)
            else:
                messages.error(request, 'Debes seleccionar al menos un equipo.')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = PrestamoEquipoForm(empresa=request.user.empresa)

    context = {
        'form': form,
        'titulo_pagina': 'Nuevo Préstamo de Equipo',
    }
    return render(request, 'core/prestamos/crear.html', context)


@login_required
@permission_required('core.can_view_prestamo', raise_exception=True)
def detalle_prestamo(request, pk):
    """
    Muestra el detalle completo de un préstamo.
    """
    prestamo = get_object_or_404(
        PrestamoEquipo.objects.select_related(
            'equipo', 'empresa', 'prestado_por', 'recibido_por', 'agrupacion'
        ),
        pk=pk
    )

    # Verificar que el usuario pertenezca a la misma empresa
    if not request.user.is_superuser and prestamo.empresa != request.user.empresa:
        return HttpResponseForbidden("No tienes permiso para ver este préstamo.")

    # Calcular información adicional
    dias_prestado = prestamo.dias_en_prestamo
    esta_vencido = prestamo.esta_vencido

    # Otros préstamos del mismo prestatario (si existen)
    otros_prestamos = PrestamoEquipo.objects.filter(
        empresa=request.user.empresa,
        nombre_prestatario=prestamo.nombre_prestatario,
        estado_prestamo=PRESTAMO_ACTIVO
    ).exclude(pk=prestamo.pk).select_related('equipo')[:5]

    context = {
        'prestamo': prestamo,
        'dias_prestado': dias_prestado,
        'esta_vencido': esta_vencido,
        'otros_prestamos': otros_prestamos,
        'titulo_pagina': f'Préstamo {prestamo.equipo.codigo_interno}',
    }
    return render(request, 'core/prestamos/detalle.html', context)


@login_required
@permission_required('core.can_change_prestamo', raise_exception=True)
def devolver_equipo(request, pk):
    """
    Registra la devolución de un equipo prestado.
    """
    prestamo = get_object_or_404(
        PrestamoEquipo.objects.select_related('equipo', 'empresa'),
        pk=pk
    )

    # Verificar que el usuario pertenezca a la misma empresa
    if not request.user.is_superuser and prestamo.empresa != request.user.empresa:
        return HttpResponseForbidden("No tienes permiso para modificar este préstamo.")

    # Verificar que el préstamo esté activo
    if prestamo.estado_prestamo != 'ACTIVO':
        messages.warning(
            request,
            f'Este préstamo ya fue devuelto el {prestamo.fecha_devolucion_real.strftime("%d/%m/%Y")}.'
        )
        return redirect('core:detalle_prestamo', pk=prestamo.pk)

    if request.method == 'POST':
        form = DevolucionEquipoForm(request.POST, request.FILES)
        if form.is_valid():
            # Preparar datos de verificación de entrada
            verificacion_datos = form.to_verificacion_json()

            # Registrar devolución
            prestamo.devolver(
                user=request.user,
                verificacion_entrada_datos=verificacion_datos,
                observaciones=form.cleaned_data.get('observaciones_devolucion', '')
            )

            # Guardar documento si se cargó
            if form.cleaned_data.get('documento_devolucion'):
                prestamo.documento_devolucion = form.cleaned_data['documento_devolucion']
                prestamo.save()

            messages.success(
                request,
                f'Equipo {prestamo.equipo.codigo_interno} devuelto exitosamente. '
                f'Estado: {verificacion_datos["verificacion_funcional"]}'
            )
            return redirect('core:detalle_prestamo', pk=prestamo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = DevolucionEquipoForm()

    context = {
        'prestamo': prestamo,
        'form': form,
        'titulo_pagina': f'Devolver Equipo {prestamo.equipo.codigo_interno}',
    }
    return render(request, 'core/prestamos/devolver.html', context)


@login_required
@permission_required('core.can_view_prestamo', raise_exception=True)
def dashboard_prestamos(request):
    """
    Dashboard con vista colapsable por responsable.
    Muestra todos los préstamos activos agrupados por prestatario.
    """
    # Préstamos activos de la empresa
    prestamos_activos = PrestamoEquipo.objects.filter(
        empresa=request.user.empresa,
        estado_prestamo=PRESTAMO_ACTIVO
    ).select_related('equipo').order_by('nombre_prestatario', '-fecha_prestamo')

    # Agrupar por prestatario
    prestatarios = {}
    for prestamo in prestamos_activos:
        nombre = prestamo.nombre_prestatario
        if nombre not in prestatarios:
            prestatarios[nombre] = {
                'nombre': nombre,
                'cedula': prestamo.cedula_prestatario,
                'cargo': prestamo.cargo_prestatario,
                'email': prestamo.email_prestatario,
                'telefono': prestamo.telefono_prestatario,
                'prestamos': [],
                'cantidad_equipos': 0,
                'equipos_vencidos': 0
            }
        prestatarios[nombre]['prestamos'].append(prestamo)
        prestatarios[nombre]['cantidad_equipos'] += 1
        if prestamo.esta_vencido:
            prestatarios[nombre]['equipos_vencidos'] += 1

    # Estadísticas generales
    total_prestamos_activos = prestamos_activos.count()
    total_prestatarios = len(prestatarios)
    prestamos_vencidos = sum(1 for p in prestamos_activos if p.esta_vencido)

    # Próximas devoluciones (en los próximos 7 días)
    fecha_limite = timezone.now().date() + timezone.timedelta(days=7)
    devoluciones_proximas = prestamos_activos.filter(
        fecha_devolucion_programada__lte=fecha_limite,
        fecha_devolucion_programada__gte=timezone.now().date()
    ).count()

    # Estadísticas de equipos disponibles/prestados
    total_equipos = Equipo.objects.filter(
        empresa=request.user.empresa,
        estado=ESTADO_ACTIVO  # Solo contar equipos activos
    ).count()
    equipos_prestados = prestamos_activos.values('equipo').distinct().count()
    equipos_disponibles = total_equipos - equipos_prestados

    context = {
        'prestatarios': prestatarios.values(),
        'total_prestamos_activos': total_prestamos_activos,
        'total_prestatarios': total_prestatarios,
        'prestamos_vencidos': prestamos_vencidos,
        'devoluciones_proximas': devoluciones_proximas,
        'total_equipos': total_equipos,
        'equipos_prestados': equipos_prestados,
        'equipos_disponibles': equipos_disponibles,
        'titulo_pagina': 'Dashboard de Préstamos',
    }
    return render(request, 'core/prestamos/dashboard.html', context)


@login_required
@permission_required('core.can_view_prestamo', raise_exception=True)
def historial_equipo(request, equipo_id):
    """
    Muestra el historial completo de préstamos de un equipo específico.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_id)

    # Verificar que el usuario pertenezca a la misma empresa
    if not request.user.is_superuser and equipo.empresa != request.user.empresa:
        return HttpResponseForbidden("No tienes permiso para ver este equipo.")

    # Obtener todos los préstamos del equipo (activos y devueltos)
    prestamos = PrestamoEquipo.objects.filter(
        equipo=equipo
    ).select_related('prestado_por', 'recibido_por').order_by('-fecha_prestamo')

    # Estadísticas del equipo
    total_prestamos = prestamos.count()
    prestamos_activos = prestamos.filter(estado_prestamo=PRESTAMO_ACTIVO).count()
    prestamos_devueltos = prestamos.filter(estado_prestamo=PRESTAMO_DEVUELTO).count()

    # Agrupar por año
    from datetime import datetime
    prestamos_por_anio = {}
    for prestamo in prestamos:
        anio = prestamo.fecha_prestamo.year
        if anio not in prestamos_por_anio:
            prestamos_por_anio[anio] = []
        prestamos_por_anio[anio].append(prestamo)

    # Prestatarios únicos
    prestatarios_unicos = prestamos.values_list('nombre_prestatario', flat=True).distinct()

    context = {
        'equipo': equipo,
        'prestamos': prestamos,
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos,
        'prestamos_devueltos': prestamos_devueltos,
        'prestamos_por_anio': dict(sorted(prestamos_por_anio.items(), reverse=True)),
        'prestatarios_unicos': list(prestatarios_unicos),
        'titulo_pagina': f'Historial de Préstamos - {equipo.codigo_interno}',
    }
    return render(request, 'core/prestamos/historial.html', context)


@login_required
@permission_required('core.can_view_prestamo', raise_exception=True)
def equipos_disponibles(request):
    """
    Lista de equipos disponibles para préstamo (no están prestados actualmente).
    """
    # Obtener todos los equipos activos de la empresa
    equipos_activos = Equipo.objects.filter(
        empresa=request.user.empresa,
        estado=ESTADO_ACTIVO
    ).select_related('empresa').prefetch_related(
        'prestamos'
    ).order_by('codigo_interno')

    # Filtrar solo los que NO están prestados
    equipos_disponibles = [equipo for equipo in equipos_activos if not equipo.esta_prestado]

    context = {
        'equipos': equipos_disponibles,
        'total_equipos': len(equipos_disponibles),
        'titulo_pagina': 'Equipos Disponibles para Préstamo',
        'tipo': 'disponibles'
    }
    return render(request, 'core/prestamos/equipos_estado.html', context)


@login_required
@permission_required('core.can_view_prestamo', raise_exception=True)
def equipos_prestados(request):
    """
    Lista de equipos actualmente prestados con información del prestatario.
    """
    # Obtener préstamos activos de la empresa
    prestamos_activos = PrestamoEquipo.objects.filter(
        empresa=request.user.empresa,
        estado_prestamo=PRESTAMO_ACTIVO
    ).select_related('equipo', 'equipo__empresa').order_by('equipo__codigo_interno')

    # Crear lista de equipos con información del préstamo
    equipos_prestados = []
    for prestamo in prestamos_activos:
        equipos_prestados.append({
            'equipo': prestamo.equipo,
            'prestamo': prestamo,
            'prestatario': prestamo.nombre_prestatario,
            'cargo': prestamo.cargo_prestatario,
            'dias_prestado': prestamo.dias_en_prestamo,
            'vencido': prestamo.esta_vencido,
        })

    context = {
        'equipos_prestados': equipos_prestados,
        'total_equipos': len(equipos_prestados),
        'titulo_pagina': 'Equipos Actualmente en Préstamo',
        'tipo': 'prestados'
    }
    return render(request, 'core/prestamos/equipos_estado.html', context)
