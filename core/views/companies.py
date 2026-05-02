# core/views/companies.py
# Views para gestión de empresas, ubicaciones y planes

import re

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .base import *
from ..constants import ESTADO_ACTIVO
from ..models import EmpresaFormatoLog

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
# SELF-SERVICE: CREACIÓN DE USUARIOS POR EL ADMINISTRADOR DE LA EMPRESA
# =============================================================================

@monitor_view
@access_check
@login_required
def crear_usuario_empresa(request):
    """
    Permite a usuarios con rol ADMINISTRADOR crear nuevos usuarios para su empresa.
    Valida que no se supere el límite de usuarios (limite_usuarios_empresa).
    El ADMINISTRADOR puede crear técnicos, admins y gerentes.
    """
    if not request.user.is_superuser and not request.user.is_administrador():
        messages.error(request, 'Solo administradores pueden crear usuarios.')
        return redirect('core:dashboard')

    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'No tienes una empresa asociada.')
        return redirect('core:dashboard')

    # Contar usuarios activos actuales (sin contar superusuarios de SAM)
    total_usuarios = empresa.usuarios_empresa.filter(is_active=True, is_superuser=False).count()
    limite = empresa.limite_usuarios_empresa
    puede_crear = total_usuarios < limite

    password_generado = None  # se muestra solo tras creación exitosa

    if request.method == 'POST':
        if not puede_crear:
            messages.error(
                request,
                f'Alcanzaste el límite de {limite} usuarios. '
                'Compra usuarios adicionales en la sección de Add-ons.'
            )
            return redirect('core:planes')

        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip().lower()
        rol        = request.POST.get('rol_usuario', 'TECNICO').upper()

        if rol not in ('TECNICO', 'ADMINISTRADOR', 'GERENCIA'):
            rol = 'TECNICO'

        if not first_name or not email:
            messages.error(request, 'El nombre y el correo son obligatorios.')
        else:
            # Generar username: primeras letras + últimas del NIT
            nit_clean  = re.sub(r'\D', '', empresa.nit or '')[:6]
            base       = re.sub(r'[^a-z]', '', (first_name[:3] + last_name[:3]).lower())
            base_username = base + nit_clean or 'user' + nit_clean
            username   = base_username
            counter    = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Contraseña temporal segura
            from django.utils.crypto import get_random_string
            password = get_random_string(12)

            try:
                with transaction.atomic():
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        empresa=empresa,
                        rol_usuario=rol,
                        is_management_user=(rol == 'GERENCIA'),
                        can_access_dashboard_decisiones=(rol == 'GERENCIA'),
                        is_active=True,
                        password=password,
                    )
                    from .registro import asignar_permisos_por_rol
                    asignar_permisos_por_rol(user)

                    logger.info(
                        f"Usuario {username} (rol={rol}) creado para empresa "
                        f"{empresa.nombre} por {request.user.username}"
                    )
                    password_generado = password
                    messages.success(
                        request,
                        f'Usuario "{username}" creado con rol {rol}. '
                        f'Contraseña temporal: {password} — entregala al usuario '
                        'para que la cambie en su primer ingreso.'
                    )
                    # Recargar conteo tras creación exitosa
                    total_usuarios = empresa.usuarios_empresa.filter(
                        is_active=True, is_superuser=False
                    ).count()
                    puede_crear = total_usuarios < limite

            except Exception as e:
                messages.error(request, f'Error al crear usuario: {e}')
                logger.error(
                    f"Error creando usuario en empresa {empresa.nombre}: {e}"
                )

    context = {
        'empresa': empresa,
        'total_usuarios': total_usuarios,
        'limite': limite,
        'puede_crear': puede_crear,
        'password_generado': password_generado,
        'titulo_pagina': 'Crear Usuario',
    }
    return render(request, 'core/crear_usuario_empresa.html', context)


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


def _enviar_email_cambio_formato(empresa, usuario_editor, cambios):
    """Envía email de notificación a Admin/Gerencia cuando cambian códigos/versiones de formatos."""
    import base64
    from pathlib import Path

    destinatarios = list(
        CustomUser.objects.filter(
            empresa=empresa,
            rol_usuario__in=['ADMINISTRADOR', 'GERENCIA'],
            is_active=True,
        ).exclude(email='').values_list('email', flat=True)
    )
    if not destinatarios:
        return

    # Logo embebido en base64 para máxima compatibilidad con clientes de email
    logo_tag = ''
    try:
        logo_path = Path(settings.BASE_DIR) / 'logo.png'
        if logo_path.exists():
            with open(logo_path, 'rb') as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            logo_tag = (
                f'<img src="data:image/png;base64,{logo_b64}" '
                f'alt="SAM Metrología" style="max-width:80px;margin-top:14px;">'
            )
    except Exception:
        pass

    nombre_editor = usuario_editor.get_full_name() or usuario_editor.username

    filas_html = ''.join(
        f'<tr>'
        f'<td style="padding:9px 14px;border-bottom:1px solid #e2e8f0;font-weight:600;">{etiqueta}</td>'
        f'<td style="padding:9px 14px;border-bottom:1px solid #e2e8f0;color:#64748b;">{anterior or "—"}</td>'
        f'<td style="padding:9px 14px;border-bottom:1px solid #e2e8f0;color:#003366;font-weight:600;">{nuevo or "—"}</td>'
        f'</tr>'
        for etiqueta, anterior, nuevo in cambios
    )

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#333;line-height:1.6;margin:0;padding:0;">
  <div style="max-width:600px;margin:20px auto;border:1px solid #e1e1e1;border-radius:10px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,0.05);">

    <div style="background-color:#003366;color:#ffffff;padding:25px;text-align:center;">
      <h1 style="margin:0;font-size:22px;letter-spacing:1px;">SAM METROLOGÍA</h1>
      <p style="margin:5px 0 0;opacity:0.9;font-size:14px;">Control Digital e Inteligencia Metrológica</p>
      {logo_tag}
    </div>

    <div style="padding:35px;background-color:#ffffff;">
      <p>Cordial saludo,</p>
      <p>El usuario <strong>{nombre_editor}</strong> realizó cambios en los formatos de documentos
         de la empresa <strong>{empresa.nombre}</strong>.</p>

      <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
        <thead>
          <tr style="background-color:#003366;color:#ffffff;">
            <th style="padding:10px 14px;text-align:left;">Campo</th>
            <th style="padding:10px 14px;text-align:left;">Valor anterior</th>
            <th style="padding:10px 14px;text-align:left;">Valor nuevo</th>
          </tr>
        </thead>
        <tbody>{filas_html}</tbody>
      </table>

      <p style="color:#555;font-size:14px;">Este cambio quedó registrado en el historial de auditoría
         de SAM Metrología y puede consultarse desde el panel de administración.</p>
      <p>Quedo atento a sus comentarios o cualquier requerimiento adicional.</p>
      <p>Atentamente,</p>
      <div style="color:#003366;font-weight:bold;font-size:16px;margin-top:10px;">SAM Metrología</div>
      <div style="font-size:14px;color:#666;margin-top:4px;">
        <a href="https://sammetrologia.com" style="color:#0056b3;text-decoration:none;">sammetrologia.com</a>
        &nbsp;|&nbsp; +57 324 799 0534
      </div>
    </div>

    <div style="background-color:#1a1a1a;padding:25px;font-size:12px;text-align:center;color:#999;">
      <p style="margin:0;"><strong>SAM Metrología | Gestión Metrológica 4.0</strong><br>
      Colombia | Soluciones Avanzadas en Medición</p>
    </div>
  </div>
</body>
</html>"""

    text_body = (
        f"Cambio en formatos de {empresa.nombre} por {nombre_editor}:\n"
        + '\n'.join(f"  {e}: {a or '—'} → {n or '—'}" for e, a, n in cambios)
    )

    try:
        msg = EmailMultiAlternatives(
            subject=f'[SAM] Actualización de formatos — {empresa.nombre}',
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        logger.exception("Error enviando email de cambio de formato para empresa %s", empresa.pk)


@monitor_view
@access_check
@login_required
@require_http_methods(["GET", "POST"])
def editar_empresa_formato(request, pk):
    """
    Maneja la edición de información de formato de empresa (página dedicada).
    Solo Admin y Gerente pueden editar. Superusuarios pueden editar cualquier empresa.
    """
    empresa = get_object_or_404(Empresa, pk=pk)

    # Verificar permisos: Solo superusuario, ADMINISTRADOR o GERENCIA
    if not request.user.is_superuser:
        # Verificar que pertenece a la empresa
        if request.user.empresa != empresa:
            messages.error(request, 'No tienes permiso para editar la información de formato de esta empresa.')
            return redirect('core:home')

        # Verificar que sea ADMINISTRADOR o GERENCIA
        if request.user.rol_usuario not in ['ADMINISTRADOR', 'GERENCIA']:
            messages.error(request, 'Solo usuarios con rol Administrador o Gerencia pueden editar la información de formato.')
            return redirect('core:home')

    CAMPOS_FORMATO = {
        # Hoja de vida
        'formato_codificacion_empresa': 'Código Hoja de Vida',
        'formato_version_empresa': 'Versión Hoja de Vida',
        'formato_fecha_version_empresa': 'Fecha Hoja de Vida',
        # Confirmación metrológica
        'confirmacion_codigo': 'Código Confirmación',
        'confirmacion_version': 'Versión Confirmación',
        'confirmacion_fecha_formato': 'Fecha Confirmación',
        # Intervalos de calibración
        'intervalos_codigo': 'Código Intervalos',
        'intervalos_version': 'Versión Intervalos',
        'intervalos_fecha_formato': 'Fecha Intervalos',
        # Comprobación metrológica
        'comprobacion_codigo': 'Código Comprobación',
        'comprobacion_version': 'Versión Comprobación',
        'comprobacion_fecha_formato': 'Fecha Comprobación',
        # Mantenimiento
        'mantenimiento_codigo': 'Código Mantenimiento',
        'mantenimiento_version': 'Versión Mantenimiento',
        'mantenimiento_fecha_formato': 'Fecha Mantenimiento',
        # Listado de equipos
        'listado_codigo': 'Código Listado de Equipos',
        'listado_version': 'Versión Listado de Equipos',
        'listado_fecha_formato': 'Fecha Listado de Equipos',
    }

    def _campo_a_str(valor):
        """Convierte cualquier valor de campo (incluidos DateField) a string para el log."""
        if valor is None or valor == '':
            return ''
        if hasattr(valor, 'strftime'):
            return valor.strftime('%d/%m/%Y')
        return str(valor)

    if request.method == 'POST':
        form = EmpresaFormatoForm(request.POST, instance=empresa)
        if form.is_valid():
            # Capturar valores anteriores antes de guardar (incluye fechas)
            valores_anteriores = {campo: _campo_a_str(getattr(empresa, campo, '')) for campo in CAMPOS_FORMATO}

            form.save()
            empresa.refresh_from_db()

            # Registrar y notificar cambios
            cambios = []
            for campo, etiqueta in CAMPOS_FORMATO.items():
                valor_anterior = valores_anteriores[campo]
                valor_nuevo = _campo_a_str(getattr(empresa, campo, ''))
                if valor_anterior != valor_nuevo:
                    EmpresaFormatoLog.objects.create(
                        empresa=empresa,
                        campo=etiqueta,
                        valor_anterior=valor_anterior,
                        valor_nuevo=valor_nuevo,
                        usuario=request.user,
                    )
                    cambios.append((etiqueta, valor_anterior, valor_nuevo))

            if cambios:
                _enviar_email_cambio_formato(empresa, request.user, cambios)

            messages.success(request, f'Información de formato para "{empresa.nombre}" actualizada exitosamente.')
            logger.info(f"Formato actualizado para empresa {empresa.nombre} por {request.user.username}")
            return redirect('core:editar_empresa_formato', pk=empresa.pk)
        else:
            messages.error(request, 'Hubo un error al actualizar el formato. Por favor, revisa los datos.')
    else:
        form = EmpresaFormatoForm(instance=empresa)

    # Logs agrupados por campo para los modales de historial
    logs_por_campo = {}
    for etiqueta in CAMPOS_FORMATO.values():
        logs_por_campo[etiqueta] = list(
            EmpresaFormatoLog.objects.filter(empresa=empresa, campo=etiqueta)
            .select_related('usuario')
            .order_by('-fecha')[:20]
        )

    context = {
        'form': form,
        'empresa': empresa,
        'titulo_pagina': f'Editar Formato de Empresa: {empresa.nombre}',
        'logs_por_campo': logs_por_campo,
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
# SELF-SERVICE: EDITAR PERFIL DE EMPRESA (Admin / Gerencia)
# =============================================================================

@monitor_view
@access_check
@login_required
def editar_perfil_empresa(request):
    """
    Permite a ADMINISTRADOR y GERENCIA editar los datos operativos de su empresa:
    teléfono, dirección, correos de facturación, correos de notificaciones y logo.
    No expone NIT, nombre ni configuración de plan (solo superusuarios pueden tocar eso).
    """
    if request.user.is_superuser:
        # Superusuario usa la vista completa editar_empresa
        messages.info(request, 'Como superusuario usa la vista de administración.')
        if request.user.empresa:
            return redirect('core:editar_empresa', pk=request.user.empresa.pk)
        return redirect('core:listar_empresas')

    empresa = request.user.empresa
    if not empresa:
        messages.error(request, 'No tienes una empresa asociada.')
        return redirect('core:dashboard')

    if request.user.rol_usuario not in ['ADMINISTRADOR', 'GERENCIA']:
        messages.error(request, 'Solo usuarios con rol Administrador o Gerencia pueden editar el perfil de la empresa.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = EmpresaPerfilForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            try:
                empresa_actualizada = form.save(commit=False)
                if 'logo_empresa' in request.FILES:
                    _process_company_logo(empresa_actualizada, request.FILES['logo_empresa'])
                empresa_actualizada.save()
                messages.success(request, 'Perfil de empresa actualizado exitosamente.')
                logger.info(f"Perfil empresa actualizado: {empresa.nombre} por {request.user.username}")
                return redirect('core:editar_perfil_empresa')
            except Exception as e:
                logger.error(f"Error al actualizar perfil de empresa {empresa.pk}: {e}")
                messages.error(request, str(e))
        else:
            messages.error(request, 'Revisa los datos ingresados.')
    else:
        form = EmpresaPerfilForm(instance=empresa)

    # Determinar qué campos faltan (para mostrar progreso)
    campos_faltantes = []
    if not empresa.correos_facturacion:
        campos_faltantes.append('correos de facturación')
    if not empresa.correos_notificaciones:
        campos_faltantes.append('correos de notificaciones')
    if not empresa.logo_empresa:
        campos_faltantes.append('logo')
    if not empresa.telefono:
        campos_faltantes.append('teléfono')

    return render(request, 'core/editar_perfil_empresa.html', {
        'form': form,
        'empresa': empresa,
        'campos_faltantes': campos_faltantes,
        'titulo_pagina': 'Perfil de Empresa',
    })


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
    try:
        default_storage.save(ruta_s3, archivo_subido)
    except Exception as e:
        logger.error(
            f"Error al subir logo a R2 para empresa '{empresa.nombre}': "
            f"{type(e).__name__}: {e}"
        )
        raise Exception(
            "No se pudo subir el logo de la empresa al almacenamiento. "
            "Por favor intenta de nuevo o contacta al soporte."
        ) from e
    empresa.logo_empresa = ruta_s3
    logger.info(f'Logo subido para empresa {empresa.nombre}: {ruta_s3}')