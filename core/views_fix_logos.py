# Vista temporal para que las empresas puedan volver a subir sus logos
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import default_storage
from .models import Empresa
from .forms import EmpresaForm
import logging

logger = logging.getLogger('core')

@login_required
def fix_mi_logo_empresa(request):
    """
    Vista para que los usuarios puedan corregir el logo de su empresa
    """
    # Obtener la empresa del usuario
    if hasattr(request.user, 'empresa'):
        empresa = request.user.empresa
    else:
        messages.error(request, 'No tienes una empresa asociada.')
        return redirect('core:dashboard')

    # Verificar si el logo actual existe
    logo_exists = False
    if empresa.logo_empresa:
        try:
            logo_exists = default_storage.exists(empresa.logo_empresa.name)
        except:
            logo_exists = False

    if request.method == 'POST' and request.FILES.get('nuevo_logo'):
        try:
            # Guardar el nuevo logo
            nuevo_logo = request.FILES['nuevo_logo']

            # Validar formato
            if not nuevo_logo.content_type.startswith('image/'):
                messages.error(request, 'El archivo debe ser una imagen.')
                return render(request, 'core/fix_mi_logo.html', {
                    'empresa': empresa,
                    'logo_exists': logo_exists
                })

            # Validar tamaño (10MB máximo)
            if nuevo_logo.size > 10 * 1024 * 1024:
                messages.error(request, 'La imagen no debe superar 10MB.')
                return render(request, 'core/fix_mi_logo.html', {
                    'empresa': empresa,
                    'logo_exists': logo_exists
                })

            # Guardar el logo
            empresa.logo_empresa = nuevo_logo
            empresa.save()

            logger.info(f"Logo actualizado para empresa {empresa.nombre} por usuario {request.user.username}")
            messages.success(request, f'Logo actualizado exitosamente para {empresa.nombre}.')

            return redirect('core:detalle_empresa', pk=empresa.pk)

        except Exception as e:
            logger.error(f"Error actualizando logo para empresa {empresa.nombre}: {str(e)}")
            messages.error(request, 'Error al subir el logo. Inténtalo nuevamente.')

    return render(request, 'core/fix_mi_logo.html', {
        'empresa': empresa,
        'logo_exists': logo_exists
    })

@login_required
def lista_empresas_sin_logo(request):
    """
    Vista para que superusuarios vean empresas sin logo o con logos perdidos
    Solo accesible para superusuarios
    """
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('core:dashboard')

    # Obtener empresas con problemas de logo
    empresas_sin_logo = []
    empresas_logo_perdido = []

    for empresa in Empresa.objects.all():
        if not empresa.logo_empresa:
            empresas_sin_logo.append(empresa)
        else:
            try:
                if not default_storage.exists(empresa.logo_empresa.name):
                    empresas_logo_perdido.append(empresa)
            except:
                empresas_logo_perdido.append(empresa)

    return render(request, 'core/lista_empresas_sin_logo.html', {
        'empresas_sin_logo': empresas_sin_logo,
        'empresas_logo_perdido': empresas_logo_perdido,
        'total_problemas': len(empresas_sin_logo) + len(empresas_logo_perdido)
    })