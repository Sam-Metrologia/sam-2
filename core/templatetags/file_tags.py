# core/templatetags/file_tags.py
# Template tags para manejo seguro de archivos e imágenes

from django import template
from django.core.files.storage import default_storage
from django.conf import settings
import logging

register = template.Library()
logger = logging.getLogger('core')

@register.simple_tag
def secure_file_url(file_field, expire_seconds=3600):
    """
    Obtiene URL segura para archivos, funciona tanto en local como en S3
    """
    if not file_field:
        return ''

    try:
        # Si es un campo de archivo de Django
        if hasattr(file_field, 'name') and file_field.name:
            # Verificar si es S3 storage o local storage
            storage_name = default_storage.__class__.__name__

            if 'S3' in storage_name or hasattr(default_storage, 'bucket'):
                # Para S3 - generar URL firmada
                try:
                    return default_storage.url(file_field.name, expire=expire_seconds)
                except TypeError:
                    # Fallback si el storage no soporta expire
                    return default_storage.url(file_field.name)
            else:
                # Para almacenamiento local - usar URL normal (no soporta expire)
                return file_field.url if hasattr(file_field, 'url') else default_storage.url(file_field.name)
        return ''
    except Exception as e:
        logger.error(f"Error obteniendo URL de archivo: {str(e)}")
        return ''

@register.simple_tag
def empresa_logo_url(empresa, expire_seconds=3600):
    """
    Obtiene URL del logo de empresa de forma segura
    """
    if not empresa or not hasattr(empresa, 'logo_empresa') or not empresa.logo_empresa:
        return ''
    return secure_file_url(empresa.logo_empresa, expire_seconds)

@register.simple_tag
def equipo_imagen_url(equipo, expire_seconds=3600):
    """
    Obtiene URL de imagen de equipo de forma segura
    """
    if not equipo or not hasattr(equipo, 'imagen_equipo') or not equipo.imagen_equipo:
        return ''
    return secure_file_url(equipo.imagen_equipo, expire_seconds)

@register.filter
def has_file(file_field):
    """
    Verifica si un campo de archivo tiene un archivo asociado
    """
    return bool(file_field and hasattr(file_field, 'name') and file_field.name)

@register.simple_tag
def pdf_image_url(file_field):
    """
    Obtiene URL para usar en PDFs (con URL absoluta)
    """
    if not file_field:
        return ''

    try:
        if hasattr(file_field, 'name') and file_field.name:
            storage_name = default_storage.__class__.__name__

            if 'S3' in storage_name or hasattr(default_storage, 'bucket'):
                # Para S3, usar URL con mayor tiempo de expiración para PDFs
                try:
                    url = default_storage.url(file_field.name, expire=7200)  # 2 horas
                except TypeError:
                    # Fallback si el storage no soporta expire
                    url = default_storage.url(file_field.name)
                # Asegurar que sea URL absoluta
                if url.startswith('//'):
                    url = 'https:' + url
                return url
            else:
                # Para almacenamiento local
                url = file_field.url if hasattr(file_field, 'url') else default_storage.url(file_field.name)
                if url.startswith('/'):
                    # Para URLs locales, agregar el dominio
                    from django.contrib.sites.models import Site
                    try:
                        current_site = Site.objects.get_current()
                        url = f"https://{current_site.domain}{url}"
                    except:
                        # Fallback para desarrollo
                        url = f"http://127.0.0.1:8000{url}"
                return url
        return ''
    except Exception as e:
        logger.error(f"Error obteniendo URL de imagen para PDF: {str(e)}")
        return ''

@register.inclusion_tag('core/includes/image_display.html')
def display_image(file_field, alt_text="", css_class="", max_width="300px"):
    """
    Template tag para mostrar imágenes de forma segura con fallback
    """
    return {
        'image_url': secure_file_url(file_field) if file_field else '',
        'has_image': has_file(file_field),
        'alt_text': alt_text,
        'css_class': css_class,
        'max_width': max_width
    }

@register.simple_tag
def storage_quota_info(empresa):
    """
    Obtiene información de cuota de almacenamiento para una empresa
    """
    if not empresa:
        return {}

    try:
        from ..security import StorageQuotaManager
        manager = StorageQuotaManager()
        return manager.get_quota_info(empresa)
    except Exception as e:
        logger.error(f"Error obteniendo información de cuota: {str(e)}")
        return {}