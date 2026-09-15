# core/signals.py
# Signals for cache invalidation

import logging
import threading
from contextlib import contextmanager
from django.db.models import FileField, ImageField
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.core.files.storage import default_storage
from .models import (
    Equipo, Calibracion, Mantenimiento, Comprobacion, CustomUser, OnboardingProgress,
    PrestamoEquipo, BajaEquipo, Procedimiento, Empresa, Documento,
)

logger = logging.getLogger(__name__)

# Ver collect_file_cleanup_errors() más abajo — permite a un borrado en lote
# (ej. la purga automática de empresas) enterarse si algún archivo no se pudo
# borrar del storage, en vez de que quede solo como advertencia en el log.
_file_cleanup_state = threading.local()


@contextmanager
def collect_file_cleanup_errors():
    """
    Úsalo alrededor de un borrado (normalmente dentro de una transacción)
    para recibir la lista de archivos que no se pudieron borrar del storage.

    Sin esto, un fallo al borrar un archivo (ej. R2 caído un momento) solo
    queda como warning en el log — en un proceso automático sin revisión
    humana (como la purga mensual de empresas), eso significa que las filas
    de la base de datos se borran igual mientras el archivo real queda
    huérfano para siempre, sin que nadie se entere. Con este context manager,
    el llamador puede revisar la lista al salir y decidir, por ejemplo,
    cancelar la transacción completa si no quedó vacía.
    """
    errores = []
    _file_cleanup_state.errores = errores
    try:
        yield errores
    finally:
        _file_cleanup_state.errores = None


def _borrar_archivos_de_instancia(instance):
    """
    Borra del almacenamiento (Cloudflare R2/S3, o local en dev) todos los
    FileField/ImageField con archivo real de una instancia que se acaba de
    eliminar de la base de datos.

    Django NUNCA hace esto solo: borrar un registro no borra el archivo que
    apuntaba en el storage -- si nadie lo hace explícito, el archivo queda
    huérfano ahí para siempre, siguiendo consumiendo (y cobrando) espacio
    aunque el registro ya no exista. Esto se conecta a cualquier modelo con
    campos de archivo via post_delete, así que cubre tanto el borrado normal
    del día a día como el borrado en cascada de una empresa completa.
    """
    for field in instance._meta.get_fields():
        if isinstance(field, (FileField, ImageField)):
            try:
                archivo = getattr(instance, field.name, None)
            except Exception:
                continue
            if archivo and archivo.name:
                try:
                    archivo.delete(save=False)
                except Exception as e:
                    logger.warning(
                        f"No se pudo borrar del storage el archivo '{archivo.name}' "
                        f"({instance.__class__.__name__} id={instance.pk}): {e}"
                    )
                    errores = getattr(_file_cleanup_state, 'errores', None)
                    if errores is not None:
                        errores.append(f"{instance.__class__.__name__} id={instance.pk}: {archivo.name} ({e})")


@receiver(post_delete, sender=Equipo)
@receiver(post_delete, sender=Calibracion)
@receiver(post_delete, sender=Mantenimiento)
@receiver(post_delete, sender=Comprobacion)
@receiver(post_delete, sender=BajaEquipo)
@receiver(post_delete, sender=PrestamoEquipo)
@receiver(post_delete, sender=Procedimiento)
@receiver(post_delete, sender=Empresa)
def borrar_archivos_al_eliminar(sender, instance, **kwargs):
    """Limpieza de storage al borrar cualquiera de estos modelos (individual o en cascada)."""
    _borrar_archivos_de_instancia(instance)


@receiver(post_delete, sender=Documento)
def borrar_archivo_documento(sender, instance, **kwargs):
    """
    Documento.archivo_s3_path es un CharField con la ruta (no un FileField),
    así que no lo cubre el helper genérico de arriba -- se borra aparte.
    """
    if instance.archivo_s3_path:
        try:
            if default_storage.exists(instance.archivo_s3_path):
                default_storage.delete(instance.archivo_s3_path)
        except Exception as e:
            logger.warning(f"No se pudo borrar del storage el documento '{instance.archivo_s3_path}': {e}")
            errores = getattr(_file_cleanup_state, 'errores', None)
            if errores is not None:
                errores.append(f"Documento id={instance.pk}: {instance.archivo_s3_path} ({e})")


def invalidate_dashboard_cache(empresa_id=None):
    """
    Invalida el cache del dashboard usando versioning (compatible con cualquier backend).

    En lugar de delete_pattern (no disponible en Django nativo) o cache.clear()
    (que borra el cache de storage y causa llamadas masivas a R2), se incrementa
    un contador de versión por empresa. El dashboard incluye este contador en su
    cache key, de modo que las entradas anteriores quedan huérfanas y expiran
    naturalmente en 5 minutos.

    Args:
        empresa_id: ID de la empresa cuyo cache se debe invalidar
    """
    from datetime import date

    if empresa_id:
        # Bump versión específica de la empresa (usuarios normales y superusuarios
        # que tengan esa empresa seleccionada)
        version_key = f"dashboard_version_{empresa_id}"
        try:
            cache.incr(version_key)
        except ValueError:
            cache.set(version_key, 1, 86400 * 30)  # 30 días de TTL
        except Exception:
            current = cache.get(version_key, 0)
            cache.set(version_key, current + 1, 86400 * 30)

        # Bump versión 'all' para superusuarios sin empresa seleccionada
        all_version_key = "dashboard_version_all"
        try:
            cache.incr(all_version_key)
        except ValueError:
            cache.set(all_version_key, 1, 86400 * 30)
        except Exception:
            current = cache.get(all_version_key, 0)
            cache.set(all_version_key, current + 1, 86400 * 30)

        # Panel de decisiones: clave determinista → delete directo (sin pattern)
        year = date.today().year
        cache.delete(f"panel_decisiones_{empresa_id}_{year}")
    else:
        # Equipo sin empresa (caso borde) → clear es seguro aquí
        cache.clear()


@receiver(post_save, sender=Equipo)
@receiver(post_delete, sender=Equipo)
def invalidate_cache_on_equipo_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard y actualiza stats pre-computadas cuando se modifica un equipo.
    """
    if instance.empresa:
        invalidate_dashboard_cache(instance.empresa.id)
        try:
            instance.empresa.recalcular_stats_dashboard()
        except Exception as e:
            logger.error(f"Error recalculando stats de empresa '{instance.empresa.nombre}': {e}")
    else:
        # Si el equipo no tiene empresa, invalidar todo
        invalidate_dashboard_cache()


@receiver(post_save, sender=Calibracion)
@receiver(post_delete, sender=Calibracion)
def invalidate_cache_on_calibracion_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard y actualiza stats pre-computadas cuando se modifica una calibración.
    """
    if instance.equipo and instance.equipo.empresa:
        empresa = instance.equipo.empresa
        invalidate_dashboard_cache(empresa.id)
        try:
            empresa.recalcular_stats_dashboard()
        except Exception as e:
            logger.error(f"Error recalculando stats de empresa '{empresa.nombre}': {e}")
    else:
        invalidate_dashboard_cache()


@receiver(post_save, sender=Mantenimiento)
@receiver(post_delete, sender=Mantenimiento)
def invalidate_cache_on_mantenimiento_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard y actualiza stats pre-computadas cuando se modifica un mantenimiento.
    """
    if instance.equipo and instance.equipo.empresa:
        empresa = instance.equipo.empresa
        invalidate_dashboard_cache(empresa.id)
        try:
            empresa.recalcular_stats_dashboard()
        except Exception as e:
            logger.error(f"Error recalculando stats de empresa '{empresa.nombre}': {e}")
    else:
        invalidate_dashboard_cache()


@receiver(post_save, sender=Comprobacion)
@receiver(post_delete, sender=Comprobacion)
def invalidate_cache_on_comprobacion_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard y actualiza stats pre-computadas cuando se modifica una comprobación.
    """
    if instance.equipo and instance.equipo.empresa:
        empresa = instance.equipo.empresa
        invalidate_dashboard_cache(empresa.id)
        try:
            empresa.recalcular_stats_dashboard()
        except Exception as e:
            logger.error(f"Error recalculando stats de empresa '{empresa.nombre}': {e}")
    else:
        invalidate_dashboard_cache()


@receiver(post_save, sender=PrestamoEquipo)
@receiver(post_delete, sender=PrestamoEquipo)
def invalidate_cache_on_prestamo_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard cuando se crea, modifica o devuelve un préstamo.
    """
    if instance.empresa:
        invalidate_dashboard_cache(instance.empresa.id)
    else:
        invalidate_dashboard_cache()


@receiver(post_save, sender=CustomUser)
def crear_onboarding_para_trial(sender, instance, created, **kwargs):
    """Crea OnboardingProgress automáticamente para usuarios de empresas trial."""
    if (created
            and instance.empresa
            and getattr(instance.empresa, 'es_periodo_prueba', False)):
        OnboardingProgress.objects.get_or_create(usuario=instance)


@receiver(post_save, sender=CustomUser)
def asignar_permisos_al_crear_usuario(sender, instance, created, **kwargs):
    """Asigna permisos según el rol automáticamente cuando se crea un usuario nuevo."""
    if created and not instance.is_superuser:
        try:
            from core.views.registro import asignar_permisos_por_rol
            asignar_permisos_por_rol(instance)
        except Exception as e:
            logger.error(f"Error asignando permisos al usuario '{instance.username}': {e}")
