# core/views/activities.py
# Views para gestión de actividades: calibraciones, mantenimientos y comprobaciones

from .base import *
import logging
from ..constants import ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_DE_BAJA

# Logger específico para activities
logger = logging.getLogger('activities')

# =============================================================================
# MAIN ACTIVITY VIEWS - CALIBRACIONES
# =============================================================================

@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.add_calibracion', raise_exception=True)
def añadir_calibracion(request, equipo_pk):
    """
    Añade una nueva calibración a un equipo específico.
    Incluye validación de almacenamiento y manejo de múltiples archivos PDF.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para añadir calibraciones a este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        logger.info(f"=== POST CALIBRACIÓN - Datos recibidos ===")
        logger.info(f"POST data: {dict(request.POST)}")
        logger.info(f"FILES data: {list(request.FILES.keys())}")
        logger.info(f"Empresa del equipo: {equipo.empresa.nombre}")

        form = CalibracionForm(request.POST, request.FILES, empresa=equipo.empresa)
        logger.info(f"Formulario inicializado para empresa: {equipo.empresa.nombre}")

        if form.is_valid():
            logger.info("Formulario es VÁLIDO - procesando...")
            try:
                # Validar límites de almacenamiento solo si hay archivos
                archivos_calibracion = [
                    'documento_calibracion',
                    'confirmacion_metrologica_pdf',
                    'intervalos_calibracion_pdf'
                ]

                # Verificar si hay algún archivo subido
                hay_archivos = any(campo in request.FILES for campo in archivos_calibracion)

                if hay_archivos:
                    total_file_size = _calculate_calibracion_files_size(request.FILES)
                    if total_file_size > 0:
                        _validate_storage_limit(equipo.empresa, total_file_size, form, equipo)

                # Crear calibración con archivos procesados
                calibracion = _create_calibracion_with_files(equipo, form, request.FILES)

                messages.success(request, 'Calibración añadida exitosamente.')
                logger.info(f"[SUCCESS] ÉXITO: Calibración creada ID: {calibracion.pk} para equipo {equipo.nombre}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except ValidationError as e:
                logger.error(f"[ERROR] ERROR DE VALIDACIÓN: {e}")
                messages.error(request, str(e))
                return _render_calibracion_form_with_error(request, equipo, CalibracionForm(empresa=equipo.empresa))
            except Exception as e:
                logger.error(f"[ERROR] ERROR GENERAL al guardar calibración: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                messages.error(request, f'Hubo un error al guardar la calibración: {e}')
        else:
            logger.error("[ERROR] FORMULARIO INVÁLIDO")
            logger.error(f"Errores del formulario: {form.errors}")
            logger.error(f"Errores no de campo: {form.non_field_errors()}")
            # Revisar proveedores disponibles
            proveedores = form.fields['proveedor'].queryset
            logger.error(f"Proveedores disponibles para {equipo.empresa.nombre}: {proveedores.count()}")
            for p in proveedores:
                logger.error(f"  - Proveedor: {p.nombre_empresa} ({p.tipo_servicio})")

    else:
        logger.info("GET request - mostrando formulario vacío")
        form = CalibracionForm(empresa=equipo.empresa)
        proveedores = form.fields['proveedor'].queryset
        logger.info(f"Proveedores disponibles para {equipo.empresa.nombre}: {proveedores.count()}")

    return render(request, 'core/añadir_calibracion.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Añadir Calibración para {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.change_calibracion', raise_exception=True)
def editar_calibracion(request, equipo_pk, pk):
    """
    Edita una calibración existente.
    Permite actualizar datos y archivos asociados.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    calibracion = get_object_or_404(Calibracion, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar esta calibración.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = CalibracionForm(request.POST, request.FILES, instance=calibracion, empresa=equipo.empresa)
        if form.is_valid():
            try:
                calibracion = form.save(commit=False)

                # Procesar archivos PDF si se subieron nuevos
                _process_calibracion_files(calibracion, request.FILES)
                calibracion.save()

                messages.success(request, 'Calibración actualizada exitosamente.')
                logger.info(f"Calibración actualizada ID: {calibracion.pk}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except Exception as e:
                logger.error(f"ERROR al actualizar calibración: {e}")
                messages.error(request, f'Hubo un error al actualizar la calibración: {e}')
    else:
        form = CalibracionForm(instance=calibracion, empresa=equipo.empresa)

    return render(request, 'core/editar_calibracion.html', {
        'form': form,
        'equipo': equipo,
        'calibracion': calibracion,
        'titulo_pagina': f'Editar Calibración para {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.delete_calibracion', raise_exception=True)
def eliminar_calibracion(request, equipo_pk, pk):
    """
    Elimina una calibración después de confirmación.
    Utiliza plantilla genérica de confirmación.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    calibracion = get_object_or_404(Calibracion, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar esta calibración.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            logger.info(f"Eliminando calibración ID: {calibracion.pk} del equipo {equipo.nombre}")
            calibracion.delete()
            messages.success(request, 'Calibración eliminada exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al eliminar la calibración: {e}')
            logger.error(f"Error al eliminar calibración {calibracion.pk}: {e}")
            return redirect('core:detalle_equipo', pk=equipo.pk)

    # Contexto para plantilla de confirmación
    context = {
        'object_name': f'la calibración de {equipo.nombre}',
        'return_url_name': 'core:detalle_equipo',
        'return_url_pk': equipo.pk,
        'titulo_pagina': f'Eliminar Calibración de {equipo.nombre}',
    }
    return render(request, 'core/confirmar_eliminacion.html', context)


# =============================================================================
# MAIN ACTIVITY VIEWS - MANTENIMIENTOS
# =============================================================================

@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.add_mantenimiento', raise_exception=True)
def añadir_mantenimiento(request, equipo_pk):
    """
    Añade un nuevo mantenimiento a un equipo específico.
    Incluye validación de almacenamiento y manejo de archivo PDF.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para añadir mantenimientos a este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        logger.info(f"=== POST MANTENIMIENTO - Datos recibidos ===")
        logger.info(f"POST data: {dict(request.POST)}")
        logger.info(f"FILES data: {list(request.FILES.keys())}")
        logger.info(f"Empresa del equipo: {equipo.empresa.nombre}")

        form = MantenimientoForm(request.POST, request.FILES, empresa=equipo.empresa)
        logger.info(f"Formulario inicializado para empresa: {equipo.empresa.nombre}")

        if form.is_valid():
            logger.info("Formulario es VÁLIDO - procesando...")
            try:
                # Validar límite de almacenamiento para TODOS los archivos
                for campo in ['documento_externo', 'analisis_interno', 'documento_mantenimiento']:
                    if campo in request.FILES:
                        archivo = request.FILES[campo]
                        _validate_single_file_storage(equipo.empresa, archivo, form, equipo, 'mantenimiento')

                # Crear mantenimiento con archivos procesados
                mantenimiento = _create_mantenimiento_with_files(equipo, form, request.FILES)

                messages.success(request, 'Mantenimiento añadido exitosamente.')
                logger.info(f"[SUCCESS] ÉXITO: Mantenimiento creado ID: {mantenimiento.pk} para equipo {equipo.nombre}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except ValidationError as e:
                logger.error(f"[ERROR] ERROR DE VALIDACIÓN MANTENIMIENTO: {e}")
                messages.error(request, str(e))
                return _render_mantenimiento_form_with_error(request, equipo, MantenimientoForm(empresa=equipo.empresa))
            except Exception as e:
                logger.error(f"[ERROR] ERROR GENERAL al guardar mantenimiento: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                messages.error(request, f'Hubo un error al guardar el mantenimiento: {e}')
        else:
            logger.error("[ERROR] FORMULARIO MANTENIMIENTO INVÁLIDO")
            logger.error(f"Errores del formulario: {form.errors}")
            logger.error(f"Errores no de campo: {form.non_field_errors()}")
            proveedores = form.fields['proveedor'].queryset
            logger.error(f"Proveedores disponibles para {equipo.empresa.nombre}: {proveedores.count()}")

    else:
        logger.info("GET request - mostrando formulario de mantenimiento vacío")
        form = MantenimientoForm(empresa=equipo.empresa)

    return render(request, 'core/añadir_mantenimiento.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Añadir Mantenimiento para {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.change_mantenimiento', raise_exception=True)
def editar_mantenimiento(request, equipo_pk, pk):
    """
    Edita un mantenimiento existente.
    Permite actualizar datos y archivo asociado.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar este mantenimiento.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = MantenimientoForm(request.POST, request.FILES, instance=mantenimiento, empresa=equipo.empresa)
        if form.is_valid():
            try:
                mantenimiento = form.save(commit=False)

                # Procesar TODOS los archivos si se subieron nuevos
                _process_single_file(mantenimiento, request.FILES, 'documento_externo')
                _process_single_file(mantenimiento, request.FILES, 'analisis_interno')
                _process_single_file(mantenimiento, request.FILES, 'documento_mantenimiento')
                mantenimiento.save()

                messages.success(request, 'Mantenimiento actualizado exitosamente.')
                logger.info(f"Mantenimiento actualizado ID: {mantenimiento.pk}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except Exception as e:
                logger.error(f"ERROR al actualizar mantenimiento: {e}")
                messages.error(request, f'Hubo un error al actualizar el mantenimiento: {e}')
    else:
        form = MantenimientoForm(instance=mantenimiento, empresa=equipo.empresa)

    return render(request, 'core/editar_mantenimiento.html', {
        'form': form,
        'equipo': equipo,
        'mantenimiento': mantenimiento,
        'titulo_pagina': f'Editar Mantenimiento para {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.delete_mantenimiento', raise_exception=True)
def eliminar_mantenimiento(request, equipo_pk, pk):
    """
    Elimina un mantenimiento después de confirmación.
    Utiliza plantilla genérica de confirmación.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar este mantenimiento.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            logger.info(f"Eliminando mantenimiento ID: {mantenimiento.pk} del equipo {equipo.nombre}")
            mantenimiento.delete()
            messages.success(request, 'Mantenimiento eliminado exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al eliminar el mantenimiento: {e}')
            logger.error(f"Error al eliminar mantenimiento {mantenimiento.pk}: {e}")
            return redirect('core:detalle_equipo', pk=equipo.pk)

    # Contexto para plantilla de confirmación
    context = {
        'object_name': f'el mantenimiento de {equipo.nombre}',
        'return_url_name': 'core:detalle_equipo',
        'return_url_pk': equipo.pk,
        'titulo_pagina': f'Eliminar Mantenimiento de {equipo.nombre}',
    }
    return render(request, 'core/confirmar_eliminacion.html', context)


@monitor_view
@access_check
@login_required
@permission_required('core.view_mantenimiento', raise_exception=True)
def detalle_mantenimiento(request, equipo_pk, pk):
    """
    Muestra los detalles de un mantenimiento específico.
    Incluye URL segura para documento PDF.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para ver este mantenimiento.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    # Generar URL segura del documento
    documento_mantenimiento_url = pdf_image_url(mantenimiento.documento_mantenimiento)

    context = {
        'equipo': equipo,
        'mantenimiento': mantenimiento,
        'documento_mantenimiento_url': documento_mantenimiento_url,
        'titulo_pagina': f'Detalle de Mantenimiento: {equipo.nombre}',
    }
    return render(request, 'core/detalle_mantenimiento.html', context)


# =============================================================================
# MAIN ACTIVITY VIEWS - COMPROBACIONES
# =============================================================================

@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.add_comprobacion', raise_exception=True)
def añadir_comprobacion(request, equipo_pk):
    """
    Añade una nueva comprobación a un equipo específico.
    Incluye validación de almacenamiento y manejo de archivo PDF.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para añadir comprobaciones a este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        logger.info(f"=== POST COMPROBACIÓN - Datos recibidos ===")
        logger.info(f"POST data: {dict(request.POST)}")
        logger.info(f"FILES data: {list(request.FILES.keys())}")
        logger.info(f"Empresa del equipo: {equipo.empresa.nombre}")

        form = ComprobacionForm(request.POST, request.FILES, empresa=equipo.empresa)
        logger.info(f"Formulario inicializado para empresa: {equipo.empresa.nombre}")

        if form.is_valid():
            logger.info("Formulario es VÁLIDO - procesando...")
            try:
                # Validar límite de almacenamiento para TODOS los archivos
                for campo in ['documento_externo', 'analisis_interno', 'documento_comprobacion']:
                    if campo in request.FILES:
                        archivo = request.FILES[campo]
                        _validate_single_file_storage(equipo.empresa, archivo, form, equipo, 'comprobación')

                # Crear comprobación con archivos procesados
                comprobacion = _create_comprobacion_with_files(equipo, form, request.FILES)

                messages.success(request, 'Comprobación añadida exitosamente.')
                logger.info(f"[SUCCESS] ÉXITO: Comprobación creada ID: {comprobacion.pk} para equipo {equipo.nombre}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except ValidationError as e:
                logger.error(f"[ERROR] ERROR DE VALIDACIÓN COMPROBACIÓN: {e}")
                messages.error(request, str(e))
                return _render_comprobacion_form_with_error(request, equipo, ComprobacionForm(empresa=equipo.empresa))
            except Exception as e:
                logger.error(f"[ERROR] ERROR GENERAL al guardar comprobación: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                messages.error(request, f'Hubo un error al guardar la comprobación: {e}')
        else:
            logger.error("[ERROR] FORMULARIO COMPROBACIÓN INVÁLIDO")
            logger.error(f"Errores del formulario: {form.errors}")
            logger.error(f"Errores no de campo: {form.non_field_errors()}")
            proveedores = form.fields['proveedor'].queryset
            logger.error(f"Proveedores disponibles para {equipo.empresa.nombre}: {proveedores.count()}")

    else:
        logger.info("GET request - mostrando formulario de comprobación vacío")
        form = ComprobacionForm(empresa=equipo.empresa)

    return render(request, 'core/añadir_comprobacion.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Añadir Comprobación para {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.change_comprobacion', raise_exception=True)
def editar_comprobacion(request, equipo_pk, pk):
    """
    Edita una comprobación existente.
    Permite actualizar datos y archivo asociado.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    comprobacion = get_object_or_404(Comprobacion, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar esta comprobación.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = ComprobacionForm(request.POST, request.FILES, instance=comprobacion, empresa=equipo.empresa)
        if form.is_valid():
            try:
                comprobacion = form.save(commit=False)

                # Procesar TODOS los archivos si se subieron nuevos
                _process_single_file(comprobacion, request.FILES, 'documento_externo')
                _process_single_file(comprobacion, request.FILES, 'analisis_interno')
                _process_single_file(comprobacion, request.FILES, 'documento_comprobacion')
                comprobacion.save()

                messages.success(request, 'Comprobación actualizada exitosamente.')
                logger.info(f"Comprobación actualizada ID: {comprobacion.pk}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except Exception as e:
                logger.error(f"ERROR al actualizar comprobación: {e}")
                messages.error(request, f'Hubo un error al actualizar la comprobación: {e}')
    else:
        form = ComprobacionForm(instance=comprobacion, empresa=equipo.empresa)

    return render(request, 'core/editar_comprobacion.html', {
        'form': form,
        'equipo': equipo,
        'comprobacion': comprobacion,
        'titulo_pagina': f'Editar Comprobación para {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.delete_comprobacion', raise_exception=True)
def eliminar_comprobacion(request, equipo_pk, pk):
    """
    Elimina una comprobación después de confirmación.
    Utiliza plantilla genérica de confirmación.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    comprobacion = get_object_or_404(Comprobacion, pk=pk, equipo=equipo)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar esta comprobación.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            logger.info(f"Eliminando comprobación ID: {comprobacion.pk} del equipo {equipo.nombre}")
            comprobacion.delete()
            messages.success(request, 'Comprobación eliminada exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al eliminar la comprobación: {e}')
            logger.error(f"Error al eliminar comprobación {comprobacion.pk}: {e}")
            return redirect('core:detalle_equipo', pk=equipo.pk)

    # Contexto para plantilla de confirmación
    context = {
        'object_name': f'la comprobación de {equipo.nombre}',
        'return_url_name': 'core:detalle_equipo',
        'return_url_pk': equipo.pk,
        'titulo_pagina': f'Eliminar Comprobación de {equipo.nombre}',
    }
    return render(request, 'core/confirmar_eliminacion.html', context)


# =============================================================================
# HELPER FUNCTIONS - FILE HANDLING
# =============================================================================

def _calculate_calibracion_files_size(files):
    """Calcula el tamaño total de archivos de calibración."""
    total_file_size = 0
    archivos_calibracion = ['documento_calibracion', 'confirmacion_metrologica_pdf', 'intervalos_calibracion_pdf']

    for campo in archivos_calibracion:
        if campo in files:
            archivo = files[campo]
            total_file_size += archivo.size

    return total_file_size


def _validate_storage_limit(empresa, file_size, form, equipo):
    """Valida límites de almacenamiento para archivos."""
    try:
        StorageLimitValidator.validate_storage_limit(empresa, file_size)
    except ValidationError as e:
        raise ValidationError(str(e))


def _validate_single_file_storage(empresa, archivo, form, equipo, tipo_actividad):
    """Valida límite de almacenamiento para un solo archivo."""
    try:
        StorageLimitValidator.validate_storage_limit(empresa, archivo.size)
    except ValidationError as e:
        raise ValidationError(str(e))


def _process_calibracion_files(calibracion, files):
    """Procesa y guarda archivos de calibración."""
    archivos = [
        'documento_calibracion',
        'confirmacion_metrologica_pdf',
        'intervalos_calibracion_pdf',
    ]

    for campo in archivos:
        if campo in files:
            archivo_subido = files[campo]
            nombre_archivo = sanitize_filename(archivo_subido.name)
            ruta_final = f"pdfs/{nombre_archivo}"
            default_storage.save(ruta_final, archivo_subido)
            setattr(calibracion, campo, ruta_final)


def _process_single_file(instance, files, field_name):
    """Procesa y guarda un solo archivo PDF."""
    if field_name in files:
        archivo_subido = files[field_name]
        nombre_archivo = sanitize_filename(archivo_subido.name)
        ruta_final = f"pdfs/{nombre_archivo}"
        default_storage.save(ruta_final, archivo_subido)
        setattr(instance, field_name, ruta_final)


def _create_calibracion_with_files(equipo, form, files):
    """Crea una calibración con sus archivos procesados."""
    calibracion = Calibracion(
        equipo=equipo,
        fecha_calibracion=form.cleaned_data['fecha_calibracion'],
        proveedor=form.cleaned_data['proveedor'],
        nombre_proveedor=form.cleaned_data['nombre_proveedor'],
        resultado=form.cleaned_data['resultado'],
        numero_certificado=form.cleaned_data['numero_certificado'],
        observaciones=form.cleaned_data['observaciones'],
    )

    # Primero guardamos el objeto para obtener un ID
    calibracion.save()

    # Luego procesamos los archivos
    _process_calibracion_files(calibracion, files)

    # Guardamos nuevamente para actualizar los campos de archivo
    calibracion.save()
    return calibracion


def _create_mantenimiento_with_files(equipo, form, files):
    """Crea un mantenimiento con sus archivos procesados."""
    mantenimiento = Mantenimiento(
        equipo=equipo,
        fecha_mantenimiento=form.cleaned_data['fecha_mantenimiento'],
        tipo_mantenimiento=form.cleaned_data['tipo_mantenimiento'],
        proveedor=form.cleaned_data['proveedor'],
        nombre_proveedor=form.cleaned_data['nombre_proveedor'],
        responsable=form.cleaned_data['responsable'],
        costo=form.cleaned_data['costo'],
        descripcion=form.cleaned_data['descripcion'],
        observaciones=form.cleaned_data['observaciones'],
    )

    # Primero guardamos el objeto para obtener un ID
    mantenimiento.save()

    # Luego procesamos TODOS los archivos
    _process_single_file(mantenimiento, files, 'documento_externo')
    _process_single_file(mantenimiento, files, 'analisis_interno')
    _process_single_file(mantenimiento, files, 'documento_mantenimiento')

    # Guardamos nuevamente para actualizar los campos de archivo
    mantenimiento.save()
    return mantenimiento


def _create_comprobacion_with_files(equipo, form, files):
    """Crea una comprobación con sus archivos procesados."""
    comprobacion = Comprobacion(
        equipo=equipo,
        fecha_comprobacion=form.cleaned_data['fecha_comprobacion'],
        proveedor=form.cleaned_data['proveedor'],
        nombre_proveedor=form.cleaned_data['nombre_proveedor'],
        responsable=form.cleaned_data['responsable'],
        resultado=form.cleaned_data['resultado'],
        observaciones=form.cleaned_data['observaciones'],
    )

    # Primero guardamos el objeto para obtener un ID
    comprobacion.save()

    # Luego procesamos TODOS los archivos
    _process_single_file(comprobacion, files, 'documento_externo')
    _process_single_file(comprobacion, files, 'analisis_interno')
    _process_single_file(comprobacion, files, 'documento_comprobacion')

    # Guardamos nuevamente para actualizar los campos de archivo
    comprobacion.save()
    return comprobacion


# =============================================================================
# HELPER FUNCTIONS - ERROR HANDLING
# =============================================================================

def _render_calibracion_form_with_error(request, equipo, form):
    """Renderiza formulario de calibración con error."""
    return render(request, 'core/añadir_calibracion.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Añadir Calibración a {equipo.nombre}',
    })


def _render_mantenimiento_form_with_error(request, equipo, form):
    """Renderiza formulario de mantenimiento con error."""
    return render(request, 'core/añadir_mantenimiento.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Añadir Mantenimiento a {equipo.nombre}',
    })


def _render_comprobacion_form_with_error(request, equipo, form):
    """Renderiza formulario de comprobación con error."""
    return render(request, 'core/añadir_comprobacion.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Añadir Comprobación a {equipo.nombre}',
    })


# =============================================================================
# EQUIPMENT STATUS MANAGEMENT VIEWS
# =============================================================================

@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.add_bajaequipo', raise_exception=True)
@require_http_methods(["GET", "POST"])
def dar_baja_equipo(request, equipo_pk):
    """
    Da de baja un equipo de forma permanente.
    Crea un registro de BajaEquipo con documentación.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para dar de baja este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    # Verificar si ya está dado de baja o ya tiene un registro de baja
    if equipo.estado == ESTADO_DE_BAJA:
        messages.warning(request, f'El equipo "{equipo.nombre}" ya está dado de baja.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    # Verificar si existe un registro de baja previo (problema de reactivación incorrecta)
    try:
        existing_baja = BajaEquipo.objects.get(equipo=equipo)
        if equipo.estado != 'De Baja':
            # Inconsistencia: existe registro de baja pero equipo no está marcado como dado de baja
            # Auto-corregir eliminando el registro de baja previo
            existing_baja.delete()
            messages.info(request, f'Se detectó un registro de baja previo inconsistente para "{equipo.nombre}". Se ha corregido automáticamente.')
            logger.info(f"Auto-corrección: Eliminado registro BajaEquipo inconsistente para equipo {equipo.pk}")
            # Continuar con el proceso normal de dar de baja
        else:
            # Estado y registro coinciden, equipo realmente está dado de baja
            messages.warning(request, f'El equipo "{equipo.nombre}" ya está dado de baja.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
    except BajaEquipo.DoesNotExist:
        pass  # No existe registro previo, proceder normalmente

    if request.method == 'POST':
        form = BajaEquipoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Crear registro de baja
                baja_registro = BajaEquipo(
                    equipo=equipo,
                    fecha_baja=form.cleaned_data['fecha_baja'],
                    razon_baja=form.cleaned_data['razon_baja'],
                    observaciones=form.cleaned_data['observaciones'],
                    dado_de_baja_por=request.user,
                )

                # Procesar archivo de documentación si existe
                if 'documento_baja' in request.FILES:
                    archivo_subido = request.FILES['documento_baja']
                    nombre_archivo = sanitize_filename(archivo_subido.name)
                    subir_archivo(nombre_archivo, archivo_subido)
                    baja_registro.documento_baja = f"pdfs/{nombre_archivo}"

                baja_registro.save()

                messages.success(request, f'Equipo "{equipo.nombre}" dado de baja exitosamente.')
                logger.info(f"Equipo dado de baja ID: {equipo.pk} por usuario {request.user.username}")
                return redirect('core:detalle_equipo', pk=equipo.pk)

            except Exception as e:
                messages.error(request, f'Hubo un error al dar de baja el equipo: {e}')
                logger.error(f"Error al dar de baja equipo {equipo.pk}: {e}")
                return render(request, 'core/dar_baja_equipo.html', {
                    'form': form,
                    'equipo': equipo,
                    'titulo_pagina': f'Dar de Baja Equipo: {equipo.nombre}'
                })
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario de baja.')
    else:
        form = BajaEquipoForm()

    return render(request, 'core/dar_baja_equipo.html', {
        'form': form,
        'equipo': equipo,
        'titulo_pagina': f'Dar de Baja Equipo: {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.change_equipo', raise_exception=True)
@require_http_methods(["GET", "POST"])
def inactivar_equipo(request, equipo_pk):
    """
    Inactiva un equipo temporalmente (cambia estado a 'Inactivo').
    Las próximas fechas se ponen en None hasta reactivación.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para inactivar este equipo.')
        return redirect('core:detalle_equipo', pk=equipo_pk)

    # Verificar estado actual
    if equipo.estado == ESTADO_INACTIVO:
        messages.info(request, f'El equipo "{equipo.nombre}" ya está inactivo.')
        return redirect('core:detalle_equipo', pk=equipo_pk)
    elif equipo.estado == ESTADO_DE_BAJA:
        messages.error(request, f'El equipo "{equipo.nombre}" ha sido dado de baja de forma permanente y no puede ser inactivado.')
        return redirect('core:detalle_equipo', pk=equipo_pk)

    if request.method == 'POST':
        # Cambiar estado a inactivo y limpiar próximas fechas
        equipo.estado = ESTADO_INACTIVO
        equipo.proxima_calibracion = None
        equipo.proximo_mantenimiento = None
        equipo.proxima_comprobacion = None
        equipo.save(update_fields=['estado', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])

        messages.success(request, f'Equipo "{equipo.nombre}" inactivado exitosamente.')
        logger.info(f"Equipo inactivado ID: {equipo.pk} por usuario {request.user.username}")
        return redirect('core:detalle_equipo', pk=equipo_pk)

    # Mostrar página de confirmación
    return render(request, 'core/confirmar_inactivacion.html', {
        'equipo': equipo,
        'titulo_pagina': f'Inactivar Equipo: {equipo.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.change_equipo', raise_exception=True)
@require_http_methods(["GET", "POST"])
def activar_equipo(request, equipo_pk):
    """
    Activa un equipo (cambia estado a 'Activo' desde 'Inactivo' o 'De Baja').
    Recalcula próximas fechas y elimina registro de baja si aplica.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    # Verificar permisos de empresa
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para activar este equipo.')
        return redirect('core:detalle_equipo', pk=equipo_pk)

    # Verificar estado actual
    if equipo.estado == ESTADO_ACTIVO:
        messages.info(request, f'El equipo "{equipo.nombre}" ya está activo.')
        return redirect('core:detalle_equipo', pk=equipo_pk)

    if request.method == 'POST':
        try:
            if equipo.estado == ESTADO_DE_BAJA:
                # Eliminar registro de baja y activar
                try:
                    baja_registro = BajaEquipo.objects.get(equipo=equipo)
                    baja_registro.delete()  # Esto activará el equipo a través de señal post_delete
                    messages.success(request, f'Equipo "{equipo.nombre}" activado exitosamente y registro de baja eliminado.')
                    logger.info(f"Equipo reactivado desde baja ID: {equipo.pk} por usuario {request.user.username}")
                except BajaEquipo.DoesNotExist:
                    equipo.estado = ESTADO_ACTIVO
                    equipo.save(update_fields=['estado'])
                    messages.warning(request, f'Equipo "{equipo.nombre}" activado. No se encontró registro de baja asociado.')

            elif equipo.estado == ESTADO_INACTIVO:
                # Activar y recalcular próximas fechas
                equipo.estado = ESTADO_ACTIVO
                equipo.calcular_proxima_calibracion()
                equipo.calcular_proximo_mantenimiento()
                equipo.calcular_proxima_comprobacion()
                equipo.save()

                messages.success(request, f'Equipo "{equipo.nombre}" activado exitosamente.')
                logger.info(f"Equipo reactivado desde inactivo ID: {equipo.pk} por usuario {request.user.username}")

        except Exception as e:
            messages.error(request, f'Error al activar el equipo: {e}')
            logger.error(f"Error al activar equipo {equipo.pk}: {e}")
            return redirect('core:detalle_equipo', pk=equipo.pk)

        return redirect('core:detalle_equipo', pk=equipo.pk)

    # Mostrar página de confirmación
    return render(request, 'core/confirmar_activacion.html', {
        'equipo': equipo,
        'titulo_pagina': f'Activar Equipo: {equipo.nombre}'
    })


# ===== VISTA DE ACTIVIDADES PROGRAMADAS =====

@monitor_view
@access_check
@login_required
def programmed_activities_list(request):
    """
    Lists all programmed activities.
    """
    from datetime import date
    from django.utils import timezone
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

    today = timezone.localdate()
    scheduled_activities = []

    equipos_base_query = Equipo.objects.all()
    if not request.user.is_superuser and request.user.empresa:
        equipos_base_query = equipos_base_query.filter(empresa=request.user.empresa)
    elif not request.user.is_superuser and not request.user.empresa:
        equipos_base_query = Equipo.objects.none()

    # Excluir equipos "De Baja" y "Inactivo" para esta lista
    equipos_base_query = equipos_base_query.exclude(estado__in=[ESTADO_DE_BAJA, ESTADO_INACTIVO])

    calibraciones_query = equipos_base_query.filter(
        proxima_calibracion__isnull=False
    ).order_by('proxima_calibracion')

    for equipo in calibraciones_query:
        if equipo.proxima_calibracion:
            days_remaining = (equipo.proxima_calibracion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Calibración',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_calibracion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    mantenimientos_query = equipos_base_query.filter(
        proximo_mantenimiento__isnull=False
    ).order_by('proximo_mantenimiento')

    for equipo in mantenimientos_query:
        if equipo.proximo_mantenimiento:
            days_remaining = (equipo.proximo_mantenimiento - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Mantenimiento',
                'equipo': equipo,
                'fecha_programada': equipo.proximo_mantenimiento,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    comprobaciones_query = equipos_base_query.filter(
        proxima_comprobacion__isnull=False
    ).order_by('proxima_comprobacion')

    for equipo in comprobaciones_query:
        if equipo.proxima_comprobacion:
            days_remaining = (equipo.proxima_comprobacion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Comprobación',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_comprobacion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    scheduled_activities.sort(key=lambda x: x['fecha_programada'] if x['fecha_programada'] else date.max)

    paginator = Paginator(scheduled_activities, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'core/programmed_activities_list.html', {'page_obj': page_obj, 'titulo_pagina': 'Actividades Programadas'})