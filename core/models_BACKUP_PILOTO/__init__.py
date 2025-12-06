# core/models/__init__.py
"""
Módulo de modelos de SAM Metrología
Este archivo centraliza todos los modelos para mantener compatibilidad con imports existentes.

REFACTORIZACIÓN EN PROGRESO:
- Fase 1 (PILOTO): Modelos de catálogos movidos a catalogos.py
- Fase 2-N: Resto de modelos se moverán progresivamente

IMPORTANTE: Este __init__.py garantiza que los imports existentes sigan funcionando:
    from core.models import Equipo, Empresa, Ubicacion  # Funciona igual que antes
"""

# ==============================================================================
# PASO 1: Importar funciones auxiliares de base.py
# ==============================================================================
from .base import meses_decimales_a_relativedelta, logger

# ==============================================================================
# PASO 2: Importar modelos YA REFACTORIZADOS (catalogos.py - PILOTO)
# ==============================================================================
from .catalogos import (
    Unidad,
    Ubicacion,
    Procedimiento,
    Proveedor,
)

# ==============================================================================
# PASO 3: Importar TODOS los demás modelos desde models.py (TEMPORAL)
# ==============================================================================
# NOTA: Estos imports son del archivo models.py original
# Se irán eliminando a medida que se refactoricen a archivos separados

# Importar todo desde el módulo models original (ahora renombrado a _legacy)
# Para la prueba piloto, vamos a importar directamente desde el archivo original
import sys
import os
from pathlib import Path

# Importar dinámicamente desde models.py
models_path = Path(__file__).parent.parent / 'models.py'
if models_path.exists():
    # Importar módulo models.py como módulo legacy
    import importlib.util
    spec = importlib.util.spec_from_file_location("core.models_legacy", models_path)
    models_legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_legacy)

    # Exportar modelos que AÚN NO están refactorizados
    # (Todos excepto Unidad, Ubicacion, Procedimiento, Proveedor que ya están en catalogos.py)
    Empresa = models_legacy.Empresa
    PlanSuscripcion = models_legacy.PlanSuscripcion
    CustomUser = models_legacy.CustomUser
    Equipo = models_legacy.Equipo
    Calibracion = models_legacy.Calibracion
    Mantenimiento = models_legacy.Mantenimiento
    Comprobacion = models_legacy.Comprobacion
    BajaEquipo = models_legacy.BajaEquipo
    Documento = models_legacy.Documento
    ZipRequest = models_legacy.ZipRequest
    NotificacionZip = models_legacy.NotificacionZip
    EmailConfiguration = models_legacy.EmailConfiguration
    SystemScheduleConfig = models_legacy.SystemScheduleConfig
    MetricasEficienciaMetrologica = models_legacy.MetricasEficienciaMetrologica
    NotificacionVencimiento = models_legacy.NotificacionVencimiento
    TerminosYCondiciones = models_legacy.TerminosYCondiciones
    AceptacionTerminos = models_legacy.AceptacionTerminos
    MaintenanceTask = models_legacy.MaintenanceTask
    CommandLog = models_legacy.CommandLog
    SystemHealthCheck = models_legacy.SystemHealthCheck

    # También exportar la función get_upload_path original (por ahora)
    get_upload_path = models_legacy.get_upload_path

# ==============================================================================
# PASO 4: Definir __all__ para exports explícitos
# ==============================================================================
__all__ = [
    # Funciones auxiliares
    'meses_decimales_a_relativedelta',
    'get_upload_path',
    'logger',

    # Modelos de catálogos (YA REFACTORIZADOS)
    'Unidad',
    'Ubicacion',
    'Procedimiento',
    'Proveedor',

    # Modelos que AÚN FALTAN refactorizar (desde models.py)
    'Empresa',
    'PlanSuscripcion',
    'CustomUser',
    'Equipo',
    'Calibracion',
    'Mantenimiento',
    'Comprobacion',
    'BajaEquipo',
    'Documento',
    'ZipRequest',
    'NotificacionZip',
    'EmailConfiguration',
    'SystemScheduleConfig',
    'MetricasEficienciaMetrologica',
    'NotificacionVencimiento',
    'TerminosYCondiciones',
    'AceptacionTerminos',
    'MaintenanceTask',
    'CommandLog',
    'SystemHealthCheck',
]
