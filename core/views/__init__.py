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

# Sistema de Mantenimiento Web
from .maintenance import (
    maintenance_dashboard,
    create_maintenance_task,
    maintenance_task_detail,
    maintenance_task_list,
    run_system_health_check,
    system_health_detail,
    system_health_history,
    task_status_api,
    task_logs_api
)

# API para Tareas Programadas (GitHub Actions)
from .scheduled_tasks_api import (
    health_check as scheduled_health_check,
    trigger_daily_notifications,
    trigger_daily_maintenance,
    trigger_cleanup_zips,
    trigger_weekly_overdue,
    trigger_check_trials,
    trigger_cleanup_notifications
)

# Confirmación Metrológica e Intervalos de Calibración
from .confirmacion import (
    confirmacion_metrologica,
    intervalos_calibracion,
    generar_pdf_confirmacion,
    generar_pdf_intervalos,
    guardar_confirmacion
)

# Comprobación Metrológica
from .comprobacion import (
    comprobacion_metrologica_view,
    guardar_comprobacion_json,
    generar_pdf_comprobacion
)

# Mantenimientos con Actividades
from .mantenimiento import (
    mantenimiento_actividades_view,
    guardar_mantenimiento_json,
    generar_pdf_mantenimiento
)

# Calendario de Actividades
from .calendario import (
    calendario_actividades,
    calendario_eventos_api,
    calendario_exportar_ical,
)

# Sistema de Aprobaciones
from .aprobaciones import (
    pagina_aprobaciones,
    aprobar_confirmacion,
    rechazar_confirmacion,
    aprobar_intervalos,
    rechazar_intervalos,
    aprobar_comprobacion,
    rechazar_comprobacion
)

# Auto-registro de Trial (público)
from .registro import solicitar_trial, trial_exitoso

# MIGRACIÓN COMPLETADA - Ya no necesitamos importar desde el monolítico
# Todas las funciones han sido migradas a sus respectivos módulos especializados