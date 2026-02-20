"""
Vistas para el sistema de aprobación de documentos.
Solo confirmaciones metrológicas, intervalos de calibración y comprobaciones requieren aprobación.
Los mantenimientos NO requieren aprobación.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q
import logging

from ..models import Calibracion, Comprobacion

logger = logging.getLogger(__name__)


@login_required
def pagina_aprobaciones(request):
    """
    Página principal de aprobaciones.
    Muestra todos los documentos pendientes de aprobación para Admin/Gerente.
    Técnicos solo ven sus documentos pendientes/rechazados.
    """
    user = request.user
    empresa = user.empresa

    # Verificar que el usuario tenga empresa
    if not empresa:
        return render(request, 'core/aprobaciones.html', {
            'error': 'No tienes empresa asignada'
        })

    # Determinar qué documentos mostrar según el rol
    es_aprobador = user.rol_usuario in ['ADMINISTRADOR', 'GERENCIA']

    # CONFIRMACIONES METROLÓGICAS
    # Solo documentos generados por la plataforma (tienen datos JSON).
    # Los PDFs subidos manualmente NO entran en flujo de aprobación.
    confirmaciones_query = Calibracion.objects.filter(
        equipo__empresa=empresa,
        confirmacion_metrologica_pdf__isnull=False,
        confirmacion_metrologica_datos__isnull=False
    ).exclude(
        confirmacion_metrologica_datos={}
    ).select_related('equipo', 'creado_por', 'confirmacion_aprobado_por')

    if es_aprobador:
        # Admin/Gerente ve todos los pendientes (excepto los suyos)
        confirmaciones_pendientes = confirmaciones_query.filter(
            confirmacion_estado_aprobacion='pendiente'
        ).exclude(creado_por=user).order_by('-fecha_registro')

        confirmaciones_rechazadas = confirmaciones_query.filter(
            confirmacion_estado_aprobacion='rechazado'
        ).order_by('-fecha_registro')[:10]  # Últimas 10 rechazadas
    else:
        # Técnico ve SOLO pendientes y rechazados (NO aprobados)
        confirmaciones_pendientes = confirmaciones_query.filter(
            Q(confirmacion_estado_aprobacion='pendiente') | Q(confirmacion_estado_aprobacion='rechazado'),
            creado_por=user
        ).order_by('-fecha_registro')

        confirmaciones_rechazadas = []

    # INTERVALOS DE CALIBRACIÓN
    # Solo documentos generados por la plataforma (tienen datos JSON).
    intervalos_query = Calibracion.objects.filter(
        equipo__empresa=empresa,
        intervalos_calibracion_pdf__isnull=False,
        intervalos_calibracion_datos__isnull=False
    ).exclude(
        intervalos_calibracion_datos={}
    ).select_related('equipo', 'creado_por', 'intervalos_aprobado_por')

    if es_aprobador:
        intervalos_pendientes = intervalos_query.filter(
            intervalos_estado_aprobacion='pendiente'
        ).exclude(creado_por=user).order_by('-fecha_registro')

        intervalos_rechazados = intervalos_query.filter(
            intervalos_estado_aprobacion='rechazado'
        ).order_by('-fecha_registro')[:10]
    else:
        # Técnico ve SOLO pendientes y rechazados (NO aprobados)
        intervalos_pendientes = intervalos_query.filter(
            Q(intervalos_estado_aprobacion='pendiente') | Q(intervalos_estado_aprobacion='rechazado'),
            creado_por=user
        ).order_by('-fecha_registro')

        intervalos_rechazados = []

    # COMPROBACIONES METROLÓGICAS
    # Solo documentos generados por la plataforma (tienen datos JSON).
    comprobaciones_query = Comprobacion.objects.filter(
        equipo__empresa=empresa,
        comprobacion_pdf__isnull=False,
        datos_comprobacion__isnull=False
    ).exclude(
        datos_comprobacion={}
    ).select_related('equipo', 'creado_por', 'aprobado_por')

    if es_aprobador:
        comprobaciones_pendientes = comprobaciones_query.filter(
            estado_aprobacion='pendiente'
        ).exclude(creado_por=user).order_by('-fecha_registro')

        comprobaciones_rechazadas = comprobaciones_query.filter(
            estado_aprobacion='rechazado'
        ).order_by('-fecha_registro')[:10]
    else:
        # Técnico ve SOLO pendientes y rechazados (NO aprobados)
        comprobaciones_pendientes = comprobaciones_query.filter(
            Q(estado_aprobacion='pendiente') | Q(estado_aprobacion='rechazado'),
            creado_por=user
        ).order_by('-fecha_registro')

        comprobaciones_rechazadas = []

    # Contar totales
    total_pendientes = (
        confirmaciones_pendientes.count() +
        intervalos_pendientes.count() +
        comprobaciones_pendientes.count()
    )

    context = {
        'es_aprobador': es_aprobador,
        'total_pendientes': total_pendientes,

        # Confirmaciones
        'confirmaciones_pendientes': confirmaciones_pendientes,
        'confirmaciones_rechazadas': confirmaciones_rechazadas,

        # Intervalos
        'intervalos_pendientes': intervalos_pendientes,
        'intervalos_rechazados': intervalos_rechazados,

        # Comprobaciones
        'comprobaciones_pendientes': comprobaciones_pendientes,
        'comprobaciones_rechazadas': comprobaciones_rechazadas,
    }

    return render(request, 'core/aprobaciones.html', context)


def puede_aprobar(usuario, documento):
    """
    Determina si un usuario puede aprobar un documento.

    Reglas:
    - Técnicos NO pueden aprobar nada
    - Nadie puede aprobar su propio documento
    - El documento debe pertenecer a la empresa del usuario (aislamiento multi-tenant)
    - Admin y Gerente pueden aprobar (si no es suyo y es de su empresa)
    - Superusuarios pueden aprobar cualquier documento
    """
    # Superusuarios pueden aprobar cualquier documento
    if usuario.is_superuser:
        return True

    # Técnicos NO pueden aprobar
    if usuario.rol_usuario == 'TECNICO':
        return False

    # Nadie puede auto-aprobar
    if documento.creado_por == usuario:
        return False

    # Validar que el documento pertenezca a la empresa del usuario (multi-tenant)
    if not usuario.empresa:
        return False

    documento_empresa = getattr(documento, 'equipo', None)
    if documento_empresa and hasattr(documento_empresa, 'empresa'):
        if documento_empresa.empresa != usuario.empresa:
            return False

    # Admin y Gerente pueden aprobar (si no es suyo y es de su empresa)
    if usuario.rol_usuario in ['ADMINISTRADOR', 'GERENCIA']:
        return True

    return False


@login_required
@require_POST
def aprobar_confirmacion(request, calibracion_id):
    """
    Aprueba una confirmación metrológica.
    Solo Admin o Gerente pueden aprobar (y no su propio documento).
    """
    try:
        # Filtrar por empresa del usuario para aislamiento multi-tenant
        if request.user.is_superuser:
            calibracion = get_object_or_404(Calibracion, id=calibracion_id)
        else:
            calibracion = get_object_or_404(
                Calibracion, id=calibracion_id,
                equipo__empresa=request.user.empresa
            )

        # Verificar permisos
        if not puede_aprobar(request.user, calibracion):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para aprobar este documento'
            }, status=403)

        # Verificar que tenga confirmación metrológica
        if not calibracion.confirmacion_metrologica_pdf:
            return JsonResponse({
                'success': False,
                'error': 'Esta calibración no tiene confirmación metrológica'
            }, status=400)

        # Obtener fechas ajustables del POST (si se proporcionan)
        from datetime import datetime

        # Fecha de realización (por defecto: fecha_calibracion)
        fecha_realizacion_str = request.POST.get('fecha_realizacion')
        if fecha_realizacion_str:
            try:
                calibracion.confirmacion_fecha_realizacion = datetime.strptime(fecha_realizacion_str, '%Y-%m-%d').date()
            except ValueError:
                calibracion.confirmacion_fecha_realizacion = calibracion.fecha_calibracion
        else:
            calibracion.confirmacion_fecha_realizacion = calibracion.fecha_calibracion

        # Fecha de emisión (por defecto: hoy)
        fecha_emision_str = request.POST.get('fecha_emision')
        if fecha_emision_str:
            try:
                calibracion.confirmacion_fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            except ValueError:
                calibracion.confirmacion_fecha_emision = timezone.now().date()
        else:
            calibracion.confirmacion_fecha_emision = timezone.now().date()

        # Fecha de aprobación ajustable (por defecto: hoy)
        fecha_aprobacion_ajustable_str = request.POST.get('fecha_aprobacion_ajustable')
        if fecha_aprobacion_ajustable_str:
            try:
                calibracion.confirmacion_fecha_aprobacion_ajustable = datetime.strptime(fecha_aprobacion_ajustable_str, '%Y-%m-%d').date()
            except ValueError:
                calibracion.confirmacion_fecha_aprobacion_ajustable = timezone.now().date()
        else:
            calibracion.confirmacion_fecha_aprobacion_ajustable = timezone.now().date()

        # Aprobar confirmación (campos específicos)
        calibracion.confirmacion_estado_aprobacion = 'aprobado'
        calibracion.confirmacion_aprobado_por = request.user
        calibracion.confirmacion_fecha_aprobacion = timezone.now()
        calibracion.confirmacion_observaciones_rechazo = None  # Limpiar observaciones previas
        calibracion.save()

        logger.info(f"Confirmación metrológica #{calibracion_id} aprobada por {request.user.username}")

        # Regenerar PDF solo si fue generado por la plataforma (tiene datos JSON).
        # Los PDFs subidos manualmente NO se regeneran para preservar el archivo original.
        datos_json = calibracion.confirmacion_metrologica_datos
        if datos_json and isinstance(datos_json, dict) and len(datos_json) > 0:
            try:
                from ..views.confirmacion import _preparar_contexto_confirmacion, _generar_grafica_confirmacion
                from django.template.loader import render_to_string
                from django.core.files.base import ContentFile
                from weasyprint import HTML
                from weasyprint.text.fonts import FontConfiguration

                # Preparar contexto para el PDF
                equipo = calibracion.equipo
                context = _preparar_contexto_confirmacion(request, equipo, calibracion, datos_json)

                # Generar gráfica si hay datos
                if 'puntos_medicion' in datos_json:
                    emp_valor = datos_json.get('emp_valor', 0)
                    emp_unidad = datos_json.get('emp_unidad', '%')
                    unidad_equipo = datos_json.get('unidad_equipo', '')
                    grafica_base64 = _generar_grafica_confirmacion(
                        datos_json['puntos_medicion'],
                        emp_valor,
                        emp_unidad,
                        unidad_equipo
                    )
                    context['grafica_imagen'] = grafica_base64

                # Renderizar y generar PDF
                html_string = render_to_string('core/confirmacion_metrologica_print.html', context)
                font_config = FontConfiguration()
                html_pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
                pdf_file = html_pdf.write_pdf(font_config=font_config)

                # Guardar PDF actualizado
                filename = f'confirmacion_metrologica_{equipo.codigo_interno}_{calibracion.fecha_calibracion.strftime("%Y%m%d")}.pdf'
                calibracion.confirmacion_metrologica_pdf.save(filename, ContentFile(pdf_file), save=True)

                logger.info(f"PDF de confirmación regenerado con información de aprobación")
            except Exception as e:
                logger.error(f"Error regenerando PDF de confirmación: {e}")
                # No fallar la aprobación si el PDF falla
        else:
            logger.info(f"Confirmación #{calibracion_id}: PDF manual, no se regenera")

        return JsonResponse({
            'success': True,
            'message': f'Confirmación aprobada por {request.user.get_full_name() or request.user.username}',
            'aprobado_por': request.user.get_full_name() or request.user.username,
            'fecha_aprobacion': calibracion.confirmacion_fecha_aprobacion.strftime('%Y-%m-%d %H:%M')
        })

    except Exception as e:
        logger.error(f"Error aprobando confirmación {calibracion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def rechazar_confirmacion(request, calibracion_id):
    """
    Rechaza una confirmación metrológica con observaciones.
    """
    try:
        # Filtrar por empresa del usuario para aislamiento multi-tenant
        if request.user.is_superuser:
            calibracion = get_object_or_404(Calibracion, id=calibracion_id)
        else:
            calibracion = get_object_or_404(
                Calibracion, id=calibracion_id,
                equipo__empresa=request.user.empresa
            )

        # Verificar permisos
        if not puede_aprobar(request.user, calibracion):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para rechazar este documento'
            }, status=403)

        # Obtener observaciones
        import json
        data = json.loads(request.body)
        observaciones = data.get('observaciones', '').strip()

        if not observaciones:
            return JsonResponse({
                'success': False,
                'error': 'Debes proporcionar observaciones para el rechazo'
            }, status=400)

        # Rechazar confirmación (campos específicos)
        calibracion.confirmacion_estado_aprobacion = 'rechazado'
        calibracion.confirmacion_observaciones_rechazo = observaciones
        calibracion.confirmacion_aprobado_por = None
        calibracion.confirmacion_fecha_aprobacion = None
        calibracion.save()

        logger.info(f"Confirmación metrológica #{calibracion_id} rechazada por {request.user.username}")

        # TODO: Implementar sistema de notificaciones in-app
        # Por ahora el técnico verá el rechazo cuando entre a /core/aprobaciones/

        return JsonResponse({
            'success': True,
            'message': 'Confirmación rechazada. El técnico deberá corregir.',
            'observaciones': observaciones
        })

    except Exception as e:
        logger.error(f"Error rechazando confirmación {calibracion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def aprobar_intervalos(request, calibracion_id):
    """
    Aprueba intervalos de calibración.
    """
    try:
        # Filtrar por empresa del usuario para aislamiento multi-tenant
        if request.user.is_superuser:
            calibracion = get_object_or_404(Calibracion, id=calibracion_id)
        else:
            calibracion = get_object_or_404(
                Calibracion, id=calibracion_id,
                equipo__empresa=request.user.empresa
            )

        # Verificar permisos
        if not puede_aprobar(request.user, calibracion):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para aprobar este documento'
            }, status=403)

        # Verificar que tenga intervalos
        if not calibracion.intervalos_calibracion_pdf:
            return JsonResponse({
                'success': False,
                'error': 'Esta calibración no tiene intervalos de calibración'
            }, status=400)

        # Obtener fechas ajustables del POST (si se proporcionan)
        from datetime import datetime

        # Fecha de realización (por defecto: fecha_calibracion)
        fecha_realizacion_str = request.POST.get('fecha_realizacion')
        if fecha_realizacion_str:
            try:
                calibracion.intervalos_fecha_realizacion = datetime.strptime(fecha_realizacion_str, '%Y-%m-%d').date()
            except ValueError:
                calibracion.intervalos_fecha_realizacion = calibracion.fecha_calibracion
        else:
            calibracion.intervalos_fecha_realizacion = calibracion.fecha_calibracion

        # Fecha de emisión (por defecto: hoy)
        fecha_emision_str = request.POST.get('fecha_emision')
        if fecha_emision_str:
            try:
                calibracion.intervalos_fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            except ValueError:
                calibracion.intervalos_fecha_emision = timezone.now().date()
        else:
            calibracion.intervalos_fecha_emision = timezone.now().date()

        # Fecha de aprobación ajustable (por defecto: hoy)
        fecha_aprobacion_ajustable_str = request.POST.get('fecha_aprobacion_ajustable')
        if fecha_aprobacion_ajustable_str:
            try:
                calibracion.intervalos_fecha_aprobacion_ajustable = datetime.strptime(fecha_aprobacion_ajustable_str, '%Y-%m-%d').date()
            except ValueError:
                calibracion.intervalos_fecha_aprobacion_ajustable = timezone.now().date()
        else:
            calibracion.intervalos_fecha_aprobacion_ajustable = timezone.now().date()

        # Aprobar intervalos (campos específicos)
        calibracion.intervalos_estado_aprobacion = 'aprobado'
        calibracion.intervalos_aprobado_por = request.user
        calibracion.intervalos_fecha_aprobacion = timezone.now()
        calibracion.intervalos_observaciones_rechazo = None
        calibracion.save()

        logger.info(f"Intervalos de calibración #{calibracion_id} aprobados por {request.user.username}")

        # Regenerar PDF solo si fue generado por la plataforma (tiene datos JSON).
        # Los PDFs subidos manualmente NO se regeneran para preservar el archivo original.
        datos_intervalos = calibracion.intervalos_calibracion_datos
        if datos_intervalos and isinstance(datos_intervalos, dict) and len(datos_intervalos) > 0:
            try:
                from django.template.loader import render_to_string
                from django.core.files.base import ContentFile
                from weasyprint import HTML
                from weasyprint.text.fonts import FontConfiguration
                from datetime import datetime
                import re

                equipo = calibracion.equipo

                # Calibración anterior
                cal_anterior = Calibracion.objects.filter(
                    equipo=equipo,
                    fecha_calibracion__lt=calibracion.fecha_calibracion
                ).order_by('-fecha_calibracion').first()

                # EMP info
                emp_info = {'valor': 8, 'unidad': '%', 'texto': '8%'}
                if equipo.error_maximo_permisible:
                    emp_texto = equipo.error_maximo_permisible.strip()
                    emp_match = re.search(r'([\d.]+)\s*(%|mm|lx|μm|°C|g|kg|m)?', emp_texto)
                    if emp_match:
                        emp_info['valor'] = float(emp_match.group(1))
                        emp_info['unidad'] = emp_match.group(2) if emp_match.group(2) else ''
                        emp_info['texto'] = emp_texto

                # Logo
                logo_empresa_url = None
                try:
                    if equipo.empresa and equipo.empresa.logo_empresa:
                        logo_empresa_url = equipo.empresa.logo_empresa.url
                except Exception:
                    pass

                # Formato fecha
                formato_fecha_formateada_int = None
                if equipo.empresa.intervalos_fecha_formato_display:
                    formato_fecha_formateada_int = equipo.empresa.intervalos_fecha_formato_display
                    if datos_intervalos.get('formato'):
                        datos_intervalos['formato']['fecha'] = formato_fecha_formateada_int
                elif datos_intervalos.get('formato', {}).get('fecha'):
                    formato_fecha_formateada_int = datos_intervalos['formato']['fecha']

                context = {
                    'equipo': equipo,
                    'cal_actual': calibracion,
                    'cal_anterior': cal_anterior,
                    'fecha_actual': datetime.now().date(),
                    'nombre_empresa': equipo.empresa.nombre,
                    'logo_empresa_url': logo_empresa_url,
                    'emp_info': emp_info,
                    'datos_intervalos': datos_intervalos,
                    'deriva_automatica': None,
                }

                html_string = render_to_string('core/intervalos_calibracion_print.html', context)
                font_config = FontConfiguration()
                html_pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
                pdf_file = html_pdf.write_pdf(font_config=font_config)

                filename = f'intervalos_calibracion_{equipo.codigo_interno}_{calibracion.fecha_calibracion.strftime("%Y%m%d")}.pdf'
                calibracion.intervalos_calibracion_pdf.save(filename, ContentFile(pdf_file), save=True)

                logger.info(f"PDF de intervalos regenerado con información de aprobación")
            except Exception as e:
                logger.error(f"Error regenerando PDF de intervalos: {e}")
                # No fallar la aprobación si el PDF falla
        else:
            logger.info(f"Intervalos #{calibracion_id}: PDF manual, no se regenera")

        return JsonResponse({
            'success': True,
            'message': f'Intervalos aprobados por {request.user.get_full_name() or request.user.username}',
            'aprobado_por': request.user.get_full_name() or request.user.username,
            'fecha_aprobacion': calibracion.intervalos_fecha_aprobacion.strftime('%Y-%m-%d %H:%M')
        })

    except Exception as e:
        logger.error(f"Error aprobando intervalos {calibracion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def rechazar_intervalos(request, calibracion_id):
    """
    Rechaza intervalos de calibración con observaciones.
    """
    try:
        # Filtrar por empresa del usuario para aislamiento multi-tenant
        if request.user.is_superuser:
            calibracion = get_object_or_404(Calibracion, id=calibracion_id)
        else:
            calibracion = get_object_or_404(
                Calibracion, id=calibracion_id,
                equipo__empresa=request.user.empresa
            )

        # Verificar permisos
        if not puede_aprobar(request.user, calibracion):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para rechazar este documento'
            }, status=403)

        # Obtener observaciones
        import json
        data = json.loads(request.body)
        observaciones = data.get('observaciones', '').strip()

        if not observaciones:
            return JsonResponse({
                'success': False,
                'error': 'Debes proporcionar observaciones para el rechazo'
            }, status=400)

        # Rechazar intervalos (campos específicos)
        calibracion.intervalos_estado_aprobacion = 'rechazado'
        calibracion.intervalos_observaciones_rechazo = observaciones
        calibracion.intervalos_aprobado_por = None
        calibracion.intervalos_fecha_aprobacion = None
        calibracion.save()

        logger.info(f"Intervalos de calibración #{calibracion_id} rechazados por {request.user.username}")

        # TODO: Implementar sistema de notificaciones in-app

        return JsonResponse({
            'success': True,
            'message': 'Intervalos rechazados. El técnico deberá corregir.',
            'observaciones': observaciones
        })

    except Exception as e:
        logger.error(f"Error rechazando intervalos {calibracion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def aprobar_comprobacion(request, comprobacion_id):
    """
    Aprueba una comprobación metrológica.
    """
    try:
        # Filtrar por empresa del usuario para aislamiento multi-tenant
        if request.user.is_superuser:
            comprobacion = get_object_or_404(Comprobacion, id=comprobacion_id)
        else:
            comprobacion = get_object_or_404(
                Comprobacion, id=comprobacion_id,
                equipo__empresa=request.user.empresa
            )

        # Verificar permisos
        if not puede_aprobar(request.user, comprobacion):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para aprobar este documento'
            }, status=403)

        # Verificar que tenga PDF de comprobación
        if not comprobacion.comprobacion_pdf:
            return JsonResponse({
                'success': False,
                'error': 'Esta comprobación no tiene PDF generado'
            }, status=400)

        # Obtener fechas ajustables del POST (si se proporcionan)
        from datetime import datetime

        # Fecha de realización (por defecto: fecha_comprobacion)
        fecha_realizacion_str = request.POST.get('fecha_realizacion')
        if fecha_realizacion_str:
            try:
                comprobacion.fecha_realizacion = datetime.strptime(fecha_realizacion_str, '%Y-%m-%d').date()
            except ValueError:
                comprobacion.fecha_realizacion = comprobacion.fecha_comprobacion
        else:
            comprobacion.fecha_realizacion = comprobacion.fecha_comprobacion

        # Fecha de emisión (por defecto: hoy)
        fecha_emision_str = request.POST.get('fecha_emision')
        if fecha_emision_str:
            try:
                comprobacion.fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date()
            except ValueError:
                comprobacion.fecha_emision = timezone.now().date()
        else:
            comprobacion.fecha_emision = timezone.now().date()

        # Fecha de aprobación ajustable (por defecto: hoy)
        fecha_aprobacion_ajustable_str = request.POST.get('fecha_aprobacion_ajustable')
        if fecha_aprobacion_ajustable_str:
            try:
                comprobacion.fecha_aprobacion_ajustable = datetime.strptime(fecha_aprobacion_ajustable_str, '%Y-%m-%d').date()
            except ValueError:
                comprobacion.fecha_aprobacion_ajustable = timezone.now().date()
        else:
            comprobacion.fecha_aprobacion_ajustable = timezone.now().date()

        # Aprobar
        comprobacion.estado_aprobacion = 'aprobado'
        comprobacion.aprobado_por = request.user
        comprobacion.fecha_aprobacion = timezone.now()
        comprobacion.observaciones_rechazo = None
        comprobacion.save()

        logger.info(f"Comprobación metrológica #{comprobacion_id} aprobada por {request.user.username}")

        # Regenerar PDF solo si fue generado por la plataforma (tiene datos JSON).
        # Los PDFs subidos manualmente NO se regeneran para preservar el archivo original.
        datos_comprobacion = comprobacion.datos_comprobacion
        if datos_comprobacion and isinstance(datos_comprobacion, dict) and len(datos_comprobacion) > 0:
            try:
                from ..views.comprobacion import generar_grafica_svg_comprobacion
                from django.template.loader import render_to_string
                from django.core.files.base import ContentFile
                from weasyprint import HTML
                from datetime import datetime

                equipo = comprobacion.equipo

                # Calcular estadísticas
                puntos = datos_comprobacion.get('puntos_medicion', [])
                puntos_conformes = sum(1 for p in puntos if p.get('conformidad') == 'CONFORME')
                puntos_no_conformes = sum(1 for p in puntos if p.get('conformidad') == 'NO CONFORME')
                total_puntos = len(puntos)

                # Generar gráfica
                unidad = datos_comprobacion.get('unidad_equipo', 'mm')
                grafica_svg = generar_grafica_svg_comprobacion(puntos, unidad)

                # Logo de empresa
                logo_empresa_url = None
                try:
                    if equipo.empresa and equipo.empresa.logo_empresa:
                        logo_empresa_url = equipo.empresa.logo_empresa.url
                except:
                    pass

                # Contexto
                context = {
                    'equipo': equipo,
                    'comprobacion': comprobacion,
                    'datos_comprobacion': datos_comprobacion,
                    'empresa': equipo.empresa,
                    'logo_empresa_url': logo_empresa_url,
                    'fecha_generacion': datetime.now(),
                    'puntos_conformes': puntos_conformes,
                    'puntos_no_conformes': puntos_no_conformes,
                    'total_puntos': total_puntos,
                    'grafica_svg': grafica_svg,
                }

                # Renderizar y generar PDF
                html_string = render_to_string('core/comprobacion_metrologica_print.html', context)
                pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

                # Guardar PDF actualizado
                fecha_str = comprobacion.fecha_comprobacion.strftime('%Y%m%d')
                filename = f'comprobacion_{equipo.codigo_interno}_{fecha_str}.pdf'
                comprobacion.comprobacion_pdf.save(filename, ContentFile(pdf_file), save=True)

                logger.info(f"PDF de comprobación regenerado con información de aprobación")
            except Exception as e:
                logger.error(f"Error regenerando PDF de comprobación: {e}")
                # No fallar la aprobación si el PDF falla
        else:
            logger.info(f"Comprobación #{comprobacion_id}: PDF manual, no se regenera")

        return JsonResponse({
            'success': True,
            'message': f'Comprobación aprobada por {request.user.get_full_name() or request.user.username}',
            'aprobado_por': request.user.get_full_name() or request.user.username,
            'fecha_aprobacion': comprobacion.fecha_aprobacion.strftime('%Y-%m-%d %H:%M')
        })

    except Exception as e:
        logger.error(f"Error aprobando comprobación {comprobacion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def rechazar_comprobacion(request, comprobacion_id):
    """
    Rechaza una comprobación metrológica con observaciones.
    """
    try:
        # Filtrar por empresa del usuario para aislamiento multi-tenant
        if request.user.is_superuser:
            comprobacion = get_object_or_404(Comprobacion, id=comprobacion_id)
        else:
            comprobacion = get_object_or_404(
                Comprobacion, id=comprobacion_id,
                equipo__empresa=request.user.empresa
            )

        # Verificar permisos
        if not puede_aprobar(request.user, comprobacion):
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para rechazar este documento'
            }, status=403)

        # Obtener observaciones
        import json
        data = json.loads(request.body)
        observaciones = data.get('observaciones', '').strip()

        if not observaciones:
            return JsonResponse({
                'success': False,
                'error': 'Debes proporcionar observaciones para el rechazo'
            }, status=400)

        # Rechazar
        comprobacion.estado_aprobacion = 'rechazado'
        comprobacion.observaciones_rechazo = observaciones
        comprobacion.aprobado_por = None
        comprobacion.fecha_aprobacion = None
        comprobacion.save()

        logger.info(f"Comprobación metrológica #{comprobacion_id} rechazada por {request.user.username}")

        # TODO: Implementar sistema de notificaciones in-app

        return JsonResponse({
            'success': True,
            'message': 'Comprobación rechazada. El técnico deberá corregir.',
            'observaciones': observaciones
        })

    except Exception as e:
        logger.error(f"Error rechazando comprobación {comprobacion_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
