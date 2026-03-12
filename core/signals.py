# core/signals.py
# Signals for cache invalidation

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Equipo, Calibracion, Mantenimiento, Comprobacion, CustomUser, OnboardingProgress

logger = logging.getLogger(__name__)


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


@receiver(post_save, sender=CustomUser)
def crear_onboarding_para_trial(sender, instance, created, **kwargs):
    """Crea OnboardingProgress automáticamente para usuarios de empresas trial."""
    if (created
            and instance.empresa
            and getattr(instance.empresa, 'es_periodo_prueba', False)):
        OnboardingProgress.objects.get_or_create(usuario=instance)
