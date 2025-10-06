# core/views/terminos.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from core.models import TerminosYCondiciones, AceptacionTerminos
import logging

logger = logging.getLogger('core')


def get_client_ip(request):
    """
    Obtiene la dirección IP del cliente desde el request.
    Maneja proxies y balanceadores de carga.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def aceptar_terminos(request):
    """
    Vista para mostrar y procesar la aceptación de términos y condiciones.

    GET: Muestra el formulario con el PDF de los términos
    POST: Procesa la aceptación y guarda el registro
    """
    # Obtener términos activos
    terminos_activos = TerminosYCondiciones.get_terminos_activos()

    if not terminos_activos:
        messages.error(request, 'No hay términos y condiciones configurados actualmente.')
        logger.error('No hay términos y condiciones activos configurados')
        return redirect('core:dashboard')

    # Verificar si el usuario ya aceptó estos términos
    if AceptacionTerminos.usuario_acepto_terminos_actuales(request.user):
        messages.info(request, 'Ya has aceptado los términos y condiciones actuales.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        # Verificar que se aceptó el checkbox
        acepta = request.POST.get('acepta_terminos', False)

        if acepta == 'on':
            # Obtener información del cliente
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Crear registro de aceptación
            aceptacion = AceptacionTerminos.crear_aceptacion(
                usuario=request.user,
                ip_address=ip_address,
                user_agent=user_agent
            )

            if aceptacion:
                messages.success(
                    request,
                    'Has aceptado los términos y condiciones. Ahora puedes usar la plataforma SAM.'
                )
                logger.info(
                    f'Usuario {request.user.username} aceptó términos v{terminos_activos.version} '
                    f'desde IP {ip_address}'
                )

                # Redirigir al dashboard
                return redirect('core:dashboard')
            else:
                messages.error(request, 'Hubo un error al registrar tu aceptación. Intenta nuevamente.')
                logger.error(f'Error al crear aceptación para usuario {request.user.username}')

        else:
            # Usuario no marcó el checkbox
            messages.warning(request, 'Debes aceptar los términos y condiciones para continuar.')

    # Renderizar el formulario (GET o POST fallido)
    context = {
        'terminos': terminos_activos,
        'titulo_pagina': 'Términos y Condiciones',
    }

    return render(request, 'core/terminos_condiciones.html', context)


@login_required
def rechazar_terminos(request):
    """
    Vista para procesar el rechazo de términos y condiciones.
    El usuario será deslogueado del sistema.
    """
    if request.method == 'POST':
        username = request.user.username

        # Log del rechazo
        logger.warning(f'Usuario {username} rechazó los términos y condiciones')

        # Cerrar sesión
        from django.contrib.auth import logout
        logout(request)

        messages.info(
            request,
            'Has rechazado los términos y condiciones. Para usar SAM Metrología, '
            'debes aceptarlos. Si tienes dudas, contacta a soporte.'
        )

        return redirect('core:login')

    # Si llega por GET, redirigir a términos
    return redirect('core:aceptar_terminos')


@login_required
def ver_terminos_pdf(request):
    """
    Vista para visualizar el PDF de los términos y condiciones activos.
    """
    terminos_activos = TerminosYCondiciones.get_terminos_activos()

    if not terminos_activos or not terminos_activos.archivo_pdf:
        return HttpResponse('No hay PDF de términos disponible', status=404)

    # Obtener el archivo PDF
    pdf_file = terminos_activos.archivo_pdf

    # Retornar el PDF
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Terminos_SAM_v{terminos_activos.version}.pdf"'

    return response


@login_required
def mi_aceptacion_terminos(request):
    """
    Vista para que el usuario vea los términos que aceptó con los detalles de su aceptación.
    """
    # Obtener la aceptación del usuario para los términos actuales
    mi_aceptacion = AceptacionTerminos.objects.filter(
        usuario=request.user,
        terminos__activo=True
    ).select_related('terminos', 'empresa').first()

    if not mi_aceptacion:
        # Si no ha aceptado, redirigir a aceptar términos
        return redirect('core:aceptar_terminos')

    context = {
        'mi_aceptacion': mi_aceptacion,
        'terminos': mi_aceptacion.terminos,
    }

    return render(request, 'core/mi_aceptacion_terminos.html', context)
