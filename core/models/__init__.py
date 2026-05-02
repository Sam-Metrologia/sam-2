# core/models/__init__.py
# Re-exporta todos los modelos del paquete core/models/

import logging

from .common import get_upload_path, meses_decimales_a_relativedelta
from .empresa import Empresa, PlanSuscripcion, EmpresaFormatoLog
from .users import CustomUser, OnboardingProgress
from .catalogs import Unidad, Ubicacion, Procedimiento, Proveedor
from .equipment import Equipo, BajaEquipo, NotificacionVencimiento
from .activities import Calibracion, Mantenimiento, Comprobacion
from .loans import AgrupacionPrestamo, PrestamoEquipo
from .documents import Documento, ZipRequest, NotificacionZip
from .payments import TerminosYCondiciones, AceptacionTerminos, TransaccionPago, LinkPago
from .system import (
    EmailConfiguration, SystemScheduleConfig, MetricasEficienciaMetrologica,
    MaintenanceTask, CommandLog, SystemHealthCheck
)

# Signals — importar AL FINAL
from . import _signals  # noqa: F401
from ._signals import update_equipo_calibracion_info

logger = logging.getLogger('core')

__all__ = [
    'get_upload_path', 'meses_decimales_a_relativedelta',
    'Empresa', 'PlanSuscripcion', 'EmpresaFormatoLog',
    'CustomUser', 'OnboardingProgress',
    'Unidad', 'Ubicacion', 'Procedimiento', 'Proveedor',
    'Equipo', 'BajaEquipo', 'NotificacionVencimiento',
    'Calibracion', 'Mantenimiento', 'Comprobacion',
    'AgrupacionPrestamo', 'PrestamoEquipo',
    'Documento', 'ZipRequest', 'NotificacionZip',
    'TerminosYCondiciones', 'AceptacionTerminos', 'TransaccionPago', 'LinkPago',
    'EmailConfiguration', 'SystemScheduleConfig', 'MetricasEficienciaMetrologica',
    'MaintenanceTask', 'CommandLog', 'SystemHealthCheck',
    'update_equipo_calibracion_info',
]
