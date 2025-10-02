# core/zip_functions.py
# Funciones ZIP migradas desde views.py para evitar problemas de importación

import logging
import io
import os
import zipfile
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Max
from django.core.files.storage import default_storage
from datetime import timedelta
from core.models import ZipRequest, Empresa, Equipo, Proveedor, Procedimiento
from .views.base import access_check

logger = logging.getLogger(__name__)

# Función de streaming local para evitar importaciones circulares
def stream_file_to_zip_local(zip_file, file_path, zip_path):
    """
    Función local de streaming para evitar importaciones circulares.
    """
    try:
        if not default_storage.exists(file_path):
            logger.warning(f"Archivo no existe: {file_path}")
            return False

        # Detectar tipo de storage para optimización específica
        storage_name = default_storage.__class__.__name__

        # Optimizar chunk size basado en el storage
        if 'S3' in storage_name:
            chunk_size = 32768  # 32KB chunks para S3
        else:
            chunk_size = 8192   # 8KB chunks para local

        with default_storage.open(file_path, 'rb') as f:
            with zip_file.open(zip_path, 'w') as zip_entry:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    zip_entry.write(chunk)

        logger.debug(f"Archivo transferido exitosamente: {file_path} -> {zip_path}")
        return True

    except Exception as e:
        logger.warning(f"Error streaming archivo {file_path}: {e}")
        return False


@access_check
@login_required
def solicitar_zip(request):
    """Vista para solicitar un ZIP. Agrega usuario a la cola."""

    # SISTEMA HÍBRIDO MEJORADO: Descarga directa para empresas pequeñas + Asíncrono para grandes
    empresa_id = request.GET.get('empresa_id') if request.user.is_superuser else None
    logger.info(f"Solicitud ZIP de usuario {request.user.username} (superuser: {request.user.is_superuser}) - empresa_id parámetro: {empresa_id}")

    # Determinar empresa para contar equipos
    if request.user.is_superuser and empresa_id:
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            logger.info(f"✅ Superusuario seleccionó empresa ID {empresa_id}: {empresa.nombre}")
        except Empresa.DoesNotExist:
            logger.error(f"❌ Empresa ID {empresa_id} no encontrada")
            return JsonResponse({'error': 'Empresa no encontrada'}, status=400)
    elif request.user.is_superuser:
        logger.warning(f"⚠️ Superusuario sin empresa_id especificada. Parámetros GET: {dict(request.GET)}")
        return JsonResponse({'error': 'Superusuario debe especificar empresa_id para descargar ZIP'}, status=400)
    else:
        empresa = request.user.empresa
        if not empresa:
            return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=400)
        logger.info(f"✅ Usuario normal usando su empresa: {empresa.nombre}")

    # Contar equipos TOTALES para decidir método de descarga (cambio: usar total, no solo activos)
    equipos_total_count = empresa.equipos.count()
    equipos_activos_count = empresa.equipos.filter(estado='Activo').count()

    # DESCARGA DIRECTA para ≤20 equipos TOTALES (aumentamos límite ligeramente)
    if equipos_total_count <= 20:
        logger.info(f"Empresa {empresa.nombre}: {equipos_total_count} equipos totales ({equipos_activos_count} activos) -> DESCARGA DIRECTA")
        return descarga_directa_rapida(request, empresa)

    # PROCESAMIENTO ASÍNCRONO para empresas grandes (SIN LÍMITE)
    logger.info(f"Empresa {empresa.nombre}: {equipos_total_count} equipos totales -> PROCESAMIENTO ASÍNCRONO")
    return solicitar_zip_asincrono(request, empresa)

    # Verificar si ya tiene una solicitud pendiente o procesándose
    existing = ZipRequest.objects.filter(
        user=request.user,
        status__in=['pending', 'processing']
    ).first()

    if existing:
        return JsonResponse({
            'status': 'already_pending',
            'request_id': existing.id,
            'position': existing.get_current_position(),
            'estimated_time': existing.get_estimated_wait_time(),
            'time_until_ready': existing.get_time_until_ready(),
            'detailed_message': existing.get_detailed_status_message(),
            'message': f'Ya tienes una solicitud: {existing.get_detailed_status_message()}'
        })

    # Obtener número de parte desde parámetros
    parte_numero = int(request.GET.get('parte', 1))

    # Obtener próxima posición en cola
    max_position = ZipRequest.objects.aggregate(
        max_pos=Max('position_in_queue')
    )['max_pos'] or 0

    # Crear nueva solicitud
    zip_request = ZipRequest.objects.create(
        user=request.user,
        empresa=empresa,
        status='pending',
        position_in_queue=max_position + 1,
        parte_numero=parte_numero,
        expires_at=timezone.now() + timedelta(hours=6)  # Expira en 6 horas
    )

    return JsonResponse({
        'status': 'queued',
        'request_id': zip_request.id,
        'position': zip_request.get_current_position(),
        'estimated_time': zip_request.get_estimated_wait_time(),
        'time_until_ready': zip_request.get_time_until_ready(),
        'detailed_message': zip_request.get_detailed_status_message(),
        'equipos_count': empresa.equipos.filter(estado='Activo').count(),
        'empresa_name': empresa.nombre,
        'parte_numero': parte_numero,
        'message': zip_request.get_detailed_status_message()
    })


@access_check
@login_required
def zip_status(request, request_id):
    """Vista para consultar el estado de una solicitud ZIP."""

    try:
        zip_req = ZipRequest.objects.get(id=request_id, user=request.user)

        # Verificar si expiró
        if zip_req.status == 'completed' and zip_req.expires_at and timezone.now() > zip_req.expires_at:
            zip_req.status = 'expired'
            zip_req.save()

        response_data = {
            'status': zip_req.status,
            'position': zip_req.get_current_position(),
            'estimated_time': zip_req.get_estimated_wait_time(),
            'time_until_ready': zip_req.get_time_until_ready(),
            'detailed_message': zip_req.get_detailed_status_message(),
            'created_at': zip_req.created_at.isoformat(),
            'parte_numero': zip_req.parte_numero,
            'request_id': zip_req.id,
            'empresa_nombre': zip_req.empresa.nombre if zip_req.empresa else 'Sin empresa',
            'equipos_count': zip_req.empresa.equipos.filter(estado='Activo').count() if zip_req.empresa else 0,
            'message': zip_req.get_detailed_status_message()
        }

        if zip_req.status == 'completed' and zip_req.file_path:
            response_data['download_url'] = f"/core/download_zip/{zip_req.id}/"

        if zip_req.error_message:
            response_data['error'] = zip_req.error_message

        return JsonResponse(response_data)

    except ZipRequest.DoesNotExist:
        return JsonResponse({'error': 'Solicitud no encontrada'}, status=404)


@access_check
@login_required
def download_zip(request, request_id):
    """Vista para descargar el archivo ZIP completado."""
    from django.http import HttpResponse

    try:
        zip_req = ZipRequest.objects.get(id=request_id, user=request.user)

        if zip_req.status != 'completed':
            return JsonResponse({'error': 'El ZIP aún no está listo'}, status=400)

        if not zip_req.file_path or not default_storage.exists(zip_req.file_path):
            return JsonResponse({'error': 'Archivo no encontrado'}, status=404)

        # Streaming de archivo para archivos grandes
        from django.http import StreamingHttpResponse
        import os

        def file_iterator(file_path, chunk_size=8192):
            with default_storage.open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        response = StreamingHttpResponse(
            file_iterator(zip_req.file_path),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="informe_completo_{zip_req.empresa.nombre}_{zip_req.parte_numero}.zip"'
        response['Content-Length'] = zip_req.file_size or default_storage.size(zip_req.file_path)

        logger.info(f"ZIP descargado: {zip_req.file_path} por {request.user.username}")
        return response

    except ZipRequest.DoesNotExist:
        return JsonResponse({'error': 'Solicitud no encontrada'}, status=404)
    except Exception as e:
        logger.error(f"Error descargando ZIP {request_id}: {e}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@access_check
@login_required
def cancel_zip_request(request, request_id):
    """Vista para cancelar una solicitud ZIP."""

    try:
        zip_req = ZipRequest.objects.get(id=request_id, user=request.user)

        if zip_req.status in ['completed', 'expired', 'cancelled']:
            return JsonResponse({'error': f'No se puede cancelar una solicitud {zip_req.status}'}, status=400)

        zip_req.status = 'cancelled'
        zip_req.save()

        logger.info(f"Solicitud ZIP cancelada: {request_id} por {request.user.username}")
        return JsonResponse({'status': 'cancelled', 'message': 'Solicitud cancelada exitosamente'})

    except ZipRequest.DoesNotExist:
        return JsonResponse({'error': 'Solicitud no encontrada'}, status=404)


@access_check
@login_required
def my_zip_requests(request):
    """Vista para obtener las solicitudes ZIP del usuario actual."""

    zip_requests = ZipRequest.objects.filter(user=request.user).order_by('-created_at')[:10]

    requests_data = []
    for zip_req in zip_requests:
        data = {
            'id': zip_req.id,
            'status': zip_req.status,
            'position': zip_req.get_current_position() if zip_req.status in ['pending', 'processing'] else None,
            'estimated_time': zip_req.get_estimated_wait_time(),
            'time_until_ready': zip_req.get_time_until_ready(),
            'detailed_message': zip_req.get_detailed_status_message(),
            'created_at': zip_req.created_at.isoformat(),
            'parte_numero': zip_req.parte_numero,
            'empresa_nombre': zip_req.empresa.nombre if zip_req.empresa else 'Sin empresa'
        }

        if zip_req.status == 'completed' and zip_req.file_path:
            data['download_url'] = f"/core/download_zip/{zip_req.id}/"

        if zip_req.error_message:
            data['error'] = zip_req.error_message

        requests_data.append(data)

    return JsonResponse({'requests': requests_data})


@access_check
@login_required
def trigger_zip_processing(request):
    """Endpoint para activar el procesamiento de ZIPs (solo para desarrollo)."""

    if not request.user.is_superuser:
        return JsonResponse({'error': 'Solo superusuarios'}, status=403)

    # Buscar próxima solicitud pendiente
    next_request = ZipRequest.objects.filter(status='pending').order_by('position_in_queue').first()

    if not next_request:
        return JsonResponse({'message': 'No hay solicitudes pendientes'})

    # Marcar como procesándose
    next_request.status = 'processing'
    next_request.started_at = timezone.now()
    next_request.save()

    logger.info(f"Procesamiento ZIP activado para solicitud {next_request.id}")

    return JsonResponse({
        'message': f'Procesamiento iniciado para solicitud {next_request.id}',
        'request_id': next_request.id
    })


@access_check
@login_required
def manual_process_zip(request):
    """Vista para procesamiento manual de ZIPs (solo superusuarios)."""

    if not request.user.is_superuser:
        return JsonResponse({'error': 'Solo superusuarios'}, status=403)

    return JsonResponse({
        'message': 'Funcionalidad de procesamiento manual disponible',
        'status': 'available'
    })


def descarga_directa_rapida(request, empresa):
    """
    DESCARGA DIRECTA INMEDIATA - Restaura funcionalidad de producción
    Para empresas con ≤15 equipos, genera y descarga ZIP inmediatamente (como producción).
    """
    try:
        logger.info(f"Descarga INMEDIATA para empresa {empresa.nombre} con {empresa.equipos.count()} equipos (todos los estados)")

        # Obtener TODOS los equipos (activos + dados de baja + inactivos) con prefetch optimizado
        equipos_empresa = Equipo.objects.filter(
            empresa=empresa
        ).select_related(
            'empresa',  # Empresa ya está filtrada, pero incluir para evitar queries extras
        ).prefetch_related(
            # Optimizar calibraciones
            'calibraciones',
            # Optimizar mantenimientos
            'mantenimientos',
            # Optimizar comprobaciones
            'comprobaciones',
            # Optimizar baja_registro
            'baja_registro'
        ).order_by('codigo_interno')

        # Optimizar consultas de proveedores y procedimientos
        proveedores_empresa = Proveedor.objects.filter(empresa=empresa).select_related('empresa').order_by('nombre_empresa')
        procedimientos_empresa = Procedimiento.objects.filter(empresa=empresa).select_related('empresa').order_by('codigo')

        # Crear ZIP en memoria con compresión adaptativa
        zip_buffer = io.BytesIO()

        # Optimizar nivel de compresión basado en cantidad de equipos
        num_equipos = len(equipos_empresa)
        if num_equipos <= 5:
            compresslevel = 9  # Máxima compresión para empresas pequeñas (más tiempo, menos espacio)
        elif num_equipos <= 15:
            compresslevel = 6  # Compresión balanceada
        else:
            compresslevel = 3  # Compresión rápida para empresas grandes (menos tiempo, más espacio)

        logger.info(f"Usando nivel de compresión {compresslevel} para {num_equipos} equipos")

        empresa_nombre = empresa.nombre

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=compresslevel) as zf:
            # Excel consolidado (importar desde views/reports)
            try:
                from .views.reports import _generate_consolidated_excel_content
                excel_consolidado = _generate_consolidated_excel_content(
                    equipos_empresa, proveedores_empresa, procedimientos_empresa
                )
                zf.writestr(f"{empresa_nombre}/Informe_Consolidado.xlsx", excel_consolidado)
            except ImportError as e:
                logger.error(f"Error importando función Excel: {e}")
                # Crear archivo de error temporal
                zf.writestr(f"{empresa_nombre}/ERROR_Excel.txt", f"Error generando Excel: {e}")

            # Carpeta de Procedimientos de la empresa
            procedimientos_count = procedimientos_empresa.count()
            logger.info(f"[DEBUG PROCEDIMIENTOS] Empresa {empresa_nombre} tiene {procedimientos_count} procedimientos")

            # Debug: Listar todos los procedimientos
            for p in procedimientos_empresa:
                logger.info(f"[DEBUG] Procedimiento encontrado: ID={p.id}, Código={p.codigo}, Tiene PDF={bool(p.documento_pdf)}")

            procedimientos_agregados = 0
            for idx, procedimiento in enumerate(procedimientos_empresa, 1):
                tiene_archivo = bool(procedimiento.documento_pdf)
                archivo_path = procedimiento.documento_pdf.name if procedimiento.documento_pdf else "No hay archivo"
                logger.info(f"Procedimiento {idx}: '{procedimiento.codigo}' - '{procedimiento.nombre}' - Archivo: {tiene_archivo} - Path: {archivo_path}")

                if procedimiento.documento_pdf:
                    try:
                        # Nombre descriptivo: CODIGO_Nombre.pdf
                        safe_codigo = procedimiento.codigo.replace('/', '_').replace('\\', '_')
                        safe_nombre = procedimiento.nombre.replace('/', '_').replace('\\', '_')[:50]  # Limitar longitud
                        filename = f"{safe_codigo}_{safe_nombre}.pdf"

                        # Usar función local de streaming
                        if stream_file_to_zip_local(zf, procedimiento.documento_pdf.name, f"{empresa_nombre}/Procedimientos/{filename}"):
                            procedimientos_agregados += 1
                            logger.info(f"✅ Procedimiento agregado: {filename}")
                        else:
                            logger.warning(f"❌ No se pudo agregar procedimiento: {filename}")
                    except Exception as e:
                        logger.error(f"❌ Error añadiendo procedimiento {procedimiento.codigo}: {e}")
                else:
                    logger.warning(f"⚠️ Procedimiento {procedimiento.codigo} sin documento PDF")

            # Crear carpeta vacía si no hay procedimientos para que aparezca en el ZIP
            if procedimientos_agregados == 0:
                zf.writestr(f"{empresa_nombre}/Procedimientos/README.txt", "No hay procedimientos con documentos PDF disponibles para esta empresa.")
                logger.info(f"📁 Carpeta /Procedimientos/ creada (vacía) para {empresa_nombre}")
            else:
                logger.info(f"✅ {procedimientos_agregados} procedimientos agregados a la carpeta /Procedimientos/")

            # Procesar cada equipo (lógica igual a producción)
            for idx, equipo in enumerate(equipos_empresa, 1):
                safe_codigo = equipo.codigo_interno.replace('/', '_').replace('\\', '_')
                equipo_folder = f"{empresa_nombre}/Equipos/{safe_codigo}"

                # Hoja de vida PDF
                try:
                    from .views.reports import _generate_equipment_hoja_vida_pdf_content
                    hoja_vida_pdf_content = _generate_equipment_hoja_vida_pdf_content(request, equipo)
                    zf.writestr(f"{equipo_folder}/Hoja_de_vida.pdf", hoja_vida_pdf_content)
                except ImportError as e:
                    logger.error(f"Error importando función PDF: {e}")
                    zf.writestr(f"{equipo_folder}/Hoja_de_vida_ERROR.txt", f"Error: {e}")
                except Exception as e:
                    logger.error(f"Error generando PDF para {equipo.codigo_interno}: {e}")
                    zf.writestr(f"{equipo_folder}/Hoja_de_vida_ERROR.txt", f"Error: {e}")

                # Documentos de actividades con subcarpetas organizadas
                # Calibraciones - TODOS los archivos en subcarpetas específicas
                calibraciones = equipo.calibraciones.all()
                cal_idx = 1
                conf_idx = 1
                int_idx = 1

                for cal in calibraciones:
                    # Documento de calibración principal -> Subcarpeta "Certificados_Calibracion"
                    if cal.documento_calibracion:
                        try:
                            if default_storage.exists(cal.documento_calibracion.name):
                                with default_storage.open(cal.documento_calibracion.name, 'rb') as f:
                                    content = f.read()
                                    filename = f"cal_{cal_idx}.pdf"
                                    zf.writestr(f"{equipo_folder}/Calibraciones/Certificados_Calibracion/{filename}", content)
                                    cal_idx += 1
                        except Exception as e:
                            logger.error(f"Error añadiendo certificado calibración: {e}")

                    # Confirmación metrológica PDF -> Subcarpeta "Confirmacion_Metrologica"
                    if cal.confirmacion_metrologica_pdf:
                        try:
                            if default_storage.exists(cal.confirmacion_metrologica_pdf.name):
                                with default_storage.open(cal.confirmacion_metrologica_pdf.name, 'rb') as f:
                                    content = f.read()
                                    filename = f"conf_{conf_idx}.pdf"
                                    zf.writestr(f"{equipo_folder}/Calibraciones/Confirmacion_Metrologica/{filename}", content)
                                    conf_idx += 1
                        except Exception as e:
                            logger.error(f"Error añadiendo confirmación metrológica: {e}")

                    # Intervalos de calibración PDF -> Subcarpeta "Intervalos_Calibracion"
                    if cal.intervalos_calibracion_pdf:
                        try:
                            if default_storage.exists(cal.intervalos_calibracion_pdf.name):
                                with default_storage.open(cal.intervalos_calibracion_pdf.name, 'rb') as f:
                                    content = f.read()
                                    filename = f"int_{int_idx}.pdf"
                                    zf.writestr(f"{equipo_folder}/Calibraciones/Intervalos_Calibracion/{filename}", content)
                                    int_idx += 1
                        except Exception as e:
                            logger.error(f"Error añadiendo intervalos calibración: {e}")

                # Mantenimientos
                mantenimientos = equipo.mantenimientos.all()
                for mant_idx, mant in enumerate(mantenimientos, 1):
                    if mant.documento_mantenimiento:
                        try:
                            if default_storage.exists(mant.documento_mantenimiento.name):
                                with default_storage.open(mant.documento_mantenimiento.name, 'rb') as f:
                                    content = f.read()
                                    filename = f"mant_{mant_idx}.pdf"
                                    zf.writestr(f"{equipo_folder}/Mantenimientos/{filename}", content)
                        except Exception as e:
                            logger.error(f"Error añadiendo archivo mantenimiento: {e}")

                # Comprobaciones
                comprobaciones = equipo.comprobaciones.all()
                for comp_idx, comp in enumerate(comprobaciones, 1):
                    if comp.documento_comprobacion:
                        try:
                            if default_storage.exists(comp.documento_comprobacion.name):
                                with default_storage.open(comp.documento_comprobacion.name, 'rb') as f:
                                    content = f.read()
                                    filename = f"comp_{comp_idx}.pdf"
                                    zf.writestr(f"{equipo_folder}/Comprobaciones/{filename}", content)
                        except Exception as e:
                            logger.error(f"Error añadiendo archivo comprobación: {e}")

                # Documentos del equipo
                equipment_docs = [
                    (equipo.archivo_compra_pdf, 'compra'),
                    (equipo.ficha_tecnica_pdf, 'ficha_tecnica'),
                    (equipo.manual_pdf, 'manual'),
                    (equipo.otros_documentos_pdf, 'otros_documentos')
                ]

                for doc_field, doc_type in equipment_docs:
                    if doc_field:
                        try:
                            if doc_field.name.lower().endswith('.pdf'):
                                nombre_descriptivo = f"{doc_type}.pdf"
                                if default_storage.exists(doc_field.name):
                                    with default_storage.open(doc_field.name, 'rb') as f:
                                        content = f.read()
                                        zf.writestr(f"{equipo_folder}/{nombre_descriptivo}", content)
                        except Exception as e:
                            logger.error(f"Error añadiendo documento del equipo: {e}")

                # LÓGICA NUEVA: Carpeta de Baja SOLO si equipo está dado de baja
                if equipo.estado == 'De Baja':
                    try:
                        baja_registro = equipo.baja_registro
                        if baja_registro and baja_registro.documento_baja:
                            if default_storage.exists(baja_registro.documento_baja.name):
                                with default_storage.open(baja_registro.documento_baja.name, 'rb') as f:
                                    content = f.read()
                                    filename = "documento_baja.pdf"
                                    zf.writestr(f"{equipo_folder}/Baja/{filename}", content)
                                    logger.info(f"Carpeta /Baja/ agregada para equipo dado de baja: {equipo.codigo_interno}")
                    except Exception as e:
                        logger.error(f"Error añadiendo documento de baja para {equipo.codigo_interno}: {e}")

        # Crear respuesta HTTP INMEDIATA (como producción)
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"SAM_Equipos_{empresa_nombre}_{timestamp}.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(zip_buffer.getvalue())

        # Log exitoso
        equipos_count = equipos_empresa.count()
        logger.info(f"ZIP INMEDIATO generado exitosamente para {empresa_nombre}: {equipos_count} equipos")

        return response

    except Exception as e:
        logger.error(f"Error en descarga INMEDIATA para empresa {empresa.nombre}: {e}", exc_info=True)
        # Si falla la descarga directa, usar cola como fallback
        return solicitar_zip_fallback(request, empresa, str(e))


def solicitar_zip_fallback(request, empresa, error_directo):
    """Fallback a cola si falla descarga directa"""
    logger.warning(f"Usando cola como fallback para {empresa.nombre}: {error_directo}")

    max_position = ZipRequest.objects.aggregate(max_pos=Max('position_in_queue'))['max_pos'] or 0

    zip_request = ZipRequest.objects.create(
        user=request.user,
        empresa=empresa,
        status='pending',
        position_in_queue=max_position + 1,
        parte_numero=1,
        expires_at=timezone.now() + timedelta(hours=6)
    )

    return JsonResponse({
        'status': 'queued_fallback',
        'request_id': zip_request.id,
        'message': f'Descarga directa falló, usando cola. Posición #{zip_request.get_current_position()}',
        'estimated_time': zip_request.get_estimated_wait_time(),
        'fallback_reason': error_directo[:100]
    })


def solicitar_zip_asincrono(request, empresa):
    """
    Nueva función para procesamiento asíncrono de ZIPs grandes.
    Mantiene la misma estructura ZIP pero sin bloquear la aplicación.
    """
    try:
        # Verificar si ya tiene una solicitud pendiente o procesándose
        existing = ZipRequest.objects.filter(
            user=request.user,
            status__in=['pending', 'processing']
        ).first()

        if existing:
            return JsonResponse({
                'status': 'already_pending',
                'request_id': existing.id,
                'position': existing.get_current_position(),
                'estimated_time': existing.get_estimated_wait_time(),
                'time_until_ready': existing.get_time_until_ready(),
                'detailed_message': existing.get_detailed_status_message(),
                'message': f'Ya tienes una solicitud: {existing.get_detailed_status_message()}'
            })

        # Obtener número de parte desde parámetros
        parte_numero = int(request.GET.get('parte', 1))

        # Obtener próxima posición en cola
        max_position = ZipRequest.objects.aggregate(
            max_pos=Max('position_in_queue')
        )['max_pos'] or 0

        # Crear nueva solicitud
        zip_request = ZipRequest.objects.create(
            user=request.user,
            empresa=empresa,
            status='pending',
            position_in_queue=max_position + 1,
            parte_numero=parte_numero,
            expires_at=timezone.now() + timedelta(hours=6)
        )

        # Agregar a la cola asíncrona para procesamiento en background
        from .async_zip_improved import add_zip_request_to_queue, start_async_processor

        # Asegurar que el procesador esté corriendo
        start_async_processor()

        # Agregar a cola asíncrona
        add_zip_request_to_queue(zip_request)

        equipos_count = empresa.equipos.count()
        tiempo_estimado = _calcular_tiempo_estimado_equipos(equipos_count)

        return JsonResponse({
            'status': 'queued_async',
            'request_id': zip_request.id,
            'position': zip_request.get_current_position(),
            'estimated_time': tiempo_estimado,
            'time_until_ready': zip_request.get_time_until_ready(),
            'detailed_message': zip_request.get_detailed_status_message(),
            'equipos_count': equipos_count,
            'empresa_name': empresa.nombre,
            'parte_numero': parte_numero,
            'message': f'Su archivo ZIP está siendo procesado en segundo plano. {tiempo_estimado} estimado.',
            'async_processing': True,
            'no_limits': True
        })

    except Exception as e:
        logger.error(f"Error en solicitar_zip_asincrono: {e}")
        return JsonResponse({
            'error': 'Error interno procesando solicitud ZIP',
            'details': str(e)
        }, status=500)


def _calcular_tiempo_estimado_equipos(equipos_count):
    """Calcula tiempo estimado basado en cantidad de equipos"""
    if equipos_count <= 50:
        return "2-4 minutos"
    elif equipos_count <= 100:
        return "5-8 minutos"
    elif equipos_count <= 200:
        return "8-12 minutos"
    elif equipos_count <= 500:
        return "12-20 minutos"
    else:
        return f"20-30 minutos (aprox. {equipos_count} equipos)"