# core/views/companies.py
# Views para gestión de empresas, ubicaciones y planes

from .base import *

# =============================================================================
# MAIN COMPANY VIEWS
# =============================================================================

@monitor_view
@access_check
@login_required
@superuser_required
def listar_empresas(request):
    """
    Lista todas las empresas con filtrado y paginación (solo superusuarios).
    Los usuarios normales solo ven su propia empresa.
    """
    query = request.GET.get('q')
    empresas_list = OptimizedQueries.get_empresas_with_stats()

    # Filtrar por empresa para usuarios normales
    if not request.user.is_superuser:
        empresas_list = empresas_list.filter(pk=request.user.empresa.pk)

    # Aplicar filtro de búsqueda si existe
    if query:
        empresas_list = empresas_list.filter(
            Q(nombre__icontains=query) |
            Q(nit__icontains=query) |
            Q(direccion__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query)
        )

    # Paginación optimizada
    paginator = Paginator(empresas_list, 10)
    page_number = request.GET.get('page')
    try:
        empresas = paginator.page(page_number)
    except PageNotAnInteger:
        empresas = paginator.page(1)
    except EmptyPage:
        empresas = paginator.page(paginator.num_pages)

    return render(request, 'core/listar_empresas.html', {
        'empresas': empresas,
        'query': query,
        'titulo_pagina': 'Listado de Empresas'
    })


@monitor_view
@access_check
@login_required
@superuser_required
def añadir_empresa(request):
    """
    Maneja la adición de una nueva empresa (solo superusuarios).
    Incluye procesamiento de logo de empresa.
    """
    if request.method == 'POST':
        formulario = EmpresaForm(request.POST)
        if formulario.is_valid():
            try:
                empresa = formulario.save(commit=False)

                # CONFIGURAR PLAN TRIAL AUTOMÁTICAMENTE PARA NUEVAS EMPRESAS
                empresa.es_periodo_prueba = True
                empresa.fecha_inicio_plan = timezone.now().date()
                empresa.duracion_prueba_dias = 30  # 1 mes de trial
                empresa.limite_equipos_empresa = 50  # 50 equipos en trial
                empresa.limite_almacenamiento_mb = 500  # 500MB para trial
                empresa.estado_suscripcion = 'Activo'

                # IMPORTANTE: Marcar que el plan fue configurado manualmente
                # para evitar que el método save() del modelo lo sobrescriba
                empresa._plan_set_manually = True

                # Procesar logo de empresa si se subió
                if 'logo_empresa' in request.FILES:
                    _process_company_logo(empresa, request.FILES['logo_empresa'])

                empresa.save()
                messages.success(request, f'Empresa añadida exitosamente con plan TRIAL (30 días, 50 equipos).')
                logger.info(f"Empresa creada con plan TRIAL: {empresa.nombre} (ID: {empresa.pk}) por {request.user.username}")
                return redirect('core:listar_empresas')

            except Exception as e:
                messages.error(request, f'Hubo un error al añadir la empresa: {e}. Revisa el log para más detalles.')
                logger.error(f"Error al añadir empresa: {e}")
        else:
            messages.error(request, 'Hubo un error al añadir la empresa. Por favor, revisa los datos.')
    else:
        formulario = EmpresaForm()

    return render(request, 'core/añadir_empresa.html', {
        'formulario': formulario,
        'titulo_pagina': 'Añadir Nueva Empresa'
    })


@monitor_view
@access_check
@login_required
def detalle_empresa(request, pk):
    """
    Muestra los detalles de una empresa específica con sus equipos y usuarios asociados.
    Solo superusuarios o usuarios de la misma empresa pueden acceder.
    """
    empresa = get_object_or_404(Empresa, pk=pk)

    # Verificar permisos de acceso
    if not request.user.is_superuser and (not request.user.empresa or request.user.empresa.pk != empresa.pk):
        messages.error(request, 'No tienes permisos para ver esta empresa.')
        return redirect('core:access_denied')

    # Obtener equipos y usuarios asociados usando queries optimizadas
    equipos_asociados = OptimizedQueries.get_equipos_optimized(empresa=empresa).order_by('codigo_interno')
    usuarios_empresa = CustomUser.objects.filter(empresa=empresa).order_by('username')

    # Obtener estadísticas de la empresa
    equipos_count = equipos_asociados.count()
    limite_equipos = empresa.get_limite_equipos()
    storage_usado = empresa.get_total_storage_used_mb()  # Ya en MB
    limite_storage = empresa.get_limite_almacenamiento()

    context = {
        'empresa': empresa,
        'equipos_asociados': equipos_asociados,
        'usuarios_empresa': usuarios_empresa,
        'estadisticas': {
            'equipos_count': equipos_count,
            'limite_equipos': limite_equipos,
            'storage_usado': storage_usado,
            'limite_storage': limite_storage,
            'estado_suscripcion': empresa.get_estado_suscripcion_display(),
        },
        'titulo_pagina': f'Detalle de Empresa: {empresa.nombre}'
    }
    return render(request, 'core/detalle_empresa.html', context)


@monitor_view
@access_check
@login_required
@superuser_required
def editar_empresa(request, pk):
    """
    Maneja la edición de una empresa existente (solo superusuarios).
    Incluye actualización de logo de empresa.
    """
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            try:
                empresa = form.save(commit=False)

                # Procesar nuevo logo si se subió
                if 'logo_empresa' in request.FILES:
                    _process_company_logo(empresa, request.FILES['logo_empresa'])

                empresa.save()
                messages.success(request, 'Empresa actualizada exitosamente.')
                logger.info(f"Empresa actualizada: {empresa.nombre} (ID: {empresa.pk}) por {request.user.username}")
                return redirect('core:detalle_empresa', pk=empresa.pk)

            except Exception as e:
                messages.error(request, f'Error al actualizar la empresa: {e}')
                logger.error(f"Error al editar empresa {empresa.pk}: {e}")
        else:
            messages.error(request, 'Hubo un error al actualizar la empresa. Por favor, revisa los datos.')
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, 'core/editar_empresa.html', {
        'form': form,
        'empresa': empresa,
        'titulo_pagina': f'Editar Empresa: {empresa.nombre}'
    })


@monitor_view
@access_check
@login_required
@superuser_required
def eliminar_empresa(request, pk):
    """
    Maneja la eliminación de una empresa (solo superusuarios).
    Utiliza plantilla genérica de confirmación.
    """
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        try:
            empresa_nombre = empresa.nombre
            logger.info(f"Eliminando empresa: {empresa_nombre} (ID: {empresa.pk}) por {request.user.username}")
            empresa.delete()
            messages.success(request, f'Empresa "{empresa_nombre}" eliminada exitosamente.')
            return redirect('core:listar_empresas')
        except Exception as e:
            messages.error(request, f'Error al eliminar la empresa: {e}')
            logger.error(f"Error al eliminar empresa {empresa.pk}: {e}")
            return redirect('core:listar_empresas')

    # Contexto para plantilla de confirmación
    context = {
        'object_name': f'la empresa "{empresa.nombre}"',
        'return_url_name': 'core:listar_empresas',
        'return_url_pk': None,
        'titulo_pagina': f'Eliminar Empresa: {empresa.nombre}',
    }
    return render(request, 'core/confirmar_eliminacion.html', context)


# =============================================================================
# COMPANY USER MANAGEMENT
# =============================================================================

@monitor_view
@access_check
@login_required
@permission_required('core.change_empresa', raise_exception=True)
def añadir_usuario_a_empresa(request, empresa_pk):
    """
    Vista para añadir un usuario existente a una empresa específica.
    Solo superusuarios o usuarios con permiso para cambiar empresas pueden acceder.
    """
    empresa = get_object_or_404(Empresa, pk=empresa_pk)
    titulo_pagina = f"Añadir Usuario a {empresa.nombre}"

    # Verificar permisos: superusuario o usuario de la misma empresa
    if not request.user.is_superuser and request.user.empresa != empresa:
        messages.error(request, 'No tienes permiso para añadir usuarios a esta empresa.')
        return redirect('core:detalle_empresa', pk=empresa.pk)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                user_to_add = CustomUser.objects.get(pk=user_id)

                # Verificar si el usuario ya está en otra empresa
                if user_to_add.empresa and user_to_add.empresa != empresa:
                    messages.warning(
                        request,
                        f"El usuario '{user_to_add.username}' ya está asociado a la empresa "
                        f"'{user_to_add.empresa.nombre}'. Se ha reasignado a '{empresa.nombre}'."
                    )

                user_to_add.empresa = empresa
                user_to_add.save()

                messages.success(request, f"Usuario '{user_to_add.username}' añadido exitosamente a '{empresa.nombre}'.")
                logger.info(f"Usuario {user_to_add.username} añadido a empresa {empresa.nombre} por {request.user.username}")
                return redirect('core:detalle_empresa', pk=empresa.pk)

            except CustomUser.DoesNotExist:
                messages.error(request, "El usuario seleccionado no existe.")
            except Exception as e:
                messages.error(request, f"Error al añadir usuario: {e}")
                logger.error(f"Error en añadir_usuario_a_empresa: {e}")
        else:
            messages.error(request, "Por favor, selecciona un usuario.")

    # Obtener usuarios disponibles (que no están en esta empresa)
    users_available = CustomUser.objects.filter(is_superuser=False).exclude(empresa=empresa)

    context = {
        'empresa': empresa,
        'users_available': users_available,
        'titulo_pagina': titulo_pagina,
    }
    return render(request, 'core/añadir_usuario_a_empresa.html', context)


# =============================================================================
# COMPANY PLAN MANAGEMENT
# =============================================================================

@monitor_view
@access_check
@login_required
@superuser_required
def activar_plan_pagado(request, empresa_id):
    """
    Vista para que superusuarios activen planes pagados para empresas.
    Permite configurar límites de equipos, almacenamiento y duración.
    """
    empresa = get_object_or_404(Empresa, id=empresa_id)

    if request.method == 'POST':
        try:
            # Obtener parámetros del plan
            limite_equipos = int(request.POST.get('limite_equipos', 0))
            limite_almacenamiento_mb = int(request.POST.get('limite_almacenamiento_mb', 0))
            duracion_meses = request.POST.get('duracion_meses')
            duracion_meses = int(duracion_meses) if duracion_meses else None

            # Obtener nuevos parámetros financieros
            tarifa_mensual_sam = request.POST.get('tarifa_mensual_sam')
            modalidad_pago = request.POST.get('modalidad_pago', 'MENSUAL')
            valor_pago_acordado = request.POST.get('valor_pago_acordado')

            # Validar parámetros
            if limite_equipos <= 0 or limite_almacenamiento_mb <= 0:
                messages.error(request, 'Los límites deben ser mayores a 0')
                return redirect('core:detalle_empresa', pk=empresa_id)

            # Activar plan pagado usando el método del modelo
            empresa.activar_plan_pagado(
                limite_equipos=limite_equipos,
                limite_almacenamiento_mb=limite_almacenamiento_mb,
                duracion_meses=duracion_meses
            )

            # Actualizar información financiera si se proporciona
            if tarifa_mensual_sam:
                empresa.tarifa_mensual_sam = float(tarifa_mensual_sam)

            empresa.modalidad_pago = modalidad_pago

            if valor_pago_acordado:
                empresa.valor_pago_acordado = float(valor_pago_acordado)

            empresa.save()

            # Mensaje de éxito detallado
            duracion_texto = f"Duración: {duracion_meses} meses" if duracion_meses else "Sin límite de tiempo"
            messages.success(
                request,
                f'Plan pagado activado exitosamente para {empresa.nombre}. '
                f'Límites: {limite_equipos} equipos, {limite_almacenamiento_mb}MB. '
                f'{duracion_texto}'
            )

            logger.info(f"Plan pagado activado para empresa {empresa.nombre} (ID: {empresa.pk}) por {request.user.username}")

        except ValueError as e:
            messages.error(request, f'Error en los datos proporcionados: {str(e)}')
            logger.error(f"Error de validación en activar_plan_pagado: {e}")
        except Exception as e:
            messages.error(request, f'Error activando plan pagado: {str(e)}')
            logger.error(f"Error al activar plan pagado para empresa {empresa_id}: {e}")

        return redirect('core:detalle_empresa', pk=empresa_id)

    return redirect('core:detalle_empresa', pk=empresa_id)


# =============================================================================
# COMPANY FORMAT MANAGEMENT
# =============================================================================

@monitor_view
@access_check
@login_required
@require_POST
@csrf_exempt
def update_empresa_formato(request):
    """
    Actualiza la información de formato de empresa via AJAX POST.
    Maneja tanto superusuarios como usuarios regulares.
    """
    # Determinar qué empresa actualizar
    company_to_update = None

    if request.user.is_superuser:
        # Superusuario puede actualizar cualquier empresa si se proporciona empresa_id
        empresa_id = request.POST.get('empresa_id')
        if empresa_id:
            try:
                company_to_update = Empresa.objects.get(pk=empresa_id)
            except Empresa.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Empresa no encontrada.'}, status=404)
        else:
            return JsonResponse({'status': 'error', 'message': 'ID de empresa requerido para superusuario.'}, status=400)
    elif request.user.empresa:
        # Usuario regular solo puede actualizar su propia empresa
        company_to_update = request.user.empresa
    else:
        return JsonResponse({'status': 'error', 'message': 'Usuario no asociado a ninguna empresa.'}, status=403)

    # Procesar el formulario
    form = EmpresaFormatoForm(request.POST, instance=company_to_update)
    if form.is_valid():
        form.save()
        logger.info(f"Formato actualizado para empresa {company_to_update.nombre} por {request.user.username}")

        return JsonResponse({
            'status': 'success',
            'message': 'Información de formato actualizada.',
            'version': company_to_update.formato_version_empresa,
            'fecha_version': company_to_update.formato_fecha_version_empresa.strftime('%d/%m/%Y') if company_to_update.formato_fecha_version_empresa else 'N/A',
            'codificacion': company_to_update.formato_codificacion_empresa,
        })
    else:
        errors = form.errors.as_json()
        return JsonResponse({'status': 'error', 'message': 'Errores de validación.', 'errors': errors}, status=400)


@monitor_view
@access_check
@login_required
@require_http_methods(["GET", "POST"])
def editar_empresa_formato(request, pk):
    """
    Maneja la edición de información de formato de empresa (página dedicada).
    Superusuarios pueden editar cualquier empresa, usuarios regulares solo la suya.
    """
    empresa = get_object_or_404(Empresa, pk=pk)

    # Verificar permisos
    if not request.user.is_superuser and request.user.empresa != empresa:
        messages.error(request, 'No tienes permiso para editar la información de formato de esta empresa.')
        return redirect('core:home')

    if request.method == 'POST':
        form = EmpresaFormatoForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Información de formato para "{empresa.nombre}" actualizada exitosamente.')
            logger.info(f"Formato actualizado para empresa {empresa.nombre} por {request.user.username}")
            return redirect('core:home')
        else:
            messages.error(request, 'Hubo un error al actualizar el formato. Por favor, revisa los datos.')
    else:
        form = EmpresaFormatoForm(instance=empresa)

    context = {
        'form': form,
        'empresa': empresa,
        'titulo_pagina': f'Editar Formato de Empresa: {empresa.nombre}',
    }
    return render(request, 'core/editar_empresa_formato.html', context)


# =============================================================================
# LOCATION MANAGEMENT VIEWS
# =============================================================================

@monitor_view
@access_check
@login_required
@permission_required('core.view_ubicacion', raise_exception=True)
def listar_ubicaciones(request):
    """
    Lista todas las ubicaciones.
    Filtradas por empresa para usuarios no-superusuarios.
    """
    ubicaciones = Ubicacion.objects.all()

    # Filtrar por empresa si el usuario no es superusuario
    if not request.user.is_superuser and request.user.empresa:
        ubicaciones = ubicaciones.filter(empresa=request.user.empresa)
    elif not request.user.is_superuser and not request.user.empresa:
        ubicaciones = Ubicacion.objects.none()

    return render(request, 'core/listar_ubicaciones.html', {
        'ubicaciones': ubicaciones,
        'titulo_pagina': 'Listado de Ubicaciones'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.add_ubicacion', raise_exception=True)
def añadir_ubicacion(request):
    """
    Maneja la adición de una nueva ubicación.
    Asigna automáticamente la empresa del usuario si no es superusuario.
    """
    if request.method == 'POST':
        form = UbicacionForm(request.POST, request=request)
        if form.is_valid():
            ubicacion = form.save(commit=False)

            # Asignar empresa automáticamente para usuarios no-superusuarios
            if not request.user.is_superuser and not ubicacion.empresa:
                ubicacion.empresa = request.user.empresa

            ubicacion.save()
            messages.success(request, 'Ubicación añadida exitosamente.')
            logger.info(f"Ubicación creada: {ubicacion.nombre} por {request.user.username}")
            return redirect('core:listar_ubicaciones')
        else:
            messages.error(request, 'Hubo un error al añadir la ubicación. Por favor, revisa los datos.')
    else:
        form = UbicacionForm(request=request)

    return render(request, 'core/añadir_ubicacion.html', {
        'form': form,
        'titulo_pagina': 'Añadir Nueva Ubicación'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.change_ubicacion', raise_exception=True)
def editar_ubicacion(request, pk):
    """
    Maneja la edición de una ubicación existente.
    Solo superusuarios o usuarios de la misma empresa pueden editar.
    """
    ubicacion = get_object_or_404(Ubicacion, pk=pk)

    # Verificar permisos
    if not request.user.is_superuser and request.user.empresa != ubicacion.empresa:
        messages.error(request, 'No tienes permiso para editar esta ubicación.')
        return redirect('core:listar_ubicaciones')

    if request.method == 'POST':
        form = UbicacionForm(request.POST, instance=ubicacion, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ubicación actualizada exitosamente.')
            logger.info(f"Ubicación actualizada: {ubicacion.nombre} por {request.user.username}")
            return redirect('core:listar_ubicaciones')
        else:
            messages.error(request, 'Hubo un error al actualizar la ubicación. Por favor, revisa los datos.')
    else:
        form = UbicacionForm(instance=ubicacion, request=request)

    return render(request, 'core/editar_ubicacion.html', {
        'form': form,
        'ubicacion': ubicacion,
        'titulo_pagina': f'Editar Ubicación: {ubicacion.nombre}'
    })


@monitor_view
@access_check
@login_required
@permission_required('core.delete_ubicacion', raise_exception=True)
def eliminar_ubicacion(request, pk):
    """
    Maneja la eliminación de una ubicación.
    Solo superusuarios o usuarios de la misma empresa pueden eliminar.
    """
    ubicacion = get_object_or_404(Ubicacion, pk=pk)

    # Verificar permisos
    if not request.user.is_superuser and request.user.empresa != ubicacion.empresa:
        messages.error(request, 'No tienes permiso para eliminar esta ubicación.')
        return redirect('core:listar_ubicaciones')

    if request.method == 'POST':
        try:
            nombre_ubicacion = ubicacion.nombre
            logger.info(f"Eliminando ubicación: {nombre_ubicacion} por {request.user.username}")
            ubicacion.delete()
            messages.success(request, f'Ubicación "{nombre_ubicacion}" eliminada exitosamente.')
            return redirect('core:listar_ubicaciones')
        except Exception as e:
            messages.error(request, f'Error al eliminar la ubicación: {e}')
            logger.error(f"Error al eliminar ubicación {ubicacion.pk}: {e}")
            return redirect('core:listar_ubicaciones')

    # Contexto para plantilla de confirmación
    context = {
        'object_name': f'la ubicación "{ubicacion.nombre}"',
        'return_url_name': 'core:listar_ubicaciones',
        'return_url_pk': None,
        'titulo_pagina': f'Eliminar Ubicación: {ubicacion.nombre}',
    }
    return render(request, 'core/confirmar_eliminacion.html', context)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _process_company_logo(empresa, logo_file):
    """
    Procesa y guarda el logo de una empresa.
    """
    archivo_subido = logo_file
    nombre_archivo = sanitize_filename(archivo_subido.name)
    ruta_s3 = f'empresas_logos/{nombre_archivo}'
    default_storage.save(ruta_s3, archivo_subido)
    empresa.logo_empresa = ruta_s3
    logger.info(f'Logo subido para empresa {empresa.nombre}: {ruta_s3}')