# core/models/_signals.py
# Todos los @receiver decorators del sistema de modelos

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from .equipment import Equipo, BajaEquipo
from .activities import Calibracion, Mantenimiento, Comprobacion
from core.constants import ESTADO_DE_BAJA, ESTADO_ACTIVO

logger = logging.getLogger('core')


@receiver(post_save, sender=Calibracion)
def update_equipo_calibracion_info(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima calibración del equipo al guardar una calibración."""
    equipo = instance.equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        equipo.fecha_ultima_calibracion = None

    # Recalcular la próxima calibración, respetando el estado del equipo
    if equipo.estado not in ['De Baja', 'Inactivo']: # SOLO calcular si está Activo, En Mantenimiento, etc.
        equipo.calcular_proxima_calibracion()
    else:
        equipo.proxima_calibracion = None # Si está de baja o inactivo, no hay próxima programación

    equipo.save(update_fields=['fecha_ultima_calibracion', 'proxima_calibracion'])

@receiver(post_delete, sender=Calibracion)
def update_equipo_calibracion_info_on_delete(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima calibración del equipo al eliminar una calibración."""
    equipo = instance.equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        equipo.fecha_ultima_calibracion = None

    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proxima_calibracion()
    else:
        equipo.proxima_calibracion = None

    equipo.save(update_fields=['fecha_ultima_calibracion', 'proxima_calibracion'])


@receiver(post_save, sender=Mantenimiento)
def update_equipo_mantenimiento_info(sender, instance, **kwargs):
    """Actualiza la fecha del último y próximo mantenimiento del equipo al guardar un mantenimiento."""
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None

    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proximo_mantenimiento()
    else:
        equipo.proximo_mantenimiento = None

    equipo.save(update_fields=['fecha_ultimo_mantenimiento', 'proximo_mantenimiento'])


@receiver(post_delete, sender=Mantenimiento)
def update_equipo_mantenimiento_info_on_delete(sender, instance, **kwargs):
    """Actualiza la fecha del último y próximo mantenimiento del equipo al eliminar un mantenimiento."""
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None

    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proximo_mantenimiento()
    else:
        equipo.proximo_mantenimiento = None

    equipo.save(update_fields=['fecha_ultimo_mantenimiento', 'proximo_mantenimiento'])


@receiver(post_save, sender=Comprobacion)
def update_equipo_comprobacion_info(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima comprobación del equipo al guardar una comprobación."""
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None

    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proxima_comprobacion()
    else:
        equipo.proxima_comprobacion = None

    equipo.save(update_fields=['fecha_ultima_comprobacion', 'proxima_comprobacion'])

@receiver(post_delete, sender=Comprobacion)
def update_equipo_comprobacion_info_on_delete(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima comprobación del equipo al eliminar una comprobación."""
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None

    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proxima_comprobacion()
    else:
        equipo.proxima_comprobacion = None

    equipo.save(update_fields=['fecha_ultima_comprobacion', 'proxima_comprobacion'])


@receiver(post_save, sender=BajaEquipo)
def set_equipo_de_baja(sender, instance, created, **kwargs):
    if created: # Solo actuar cuando se crea un nuevo registro de baja
        equipo = instance.equipo
        # Si el equipo no está ya 'De Baja', se cambia el estado
        if equipo.estado != ESTADO_DE_BAJA:
            equipo.estado = ESTADO_DE_BAJA
            # Poner a None las próximas fechas si está de baja
            equipo.proxima_calibracion = None
            equipo.proximo_mantenimiento = None
            equipo.proxima_comprobacion = None
            equipo.save(update_fields=['estado', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])

@receiver(post_delete, sender=BajaEquipo)
def set_equipo_activo_on_delete_baja(sender, instance, **kwargs):
    equipo = instance.equipo
    # Solo cambiar a 'Activo' si NO quedan otros registros de baja para este equipo
    if not BajaEquipo.objects.filter(equipo=equipo).exists():
        if equipo.estado == ESTADO_DE_BAJA: # Solo cambiar si estaba en estado 'De Baja' por este registro
            equipo.estado = ESTADO_ACTIVO # O el estado por defecto que desees
            # Recalcular las próximas fechas después de reactivar
            equipo.calcular_proxima_calibracion()
            equipo.calcular_proximo_mantenimiento()
            equipo.calcular_proxima_comprobacion()
            equipo.save(update_fields=['estado', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])
