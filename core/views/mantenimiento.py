"""
Vistas para Mantenimientos con Actividades Estructuradas y PDF
Permite registrar mantenimientos con actividades según tipo y generar PDF profesional.
"""

import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from weasyprint import HTML

from core.models import Mantenimiento, Equipo

logger = logging.getLogger(__name__)


# Definir actividades por tipo de mantenimiento
ACTIVIDADES_POR_TIPO = {
    'Preventivo': [
        'Limpieza general del equipo',
        'Verificación y ajuste de componentes',
        'Lubricación de partes móviles',
        'Inspección visual completa',
        'Cambio de baterías',
        'Cambio/limpieza de accesorios',
        'Verificación de funcionalidad',
        'Calibración de ajustes',
        'Revisión de conexiones eléctricas',
        'Actualización de firmware/software',
    ],
    'Correctivo': [
        'Diagnóstico del problema',
        'Reemplazo de componentes defectuosos',
        'Reparación de circuitos',
        'Ajuste y pruebas post-reparación',
        'Verificación de funcionamiento',
    ],
    'Predictivo': [
        'Análisis de datos históricos',
        'Medición de parámetros operativos',
        'Evaluación de desgaste',
        'Análisis de vibraciones',
        'Termografía',
        'Pronóstico de vida útil',
        'Recomendaciones preventivas',
    ],
    'Inspección': [
        'Inspección visual externa',
        'Verificación de etiquetas e identificación',
        'Revisión de estado general',
        'Comprobación de seguridad',
        'Verificación de documentación',
        'Pruebas de funcionamiento básico',
        'Registro fotográfico',
    ],
    'Otro': []  # Campo libre
}


@login_required
@require_http_methods(["GET", "POST"])
def mantenimiento_actividades_view(request, equipo_id):
    """
    Vista para crear/editar mantenimiento con actividades estructuradas.
    """
    # Superusuarios pueden ver equipos de cualquier empresa
    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

    mantenimiento_id = request.GET.get('mantenimiento_id')

    # Obtener mantenimiento existente si se proporciona ID
    mantenimiento = None
    datos_existentes = None

    if mantenimiento_id:
        mantenimiento = get_object_or_404(
            Mantenimiento,
            id=mantenimiento_id,
            equipo=equipo
        )
        if mantenimiento.actividades_realizadas:
            datos_existentes = json.dumps(mantenimiento.actividades_realizadas)

    # Obtener logo y datos de la empresa
    logo_empresa_url = None
    nombre_empresa = "Sin Empresa"

    if equipo.empresa:
        nombre_empresa = equipo.empresa.nombre
        if equipo.empresa.logo_empresa:
            try:
                logo_empresa_url = equipo.empresa.logo_empresa.url
            except:
                logo_empresa_url = None

    # Obtener información de formato de la empresa
    formato_codigo = equipo.empresa.formato_codificacion_empresa or 'SAM-MANT-001'
    formato_version = equipo.empresa.formato_version_empresa or '01'
    formato_fecha = equipo.empresa.formato_fecha_version_empresa or datetime.now().date()

    context = {
        'equipo': equipo,
        'mantenimiento': mantenimiento,
        'mantenimiento_id': mantenimiento_id,
        'datos_existentes': datos_existentes,
        'actividades_por_tipo': json.dumps(ACTIVIDADES_POR_TIPO),
        'logo_empresa_url': logo_empresa_url,
        'nombre_empresa': nombre_empresa,
        'formato_codigo': formato_codigo,
        'formato_version': formato_version,
        'formato_fecha': formato_fecha,
    }

    return render(request, 'core/mantenimiento_actividades.html', context)


@login_required
@require_http_methods(["POST"])
def guardar_mantenimiento_json(request, equipo_id):
    """
    Guarda los datos JSON del mantenimiento con actividades.
    """
    try:
        # Superusuarios pueden ver equipos de cualquier empresa
        if request.user.is_superuser:
            equipo = get_object_or_404(Equipo, id=equipo_id)
        else:
            equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

        datos = json.loads(request.body)
        mantenimiento_id = datos.get('mantenimiento_id')

        # Crear o actualizar mantenimiento
        if mantenimiento_id:
            mantenimiento = get_object_or_404(
                Mantenimiento,
                id=mantenimiento_id,
                equipo=equipo
            )
            # Actualizar campos del mantenimiento existente
            mantenimiento.fecha_mantenimiento = datos.get('fecha_mantenimiento', datetime.now().date())
            mantenimiento.tipo_mantenimiento = datos.get('tipo_mantenimiento', mantenimiento.tipo_mantenimiento)
            mantenimiento.responsable = datos.get('responsable', mantenimiento.responsable)
            mantenimiento.descripcion = datos.get('descripcion', mantenimiento.descripcion)
        else:
            # Crear nuevo mantenimiento
            mantenimiento = Mantenimiento.objects.create(
                equipo=equipo,
                fecha_mantenimiento=datos.get('fecha_mantenimiento', datetime.now().date()),
                tipo_mantenimiento=datos.get('tipo_mantenimiento', 'Preventivo'),
                responsable=datos.get('responsable', ''),
                descripcion=datos.get('descripcion', ''),
            )

        # Guardar datos JSON de actividades
        mantenimiento.actividades_realizadas = datos
        mantenimiento.save()

        return JsonResponse({
            'success': True,
            'mantenimiento_id': mantenimiento.id,
            'mensaje': 'Mantenimiento guardado exitosamente'
        })

    except Exception as e:
        logger.error(f"Error al guardar mantenimiento: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Función de gráficas removida - no se necesita para mantenimientos


@login_required
@require_http_methods(["POST"])
def generar_pdf_mantenimiento(request, equipo_id):
    """
    Genera el PDF del mantenimiento con actividades.
    """
    try:
        # Superusuarios pueden ver equipos de cualquier empresa
        if request.user.is_superuser:
            equipo = get_object_or_404(Equipo, id=equipo_id)
        else:
            equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

        mantenimiento_id = request.GET.get('mantenimiento_id')

        if not mantenimiento_id:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó ID de mantenimiento'
            }, status=400)

        mantenimiento = get_object_or_404(
            Mantenimiento,
            id=mantenimiento_id,
            equipo=equipo
        )

        # Obtener datos del POST
        datos_json = request.POST.get('datos_mantenimiento')
        if datos_json:
            datos_mantenimiento = json.loads(datos_json)
        else:
            datos_mantenimiento = mantenimiento.actividades_realizadas or {}

        # Preparar datos para el template (solo checklist, sin gráficas)
        context = {
            'equipo': equipo,
            'mantenimiento': mantenimiento,
            'datos_mantenimiento': datos_mantenimiento,
            'empresa': equipo.empresa,
            'fecha_generacion': datetime.now(),
        }

        # Renderizar template
        html_string = render_to_string('core/mantenimiento_print.html', context)

        # Generar PDF
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

        # Guardar PDF en el modelo
        fecha_str = mantenimiento.fecha_mantenimiento.strftime('%Y%m%d')
        filename = f'mantenimiento_{equipo.codigo_interno}_{fecha_str}.pdf'
        mantenimiento.documento_mantenimiento.save(filename, ContentFile(pdf_file), save=True)

        return JsonResponse({
            'success': True,
            'pdf_url': mantenimiento.documento_mantenimiento.url,
            'mensaje': 'PDF generado exitosamente'
        })

    except Exception as e:
        logger.error(f"Error al generar PDF de mantenimiento: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
