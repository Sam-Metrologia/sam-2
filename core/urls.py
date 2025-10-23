# core/urls.py

from django.urls import path
from . import views
from . import admin_views
from . import zip_functions  # Import for ZIP system
# Eliminadas importaciones de debug (views_debug, views_debug_logo, views_fix_logos)
from django.contrib.auth import views as auth_views # Importar las vistas de autenticación de Django

app_name = 'core'

urlpatterns = [
    # Autenticación
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('password_change/', views.cambiar_password, name='password_change'),
    path('password_change/done/', views.password_change_done, name='password_change_done'),

    # Términos y Condiciones
    path('terminos-condiciones/', views.aceptar_terminos, name='aceptar_terminos'),
    path('terminos-condiciones/rechazar/', views.rechazar_terminos, name='rechazar_terminos'),
    path('terminos-condiciones/pdf/', views.ver_terminos_pdf, name='ver_terminos_pdf'),
    path('mi-aceptacion-terminos/', views.mi_aceptacion_terminos, name='mi_aceptacion_terminos'),

    # Perfil de usuario
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-gerencia/', views.dashboard_gerencia, name='dashboard_gerencia'),
    path('panel-decisiones/', views.panel_decisiones, name='panel_decisiones'),
    path('api/equipos-salud-detalles/', views.get_equipos_salud_detalles, name='get_equipos_salud_detalles'),
    path('exportar_analisis_financiero/', views.exportar_analisis_financiero_excel, name='exportar_analisis_financiero'),
    path('api/chart-details/', views.get_chart_details, name='get_chart_details'),

    # Equipos
    path('', views.home, name='home'), # Listado de equipos como página principal
    path('equipos/añadir/', views.añadir_equipo, name='añadir_equipo'),
    path('equipos/<int:pk>/', views.detalle_equipo, name='detalle_equipo'),
    path('equipos/<int:pk>/editar/', views.editar_equipo, name='editar_equipo'),
    path('equipos/<int:pk>/eliminar/', views.eliminar_equipo, name='eliminar_equipo'),
    path('equipos/<int:equipo_pk>/dar_baja/', views.dar_baja_equipo, name='dar_baja_equipo'),
    path('equipos/<int:equipo_pk>/inactivar/', views.inactivar_equipo, name='inactivar_equipo'),
    path('equipos/<int:equipo_pk>/activar/', views.activar_equipo, name='activar_equipo'),
    path('equipos/importar_excel/', views.importar_equipos_excel, name='importar_equipos_excel'),
    path('equipos/plantilla_excel/', views.descargar_plantilla_excel, name='descargar_plantilla_excel'), 

    # Calibraciones
    path('equipos/<int:equipo_pk>/calibraciones/añadir/', views.añadir_calibracion, name='añadir_calibracion'),
    path('equipos/<int:equipo_pk>/calibraciones/<int:pk>/editar/', views.editar_calibracion, name='editar_calibracion'),
    path('equipos/<int:equipo_pk>/calibraciones/<int:pk>/eliminar/', views.eliminar_calibracion, name='eliminar_calibracion'),

    # Mantenimientos
    path('equipos/<int:equipo_pk>/mantenimientos/añadir/', views.añadir_mantenimiento, name='añadir_mantenimiento'),
    path('equipos/<int:equipo_pk>/mantenimientos/<int:pk>/editar/', views.editar_mantenimiento, name='editar_mantenimiento'),
    path('equipos/<int:equipo_pk>/mantenimientos/<int:pk>/eliminar/', views.eliminar_mantenimiento, name='eliminar_mantenimiento'),
    path('equipos/<int:equipo_pk>/mantenimientos/<int:pk>/detalle/', views.detalle_mantenimiento, name='detalle_mantenimiento'),
    path('mantenimientos/<int:mantenimiento_pk>/archivo/', views.ver_archivo_mantenimiento, name='ver_archivo_mantenimiento'),

    # Comprobaciones
    path('equipos/<int:equipo_pk>/comprobaciones/añadir/', views.añadir_comprobacion, name='añadir_comprobacion'),
    path('equipos/<int:equipo_pk>/comprobaciones/<int:pk>/editar/', views.editar_comprobacion, name='editar_comprobacion'),
    path('equipos/<int:equipo_pk>/comprobaciones/<int:pk>/eliminar/', views.eliminar_comprobacion, name='eliminar_comprobacion'),

    # Ubicaciones
    path('ubicaciones/', views.listar_ubicaciones, name='listar_ubicaciones'),
    path('ubicaciones/añadir/', views.añadir_ubicacion, name='añadir_ubicacion'),
    path('ubicaciones/<int:pk>/editar/', views.editar_ubicacion, name='editar_ubicacion'),
    path('ubicaciones/<int:pk>/eliminar/', views.eliminar_ubicacion, name='eliminar_ubicacion'),

    # Proveedores (General)
    path('proveedores/', views.listar_proveedores, name='listar_proveedores'),
    path('proveedores/añadir/', views.añadir_proveedor, name='añadir_proveedor'),
    path('proveedores/<int:pk>/editar/', views.editar_proveedor, name='editar_proveedor'),
    path('proveedores/<int:pk>/eliminar/', views.eliminar_proveedor, name='eliminar_proveedor'),
    path('proveedores/<int:pk>/detalle/', views.detalle_proveedor, name='detalle_proveedor'),

    # Procedimientos
    path('procedimientos/', views.listar_procedimientos, name='listar_procedimientos'),
    path('procedimientos/añadir/', views.añadir_procedimiento, name='añadir_procedimiento'),
    path('procedimientos/<int:pk>/editar/', views.editar_procedimiento, name='editar_procedimiento'),
    path('procedimientos/<int:pk>/eliminar/', views.eliminar_procedimiento, name='eliminar_procedimiento'),

    # Empresas
    path('empresas/', views.listar_empresas, name='listar_empresas'),
    path('empresas/añadir/', views.añadir_empresa, name='añadir_empresa'),
    path('empresas/<int:pk>/', views.detalle_empresa, name='detalle_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('empresas/<int:pk>/eliminar/', views.eliminar_empresa, name='eliminar_empresa'),
    path('empresas/<int:empresa_pk>/añadir_usuario/', views.añadir_usuario_a_empresa, name='añadir_usuario_a_empresa'),
    path('empresas/<int:pk>/editar_formato/', views.editar_empresa_formato, name='editar_empresa_formato'),
    path('empresas/<int:empresa_id>/activar_plan_pagado/', views.activar_plan_pagado, name='activar_plan_pagado'),

    # Usuarios
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/añadir/', views.añadir_usuario, name='añadir_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'), 
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    path('usuarios/<int:pk>/', views.detalle_usuario, name='detalle_usuario'),
    path('usuarios/<int:pk>/cambiar_password/', views.change_user_password, name='change_user_password'),
    # URL de redirección temporal para compatibilidad con URLs antiguas
    path('usuarios/<int:pk>/password/', views.redirect_to_change_password, name='redirect_to_change_password'),
    path('usuarios/toggle_active/', views.toggle_user_active_status, name='toggle_user_active_status'), # <--- AÑADIR ESTA LÍNEA
    path('usuarios/toggle_download_permission/', views.toggle_download_permission, name='toggle_download_permission'),

    # API endpoints para progreso en tiempo real (Fase 3)
    path('api/zip-progress/', views.zip_progress_api, name='zip_progress_api'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),

    # Dashboard de monitoreo del sistema (solo superusuarios)
    path('system-monitor/', views.system_monitor_dashboard, name='system_monitor'),

    # Informes
    path('informes/', views.informes, name='informes'),
    path('informes/generar_zip/', views.generar_informe_zip, name='generar_informe_zip'),
    path('informes/dashboard_excel/', views.generar_informe_dashboard_excel, name='generar_informe_dashboard_excel'),
    path('informes/vencimientos_pdf/', views.informe_vencimientos_pdf, name='informe_vencimientos_pdf'),
    path('informes/actividades_programadas/', views.programmed_activities_list, name='programmed_activities_list'),
    path('informes/exportar_excel/', views.exportar_equipos_excel, name='exportar_equipos_excel'),
    path('informes/hoja_vida_pdf/<int:pk>/', views.generar_hoja_vida_pdf, name='generar_hoja_vida_pdf'),

    # URL para AJAX de actualización de formato de empresa (se mantiene para usos AJAX específicos)
    path('update_empresa_formato/', views.update_empresa_formato, name='update_empresa_formato'),
    # NUEVA: URL para el endpoint AJAX de añadir mensajes
    path('add_message/', views.add_message, name='add_message'),

    # Acceso Denegado
    path('access_denied/', views.access_denied, name='access_denied'),

    # Panel de Administración del Sistema (solo superusuarios)
    path('admin/system/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/system/maintenance/', admin_views.system_maintenance, name='admin_maintenance'),
    path('admin/system/notifications/', admin_views.system_notifications, name='admin_notifications'),
    path('admin/system/backup/', admin_views.system_backup, name='admin_backup'),
    path('admin/system/backup/download/<path:filename>/', admin_views.download_backup, name='download_backup'),
    path('admin/system/monitoring/', admin_views.system_monitoring, name='admin_monitoring'),
    path('admin/system/schedule/', admin_views.system_schedule, name='admin_schedule'),
    path('admin/system/email/', admin_views.email_configuration, name='admin_email_config'),
    path('admin/system/history/', admin_views.execution_history, name='admin_history'),
    path('admin/system/tests/', admin_views.run_tests_panel, name='run_tests_panel'),

    # API endpoints para el panel de administración
    path('api/admin/status/', admin_views.api_system_status, name='api_system_status'),
    path('api/admin/execute/', admin_views.api_execute_command, name='api_execute_command'),

    # Diagnóstico temporal de cache
    path('cache_diagnostics/', views.cache_diagnostics, name='cache_diagnostics'),

    # Sistema de Cola para ZIP
    path('solicitar_zip/', zip_functions.solicitar_zip, name='solicitar_zip'),
    path('zip_status/<int:request_id>/', zip_functions.zip_status, name='zip_status'),
    path('download_zip/<int:request_id>/', zip_functions.download_zip, name='download_zip'),
    path('cancel_zip/<int:request_id>/', zip_functions.cancel_zip_request, name='cancel_zip_request'),
    path('my_zip_requests/', zip_functions.my_zip_requests, name='my_zip_requests'),
    # Endpoint para procesamiento compatible con Render
    path('trigger_zip_processing/', zip_functions.trigger_zip_processing, name='trigger_zip_processing'),
    # Procesamiento manual para superusuarios
    path('manual_process_zip/', zip_functions.manual_process_zip, name='manual_process_zip'),

    # URLs para eliminación suave y restauración de empresas
    path('admin/companies/deleted/', admin_views.deleted_companies, name='deleted_companies'),
    path('admin/companies/<int:empresa_id>/restore/', admin_views.restore_company, name='restore_company'),
    path('admin/companies/<int:empresa_id>/soft-delete/', admin_views.soft_delete_company, name='soft_delete_company'),
    path('admin/companies/cleanup/', admin_views.cleanup_old_companies, name='cleanup_old_companies'),

    # === URLs DE DEBUG ELIMINADAS ===
    # Eliminadas rutas de debug: s3_diagnostics, file_upload_test, logo_diagnostics,
    # test_logo_upload, fix_mi_logo, lista_empresas_sin_logo

    # ==============================================================================
    # SISTEMA DE MANTENIMIENTO WEB (Solo Superusuarios)
    # ==============================================================================
    path('maintenance/', views.maintenance_dashboard, name='maintenance_dashboard'),
    path('maintenance/task/create/', views.create_maintenance_task, name='create_maintenance_task'),
    path('maintenance/task/<int:task_id>/', views.maintenance_task_detail, name='maintenance_task_detail'),
    path('maintenance/tasks/', views.maintenance_task_list, name='maintenance_task_list'),
    path('maintenance/health/check/', views.run_system_health_check, name='run_system_health_check'),
    path('maintenance/health/<int:check_id>/', views.system_health_detail, name='system_health_detail'),
    path('maintenance/health/history/', views.system_health_history, name='system_health_history'),

    # APIs para auto-refresh
    path('api/maintenance/task/<int:task_id>/status/', views.task_status_api, name='task_status_api'),
    path('api/maintenance/task/<int:task_id>/logs/', views.task_logs_api, name='task_logs_api'),

    # ==============================================================================
    # API PARA TAREAS PROGRAMADAS (GitHub Actions)
    # ==============================================================================
    path('api/scheduled/health/', views.scheduled_health_check, name='scheduled_health_check'),
    path('api/scheduled/notifications/daily/', views.trigger_daily_notifications, name='trigger_daily_notifications'),
    path('api/scheduled/maintenance/daily/', views.trigger_daily_maintenance, name='trigger_daily_maintenance'),
    path('api/scheduled/cleanup/zips/', views.trigger_cleanup_zips, name='trigger_cleanup_zips'),
    path('api/scheduled/notifications/weekly-overdue/', views.trigger_weekly_overdue, name='trigger_weekly_overdue'),
    path('api/scheduled/check-trials/', views.trigger_check_trials, name='trigger_check_trials'),
    path('api/scheduled/cleanup/notifications/', views.trigger_cleanup_notifications, name='trigger_cleanup_notifications'),
]