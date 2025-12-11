"""
Vistas para Comprobación Metrológica
Permite registrar verificaciones intermedias de equipos con análisis de conformidad.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from weasyprint import HTML

from core.models import Comprobacion, Equipo

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """
    Convierte un valor a float de forma segura.
    Maneja cadenas vacías, None, y valores inválidos.

    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla (default: 0.0)

    Returns:
        float: Valor convertido o default
    """
    if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


@login_required
@require_http_methods(["GET", "POST"])
def comprobacion_metrologica_view(request, equipo_id):
    """
    Vista para crear/editar la comprobación metrológica con tabla de puntos de medición.
    """
    # Superusuarios pueden ver equipos de cualquier empresa
    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)
    comprobacion_id = request.GET.get('comprobacion_id')

    # Obtener comprobación existente si se proporciona ID
    comprobacion = None
    datos_existentes = None

    if comprobacion_id:
        comprobacion = get_object_or_404(
            Comprobacion,
            id=comprobacion_id,
            equipo=equipo
        )
        if hasattr(comprobacion, 'datos_comprobacion') and comprobacion.datos_comprobacion:
            datos_existentes = json.dumps(comprobacion.datos_comprobacion)

    # Obtener la última calibración para obtener datos de referencia
    ultima_calibracion = equipo.calibraciones.order_by('-fecha_calibracion').first()

    datos_calibracion = None
    unidad_equipo = 'mm'  # Valor por defecto

    if (ultima_calibracion and
        hasattr(ultima_calibracion, 'confirmacion_metrologica_datos') and
        ultima_calibracion.confirmacion_metrologica_datos):
        try:
            datos_calibracion = ultima_calibracion.confirmacion_metrologica_datos
            # Intentar obtener la unidad de la última calibración
            if 'unidad_equipo' in datos_calibracion:
                unidad_equipo = datos_calibracion['unidad_equipo']
        except:
            pass

    # Si no hay datos de calibración, intentar extraer del rango_medida
    if unidad_equipo == 'mm' and equipo.rango_medida:
        import re
        # Extraer unidad del rango (ej: "0-10mm" -> "mm")
        match = re.search(r'([a-zA-Zµ%]+)$', equipo.rango_medida)
        if match:
            unidad_equipo = match.group(1)

    # Obtener logo y datos de la empresa
    logo_empresa_url = None
    nombre_empresa = "Sin Empresa"
    formato_codigo = "SAM-COMP-001"
    formato_version = "01"

    if equipo.empresa:
        nombre_empresa = equipo.empresa.nombre
        if equipo.empresa.logo_empresa:
            try:
                logo_empresa_url = equipo.empresa.logo_empresa.url
            except:
                logo_empresa_url = None

        # Obtener formato de la empresa si existe
        if hasattr(equipo.empresa, 'formato_codigo') and equipo.empresa.formato_codigo:
            formato_codigo = equipo.empresa.formato_codigo
        if hasattr(equipo.empresa, 'formato_version') and equipo.empresa.formato_version:
            formato_version = equipo.empresa.formato_version

    context = {
        'equipo': equipo,
        'comprobacion': comprobacion,
        'comprobacion_id': comprobacion_id,
        'datos_existentes': datos_existentes,
        'datos_calibracion': json.dumps(datos_calibracion) if datos_calibracion else None,
        'unidad_equipo': unidad_equipo,
        'logo_empresa_url': logo_empresa_url,
        'nombre_empresa': nombre_empresa,
        'formato_codigo': formato_codigo,
        'formato_version': formato_version,
    }

    return render(request, 'core/comprobacion_metrologica.html', context)


@login_required
@require_http_methods(["POST"])
def guardar_comprobacion_json(request, equipo_id):
    """
    Guarda los datos JSON de la comprobación metrológica.
    """
    try:
        # Superusuarios pueden ver equipos de cualquier empresa
        if request.user.is_superuser:
            equipo = get_object_or_404(Equipo, id=equipo_id)
        else:
            equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)
        datos = json.loads(request.body)

        comprobacion_id = datos.get('comprobacion_id')

        # Crear o actualizar comprobación
        if comprobacion_id:
            comprobacion = get_object_or_404(
                Comprobacion,
                id=comprobacion_id,
                equipo=equipo
            )
        else:
            # Crear nueva comprobación
            comprobacion = Comprobacion.objects.create(
                equipo=equipo,
                fecha_comprobacion=datetime.now().date(),
                resultado='Aprobado',  # Se actualizará según conformidad
            )

        # Guardar datos JSON
        comprobacion.datos_comprobacion = datos

        # Determinar resultado basado en conformidad
        puntos = datos.get('puntos_medicion', [])
        no_conforme = any(p.get('conformidad') == 'NO CONFORME' for p in puntos)
        comprobacion.resultado = 'No Aprobado' if no_conforme else 'Aprobado'

        comprobacion.save()

        return JsonResponse({
            'success': True,
            'comprobacion_id': comprobacion.id,
            'mensaje': 'Comprobación guardada exitosamente'
        })

    except Exception as e:
        logger.error(f"Error al guardar comprobación: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def generar_grafica_svg_comprobacion(puntos, unidad='mm'):
    """
    Genera una gráfica SVG de errores vs límites EMP para comprobación.
    """
    if not puntos or len(puntos) == 0:
        return '<svg width="700" height="350"><text x="350" y="175" text-anchor="middle" fill="#999">No hay datos para mostrar</text></svg>'

    # Dimensiones
    width, height = 700, 350
    margin = {'top': 30, 'right': 60, 'bottom': 50, 'left': 70}
    plot_width = width - margin['left'] - margin['right']
    plot_height = height - margin['top'] - margin['bottom']

    # Extraer datos
    errores = [safe_float(p.get('error', 0), 0) for p in puntos]
    emps = [safe_float(p.get('emp_absoluto', 0), 0) for p in puntos]

    # Calcular escalas
    max_error = max(max(errores), max(emps))
    min_error = min(min(errores), -max(emps))
    rango = max_error - min_error
    padding = rango * 0.15

    y_max = max_error + padding
    y_min = min_error - padding

    def escala_y(valor):
        return margin['top'] + plot_height - ((valor - y_min) / (y_max - y_min)) * plot_height

    def escala_x(index):
        if len(puntos) == 1:
            return margin['left'] + plot_width / 2
        return margin['left'] + (index / (len(puntos) - 1)) * plot_width

    # Comenzar SVG
    svg_parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']

    # Título
    svg_parts.append(f'<text x="{width/2}" y="18" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#2D3748">Errores de Medición vs Límites EMP</text>')

    # Cuadrícula
    num_ticks = 6
    for i in range(num_ticks + 1):
        valor = y_min + (y_max - y_min) * (i / num_ticks)
        y = escala_y(valor)
        svg_parts.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{margin["left"] + plot_width}" y2="{y}" stroke="#E5E7EB" stroke-width="1"/>')
        svg_parts.append(f'<text x="{margin["left"] - 5}" y="{y + 3}" text-anchor="end" font-family="Arial" font-size="8" fill="#4B5563">{valor:.3f}</text>')

    # Ejes
    svg_parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"] + plot_height}" stroke="#2D3748" stroke-width="2"/>')
    svg_parts.append(f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_height}" x2="{margin["left"] + plot_width}" y2="{margin["top"] + plot_height}" stroke="#2D3748" stroke-width="2"/>')

    # Línea de cero
    y0 = escala_y(0)
    svg_parts.append(f'<line x1="{margin["left"]}" y1="{y0}" x2="{margin["left"] + plot_width}" y2="{y0}" stroke="#9CA3AF" stroke-width="1" stroke-dasharray="3,3"/>')

    # Límites EMP (líneas rojas escalonadas)
    # Límite superior
    path_sup = f'M {margin["left"]} {escala_y(emps[0])}'
    for i in range(len(puntos)):
        x = escala_x(i)
        y = escala_y(emps[i])
        path_sup += f' L {x} {y}'
        if i < len(puntos) - 1:
            x_next = escala_x(i + 1)
            path_sup += f' L {x_next} {y}'
    path_sup += f' L {margin["left"] + plot_width} {escala_y(emps[-1])}'
    svg_parts.append(f'<path d="{path_sup}" stroke="#ef4444" stroke-width="2" stroke-dasharray="5,5" fill="none"/>')

    # Límite inferior
    path_inf = f'M {margin["left"]} {escala_y(-emps[0])}'
    for i in range(len(puntos)):
        x = escala_x(i)
        y = escala_y(-emps[i])
        path_inf += f' L {x} {y}'
        if i < len(puntos) - 1:
            x_next = escala_x(i + 1)
            path_inf += f' L {x_next} {y}'
    path_inf += f' L {margin["left"] + plot_width} {escala_y(-emps[-1])}'
    svg_parts.append(f'<path d="{path_inf}" stroke="#ef4444" stroke-width="2" stroke-dasharray="5,5" fill="none"/>')

    # Puntos de error
    for i, punto in enumerate(puntos):
        x = escala_x(i)
        y = escala_y(errores[i])
        color = '#3b82f6' if punto.get('conformidad') == 'CONFORME' else '#ef4444'
        svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="#fff" stroke-width="2"/>')

    # Etiquetas eje X
    for i in range(len(puntos)):
        if i % max(1, len(puntos) // 10) == 0 or i == len(puntos) - 1:
            x = escala_x(i)
            svg_parts.append(f'<text x="{x}" y="{margin["top"] + plot_height + 15}" text-anchor="middle" font-family="Arial" font-size="9" fill="#4B5563">P{i+1}</text>')

    # Etiqueta eje X
    svg_parts.append(f'<text x="{width/2}" y="{height - 10}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#2D3748">Punto de Medición</text>')

    # Etiqueta eje Y (rotada)
    svg_parts.append(f'<text x="15" y="{height/2}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#2D3748" transform="rotate(-90 15 {height/2})">Error ({unidad})</text>')

    svg_parts.append('</svg>')

    return ''.join(svg_parts)


@login_required
@require_http_methods(["POST"])
def generar_pdf_comprobacion(request, equipo_id):
    """
    Genera el PDF de la comprobación metrológica.
    """
    try:
        # Superusuarios pueden ver equipos de cualquier empresa
        if request.user.is_superuser:
            equipo = get_object_or_404(Equipo, id=equipo_id)
        else:
            equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)
        comprobacion_id = request.GET.get('comprobacion_id')

        if not comprobacion_id:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó ID de comprobación'
            }, status=400)

        comprobacion = get_object_or_404(
            Comprobacion,
            id=comprobacion_id,
            equipo=equipo
        )

        # Obtener datos del POST
        datos_json = request.POST.get('datos_comprobacion')
        if datos_json:
            datos_comprobacion = json.loads(datos_json)
        else:
            datos_comprobacion = (comprobacion.datos_comprobacion
                                 if hasattr(comprobacion, 'datos_comprobacion')
                                 else {}) or {}

        # Calcular estadísticas de conformidad
        puntos = datos_comprobacion.get('puntos_medicion', [])
        puntos_conformes = sum(1 for p in puntos if p.get('conformidad') == 'CONFORME')
        puntos_no_conformes = sum(1 for p in puntos if p.get('conformidad') == 'NO CONFORME')
        total_puntos = len(puntos)

        # Generar gráfica SVG
        unidad = datos_comprobacion.get('unidad_equipo', 'mm')
        grafica_svg = generar_grafica_svg_comprobacion(puntos, unidad)

        # Preparar datos para el template
        context = {
            'equipo': equipo,
            'comprobacion': comprobacion,
            'datos_comprobacion': datos_comprobacion,
            'empresa': equipo.empresa,
            'fecha_generacion': datetime.now(),
            'puntos_conformes': puntos_conformes,
            'puntos_no_conformes': puntos_no_conformes,
            'total_puntos': total_puntos,
            'grafica_svg': grafica_svg,
        }

        # Renderizar template
        html_string = render_to_string('core/comprobacion_metrologica_print.html', context)

        # Generar PDF
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

        # Guardar PDF en el modelo
        fecha_str = comprobacion.fecha_comprobacion.strftime('%Y%m%d')
        filename = f'comprobacion_{equipo.codigo_interno}_{fecha_str}.pdf'
        comprobacion.comprobacion_pdf.save(filename, ContentFile(pdf_file), save=True)

        return JsonResponse({
            'success': True,
            'pdf_url': comprobacion.comprobacion_pdf.url,
            'mensaje': 'PDF generado exitosamente'
        })

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error al generar PDF de comprobación: {str(e)}\n{error_traceback}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': error_traceback if request.user.is_superuser else None
        }, status=500)
