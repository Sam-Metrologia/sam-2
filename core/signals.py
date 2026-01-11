# core/signals.py
# Signals for cache invalidation

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Equipo, Calibracion, Mantenimiento, Comprobacion


def invalidate_dashboard_cache(empresa_id=None):
    """
    Invalida el cache del dashboard.

    Si se proporciona empresa_id, invalida solo el cache de esa empresa.
    Si no se proporciona, invalida todos los caches del dashboard.

    Args:
        empresa_id: ID de la empresa cuyo cache se debe invalidar
    """
    if empresa_id:
        # Invalidar cache específico de la empresa
        # Nota: No podemos invalidar por usuario específico, así que invalidamos
        # todos los usuarios que vean esta empresa (superusuarios y usuarios de la empresa)
        cache_pattern = f"dashboard_*_{empresa_id}"
        # También invalidar el cache 'all' para superusuarios
        cache_pattern_all = "dashboard_*_all"

        # Django cache no soporta delete_pattern nativamente con LocalMemCache
        # Solución: invalidar limpiando todo el cache del dashboard
        # En producción con Redis, se puede usar delete_pattern
        try:
            # Intentar con Redis delete_pattern si está disponible
            cache.delete_pattern(cache_pattern)
            cache.delete_pattern(cache_pattern_all)
        except AttributeError:
            # Fallback: limpiar todo el cache
            # Esto es seguro porque el cache del dashboard se regenera rápido
            cache.clear()
    else:
        # Invalidar todos los caches del dashboard
        cache.clear()


@receiver(post_save, sender=Equipo)
@receiver(post_delete, sender=Equipo)
def invalidate_cache_on_equipo_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard cuando se modifica un equipo.
    """
    if instance.empresa:
        invalidate_dashboard_cache(instance.empresa.id)
    else:
        # Si el equipo no tiene empresa, invalidar todo
        invalidate_dashboard_cache()


@receiver(post_save, sender=Calibracion)
@receiver(post_delete, sender=Calibracion)
def invalidate_cache_on_calibracion_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard cuando se modifica una calibración.
    """
    if instance.equipo and instance.equipo.empresa:
        invalidate_dashboard_cache(instance.equipo.empresa.id)
    else:
        invalidate_dashboard_cache()


@receiver(post_save, sender=Mantenimiento)
@receiver(post_delete, sender=Mantenimiento)
def invalidate_cache_on_mantenimiento_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard cuando se modifica un mantenimiento.
    """
    if instance.equipo and instance.equipo.empresa:
        invalidate_dashboard_cache(instance.equipo.empresa.id)
    else:
        invalidate_dashboard_cache()


@receiver(post_save, sender=Comprobacion)
@receiver(post_delete, sender=Comprobacion)
def invalidate_cache_on_comprobacion_change(sender, instance, **kwargs):
    """
    Invalida el cache del dashboard cuando se modifica una comprobación.
    """
    if instance.equipo and instance.equipo.empresa:
        invalidate_dashboard_cache(instance.equipo.empresa.id)
    else:
        invalidate_dashboard_cache()
