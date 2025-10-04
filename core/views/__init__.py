# core/views/__init__.py
# Archivo de inicialización para el paquete de views modulares

# Importar todas las views desde los módulos - MIGRACIÓN COMPLETADA
from .dashboard import *
from .dashboard_gerencia_simple import dashboard_gerencia
from .panel_decisiones import panel_decisiones, get_equipos_salud_detalles
from .equipment import *
from .activities import *
from .companies import *
from .reports import *
from .admin import *
from .base import *
from .export_financiero import *
from .terminos import aceptar_terminos, rechazar_terminos, ver_terminos_pdf, mi_aceptacion_terminos

# Funciones ZIP que están en zip_functions
from ..zip_functions import (
    solicitar_zip,
    zip_status,
    download_zip,
    cancel_zip_request,
    my_zip_requests,
    trigger_zip_processing,
    manual_process_zip
)

# MIGRACIÓN COMPLETADA - Ya no necesitamos importar desde el monolítico
# Todas las funciones han sido migradas a sus respectivos módulos especializados