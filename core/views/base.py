# core/views/base.py
# Views base y utilidades comunes

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.db import models
from datetime import date, timedelta, datetime
import calendar
import io
import json
import os
import zipfile
from collections import defaultdict
import decimal
from functools import wraps

# IMPORTACIONES ADICIONALES PARA LA IMPORTACIÓN DE EXCEL
import openpyxl
from django.db import transaction
from django.utils.dateparse import parse_date

from django.http import HttpResponse, JsonResponse, Http404, HttpResponseRedirect
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.drawing.image import Image as ExcelImage

from dateutil.relativedelta import relativedelta
from django.urls import reverse

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.utils.html import mark_safe

# Importar para PDF
from django.template.loader import get_template
from weasyprint import HTML

# Logging para reemplazar prints de debug
import logging
logger = logging.getLogger(__name__)

# Importar validadores de almacenamiento
from ..storage_validators import StorageLimitValidator

# Importar los formularios
from ..forms import (
    AuthenticationForm,
    CalibracionForm, MantenimientoForm, ComprobacionForm, EquipoForm,
    BajaEquipoForm, UbicacionForm, ProcedimientoForm, ProveedorForm,
    ExcelUploadForm,
    CustomUserCreationForm, CustomUserChangeForm, UserProfileForm, EmpresaForm, EmpresaFormatoForm,
    DocumentoForm
)

# Importar modelos
from ..models import (
    Equipo, Calibracion, Mantenimiento, Comprobacion, BajaEquipo, Empresa,
    CustomUser, Ubicacion, Procedimiento, Proveedor, Documento
)

# Importar para autenticación y grupos
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError

# Importar para default_storage (manejo de archivos S3/local)
from django.core.files.storage import default_storage
from storages.backends.s3boto3 import S3Boto3Storage
from django import forms

# Importar servicios mejorados y utilidades de seguridad
from ..services_new import file_upload_service, equipment_service, cache_manager
from ..security import StorageQuotaManager
from ..templatetags.file_tags import secure_file_url, pdf_image_url

# Importar optimizaciones
from ..optimizations import OptimizedQueries, CacheHelpers
from ..monitoring import monitor_view


# =============================================================================
# UTILIDADES MEJORADAS PARA GESTIÓN DE ARCHIVOS E IMÁGENES
# =============================================================================

def sanitize_filename(filename):
    """
    Sanitiza el nombre del archivo para prevenir path traversal y caracteres peligrosos.
    """
    import re
    import os

    # Obtener solo el nombre del archivo, sin ruta
    filename = os.path.basename(filename)

    # Reemplazar caracteres peligrosos
    filename = filename.replace('..', '_')
    filename = filename.replace('/', '_')
    filename = filename.replace('\\', '_')
    filename = filename.replace(':', '_')

    # Remover caracteres no alfanuméricos excepto puntos, guiones y guiones bajos
    filename = re.sub(r'[^\w\-_\.]', '_', filename)

    # Limitar longitud
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext

    return filename


def subir_archivo(nombre_archivo, contenido):
    """
    Sube un archivo a AWS S3 usando el almacenamiento configurado en Django.
    :param nombre_archivo: Nombre con el que se guardará el archivo en S3.
    :param contenido: El objeto de archivo (ej. InMemoryUploadedFile de request.FILES).
    """
    # Sanitizar el nombre del archivo
    nombre_archivo_seguro = sanitize_filename(nombre_archivo)

    storage = default_storage
    ruta_s3 = f'pdfs/{nombre_archivo_seguro}'
    storage.save(ruta_s3, contenido)
    logger.info(f'Archivo subido a: {ruta_s3}')


def get_secure_file_url(file_field, expire_seconds=3600):
    """Obtiene URL segura para archivos, manejando tanto local como S3"""
    if not file_field:
        return None

    try:
        if hasattr(file_field, 'url'):
            if hasattr(default_storage, 'url'):
                # Verificar si es S3Storage (soporta expire) o FileSystemStorage (no soporta expire)
                if hasattr(default_storage, 'bucket'):  # S3Storage tiene atributo 'bucket'
                    return default_storage.url(file_field.name, expire=expire_seconds)
                else:  # FileSystemStorage
                    return default_storage.url(file_field.name)
            else:
                return file_field.url
        return None
    except Exception as e:
        logger.error(f"Error obteniendo URL de archivo: {str(e)}")
        return None


def get_empresa_logo_url(empresa, expire_seconds=3600):
    """Obtiene URL del logo de empresa de forma segura"""
    if not empresa or not empresa.logo_empresa:
        return None
    return get_secure_file_url(empresa.logo_empresa, expire_seconds)


def get_equipo_imagen_url(equipo, expire_seconds=3600):
    """Obtiene URL de imagen de equipo de forma segura"""
    if not equipo or not equipo.imagen_equipo:
        return None
    return get_secure_file_url(equipo.imagen_equipo, expire_seconds)


# =============================================================================
# Decoradores personalizados
# =============================================================================

def trial_check(view_func):
    """
    Decorador que verifica si la empresa del usuario tiene acceso a funciones avanzadas
    y bloquea ciertas acciones si no tiene un plan activo.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if request.user.is_authenticated and hasattr(request.user, 'empresa'):
            empresa = request.user.empresa
            estado_plan = empresa.get_estado_suscripcion_display()

            if empresa and estado_plan in ["Plan Expirado", "Período de Prueba Expirado", "Expirado"]:
                protected_views = [
                    'añadir_equipo', 'editar_equipo', 'añadir_calibracion', 'añadir_mantenimiento',
                    'añadir_comprobacion', 'generar_informe_zip', 'exportar_equipos_excel'
                ]

                current_view_name = view_func.__name__
                if current_view_name in protected_views:
                    messages.warning(request,
                        f'⚠️ Funcionalidad limitada: Tu plan ha expirado. '
                        f'Contacta al administrador para renovar tu suscripción.'
                    )
                    return redirect('core:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def access_check(view_func):
    """
    Decorador que verifica el acceso del usuario y registra la actividad.
    Bloquea completamente el acceso si el plan de la empresa ha expirado.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        logger.info(f"Usuario {request.user.username} accedió a {view_func.__name__}")

        # Los superusuarios siempre tienen acceso completo
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Verificar estado del plan para usuarios regulares
        if request.user.is_authenticated and hasattr(request.user, 'empresa') and request.user.empresa:
            empresa = request.user.empresa
            estado_plan = empresa.get_estado_suscripcion_display()

            # Si el plan está expirado, bloquear acceso completamente
            if estado_plan in ["Plan Expirado", "Período de Prueba Expirado", "Expirado"]:
                # Vistas permitidas aún con plan expirado (solo lectura básica)
                allowed_expired_views = ['dashboard', 'logout', 'home']

                current_view_name = view_func.__name__
                if current_view_name not in allowed_expired_views:
                    logger.warning(f"Acceso bloqueado para usuario {request.user.username} - Plan expirado en vista {current_view_name}")
                    return render(request, 'core/access_denied.html', status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    """
    Decorador que requiere que el usuario sea superusuario
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Acceso denegado: Se requieren permisos de administrador.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# VIEWS COMUNES Y DE ERROR
# =============================================================================

def access_denied(request):
    """
    View para mostrar página de acceso denegado
    """
    context = {
        'titulo_pagina': 'Acceso Denegado',
        'mensaje': 'No tienes permisos para acceder a esta página.'
    }
    return render(request, 'access_denied.html', context)


def page_not_found(request):
    """
    View personalizada para error 404
    """
    context = {
        'titulo_pagina': 'Página No Encontrada',
        'mensaje': 'La página que buscas no existe.'
    }
    return render(request, '404.html', context)


def server_error(request):
    """
    View personalizada para error 500
    """
    context = {
        'titulo_pagina': 'Error del Servidor',
        'mensaje': 'Ha ocurrido un error interno. Por favor contacta al administrador.'
    }
    return render(request, '500.html', context)


# ===== FUNCIONES AJAX BÁSICAS =====

def add_message(request):
    """
    Adds a Django message via an AJAX POST request.
    Expected JSON body: {"message": "Your message here", "tags": "success|info|warning|error"}
    """
    import json
    from django.contrib import messages
    from django.http import JsonResponse

    try:
        data = json.loads(request.body)
        message_text = data.get('message', 'Mensaje genérico.')
        message_tags = data.get('tags', 'info')

        if message_tags == 'success':
            messages.success(request, message_text)
        elif message_tags == 'error':
            messages.error(request, message_text)
        elif message_tags == 'warning':
            messages.warning(request, message_text)
        else:
            messages.info(request, message_text)

        return JsonResponse({'status': 'success', 'message': 'Mensaje añadido.'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def es_miembro_empresa(user, empresa_id):
    """Verifica si el usuario pertenece a la empresa especificada."""
    return user.is_authenticated and user.empresa and user.empresa.pk == empresa_id


@monitor_view
@login_required
def access_denied(request):
    """
    Renders the access denied page.
    """
    return render(request, 'core/access_denied.html', {'titulo_pagina': 'Acceso Denegado'})


@login_required
@require_POST
def session_heartbeat(request):
    """
    Endpoint para recibir heartbeat del frontend y mantener sesión activa.

    Este endpoint extiende la sesión por 30 minutos más cuando recibe
    un ping del JavaScript de keepalive, indicando que el usuario está activo.
    """
    try:
        # Extender sesión por 30 minutos más
        request.session.set_expiry(1800)  # 1800 segundos = 30 minutos

        # Parsear datos del heartbeat
        try:
            data = json.loads(request.body)
            timestamp = data.get('timestamp')
            inactive_time = data.get('inactive_time', 0)

            logger.debug(
                f"Heartbeat recibido de {request.user.username}. "
                f"Tiempo inactivo: {inactive_time}s"
            )
        except (json.JSONDecodeError, AttributeError):
            # Si no hay body o no se puede parsear, no es crítico
            pass

        return JsonResponse({
            'status': 'ok',
            'message': 'Session extended',
            'expires_in': 1800  # segundos
        })

    except Exception as e:
        logger.error(f"Error en session_heartbeat: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to extend session'
        }, status=500)