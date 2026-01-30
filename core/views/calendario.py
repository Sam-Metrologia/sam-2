# core/views/calendario.py
# Vista de Calendario de Actividades

import logging
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from ..models import Equipo, Calibracion, Mantenimiento, Comprobacion
from ..monitoring import monitor_view
from .base import access_check

logger = logging.getLogger(__name__)

# ============================================================================
# Colores por tipo de actividad
# ============================================================================
COLORES = {
    'calibracion':   {'programado': '#3b82f6', 'realizado': '#93c5fd'},
    'mantenimiento': {'programado': '#10b981', 'realizado': '#6ee7b7'},
    'comprobacion':  {'programado': '#f59e0b', 'realizado': '#fcd34d'},
}

TIPO_LABELS = {
    'calibracion': 'Calibración',
    'mantenimiento': 'Mantenimiento',
    'comprobacion': 'Comprobación',
}


def _build_event(title, start_date, color, extra=None):
    """Construye un dict de evento en formato FullCalendar."""
    event = {
        'title': title,
        'start': start_date.isoformat(),
        'color': color,
        'allDay': True,
    }
    if extra:
        event['extendedProps'] = extra
    return event


def _get_equipos_qs(user):
    """Retorna el queryset de equipos filtrado por empresa, excluyendo De Baja e Inactivo."""
    qs = Equipo.objects.exclude(estado__in=['De Baja', 'Inactivo'])
    if not user.is_superuser:
        qs = qs.filter(empresa=user.empresa)
    return qs


# ============================================================================
# Vista principal del calendario
# ============================================================================
@monitor_view
@access_check
@login_required
def calendario_actividades(request):
    """Renderiza la página del calendario de actividades."""
    equipos_qs = _get_equipos_qs(request.user)
    responsables = (
        equipos_qs
        .exclude(responsable__isnull=True)
        .exclude(responsable='')
        .values_list('responsable', flat=True)
        .distinct()
        .order_by('responsable')
    )
    return render(request, 'core/calendario.html', {
        'responsables': list(responsables),
        'titulo_pagina': 'Calendario de Actividades',
    })


# ============================================================================
# API JSON para FullCalendar
# ============================================================================
@monitor_view
@access_check
@login_required
def calendario_eventos_api(request):
    """API que retorna eventos en formato FullCalendar JSON."""
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    tipo = request.GET.get('tipo', '')
    responsable = request.GET.get('responsable', '')

    # Parsear fechas
    try:
        # FullCalendar envía ISO dates como "2025-01-01" o "2025-01-01T00:00:00"
        start_date = date.fromisoformat(start[:10]) if start else date.today().replace(day=1)
    except (ValueError, IndexError):
        start_date = date.today().replace(day=1)

    try:
        end_date = date.fromisoformat(end[:10]) if end else start_date + timedelta(days=42)
    except (ValueError, IndexError):
        end_date = start_date + timedelta(days=42)

    equipos_qs = _get_equipos_qs(request.user)
    if responsable:
        equipos_qs = equipos_qs.filter(responsable=responsable)

    eventos = []
    tipos_a_mostrar = [tipo] if tipo else ['calibracion', 'mantenimiento', 'comprobacion']

    # --- Eventos programados (fechas futuras del modelo Equipo) ---
    for equipo in equipos_qs.iterator():
        equipo_props = {
            'equipo_id': equipo.pk,
            'equipo_nombre': equipo.nombre,
            'equipo_codigo': equipo.codigo_interno,
            'responsable': equipo.responsable or '',
        }

        if 'calibracion' in tipos_a_mostrar and equipo.proxima_calibracion:
            if start_date <= equipo.proxima_calibracion <= end_date:
                eventos.append(_build_event(
                    title=f'[Cal] {equipo.nombre}',
                    start_date=equipo.proxima_calibracion,
                    color=COLORES['calibracion']['programado'],
                    extra={**equipo_props, 'tipo': 'calibracion', 'estado': 'programado'},
                ))

        if 'mantenimiento' in tipos_a_mostrar and equipo.proximo_mantenimiento:
            if start_date <= equipo.proximo_mantenimiento <= end_date:
                eventos.append(_build_event(
                    title=f'[Mant] {equipo.nombre}',
                    start_date=equipo.proximo_mantenimiento,
                    color=COLORES['mantenimiento']['programado'],
                    extra={**equipo_props, 'tipo': 'mantenimiento', 'estado': 'programado'},
                ))

        if 'comprobacion' in tipos_a_mostrar and equipo.proxima_comprobacion:
            if start_date <= equipo.proxima_comprobacion <= end_date:
                eventos.append(_build_event(
                    title=f'[Comp] {equipo.nombre}',
                    start_date=equipo.proxima_comprobacion,
                    color=COLORES['comprobacion']['programado'],
                    extra={**equipo_props, 'tipo': 'comprobacion', 'estado': 'programado'},
                ))

    # --- Eventos realizados (registros históricos) ---
    equipo_ids = equipos_qs.values_list('pk', flat=True)

    if 'calibracion' in tipos_a_mostrar:
        calibraciones = Calibracion.objects.filter(
            equipo_id__in=equipo_ids,
            fecha_calibracion__range=(start_date, end_date),
        ).select_related('equipo')
        for cal in calibraciones:
            eventos.append(_build_event(
                title=f'[Cal] {cal.equipo.nombre}',
                start_date=cal.fecha_calibracion,
                color=COLORES['calibracion']['realizado'],
                extra={
                    'equipo_id': cal.equipo.pk,
                    'equipo_nombre': cal.equipo.nombre,
                    'equipo_codigo': cal.equipo.codigo_interno,
                    'responsable': cal.equipo.responsable or '',
                    'tipo': 'calibracion',
                    'estado': 'realizado',
                    'resultado': getattr(cal, 'resultado', ''),
                    'certificado': getattr(cal, 'numero_certificado', ''),
                },
            ))

    if 'mantenimiento' in tipos_a_mostrar:
        mantenimientos = Mantenimiento.objects.filter(
            equipo_id__in=equipo_ids,
            fecha_mantenimiento__range=(start_date, end_date),
        ).select_related('equipo')
        for mant in mantenimientos:
            eventos.append(_build_event(
                title=f'[Mant] {mant.equipo.nombre}',
                start_date=mant.fecha_mantenimiento,
                color=COLORES['mantenimiento']['realizado'],
                extra={
                    'equipo_id': mant.equipo.pk,
                    'equipo_nombre': mant.equipo.nombre,
                    'equipo_codigo': mant.equipo.codigo_interno,
                    'responsable': mant.equipo.responsable or '',
                    'tipo': 'mantenimiento',
                    'estado': 'realizado',
                    'tipo_mantenimiento': getattr(mant, 'tipo_mantenimiento', ''),
                    'descripcion': getattr(mant, 'descripcion', ''),
                },
            ))

    if 'comprobacion' in tipos_a_mostrar:
        comprobaciones = Comprobacion.objects.filter(
            equipo_id__in=equipo_ids,
            fecha_comprobacion__range=(start_date, end_date),
        ).select_related('equipo')
        for comp in comprobaciones:
            eventos.append(_build_event(
                title=f'[Comp] {comp.equipo.nombre}',
                start_date=comp.fecha_comprobacion,
                color=COLORES['comprobacion']['realizado'],
                extra={
                    'equipo_id': comp.equipo.pk,
                    'equipo_nombre': comp.equipo.nombre,
                    'equipo_codigo': comp.equipo.codigo_interno,
                    'responsable': comp.equipo.responsable or '',
                    'tipo': 'comprobacion',
                    'estado': 'realizado',
                    'resultado': getattr(comp, 'resultado', ''),
                },
            ))

    return JsonResponse(eventos, safe=False)


# ============================================================================
# Exportar iCal (.ics)
# ============================================================================
@monitor_view
@access_check
@login_required
def calendario_exportar_ical(request):
    """Exporta actividades programadas como archivo .ics."""
    tipo = request.GET.get('tipo', '')
    responsable = request.GET.get('responsable', '')

    equipos_qs = _get_equipos_qs(request.user)
    if responsable:
        equipos_qs = equipos_qs.filter(responsable=responsable)

    tipos_a_mostrar = [tipo] if tipo else ['calibracion', 'mantenimiento', 'comprobacion']

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//SAM Metrologia//Calendario de Actividades//ES',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
    ]

    for equipo in equipos_qs.iterator():
        actividades = []
        if 'calibracion' in tipos_a_mostrar and equipo.proxima_calibracion:
            actividades.append(('Calibración', equipo.proxima_calibracion))
        if 'mantenimiento' in tipos_a_mostrar and equipo.proximo_mantenimiento:
            actividades.append(('Mantenimiento', equipo.proximo_mantenimiento))
        if 'comprobacion' in tipos_a_mostrar and equipo.proxima_comprobacion:
            actividades.append(('Comprobación', equipo.proxima_comprobacion))

        for act_tipo, act_fecha in actividades:
            uid = f'{act_tipo.lower()}-{equipo.pk}-{act_fecha.isoformat()}@sam-metrologia'
            fecha_str = act_fecha.strftime('%Y%m%d')
            lines.extend([
                'BEGIN:VEVENT',
                f'UID:{uid}',
                f'DTSTART;VALUE=DATE:{fecha_str}',
                f'DTEND;VALUE=DATE:{fecha_str}',
                f'SUMMARY:{act_tipo} - {equipo.nombre}',
                f'DESCRIPTION:Equipo: {equipo.nombre} ({equipo.codigo_interno})\\n'
                f'Responsable: {equipo.responsable or "N/A"}',
                'END:VEVENT',
            ])

    lines.append('END:VCALENDAR')

    content = '\r\n'.join(lines)
    response = HttpResponse(content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="calendario_actividades.ics"'
    return response
