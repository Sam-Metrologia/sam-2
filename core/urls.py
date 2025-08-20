# core/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Importar las vistas de autenticación de Django

app_name = 'core'

urlpatterns = [
    # Autenticación
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('password_change/', views.cambiar_password, name='password_change'),
    path('password_change/done/', views.password_change_done, name='password_change_done'),
    
    # Perfil de usuario
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

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

    # Calibraciones
    path('equipos/<int:equipo_pk>/calibraciones/añadir/', views.añadir_calibracion, name='añadir_calibracion'),
    path('equipos/<int:equipo_pk>/calibraciones/<int:pk>/editar/', views.editar_calibracion, name='editar_calibracion'),
    path('equipos/<int:equipo_pk>/calibraciones/<int:pk>/eliminar/', views.eliminar_calibracion, name='eliminar_calibracion'),

    # Mantenimientos
    path('equipos/<int:equipo_pk>/mantenimientos/añadir/', views.añadir_mantenimiento, name='añadir_mantenimiento'),
    path('equipos/<int:equipo_pk>/mantenimientos/<int:pk>/editar/', views.editar_mantenimiento, name='editar_mantenimiento'),
    path('equipos/<int:equipo_pk>/mantenimientos/<int:pk>/eliminar/', views.eliminar_mantenimiento, name='eliminar_mantenimiento'),
    path('equipos/<int:equipo_pk>/mantenimientos/<int:pk>/detalle/', views.detalle_mantenimiento, name='detalle_mantenimiento'),

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

    # Usuarios
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/añadir/', views.añadir_usuario, name='añadir_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'), 
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    path('usuarios/<int:pk>/', views.detalle_usuario, name='detalle_usuario'),
    path('usuarios/<int:pk>/cambiar_password/', views.change_user_password, name='change_user_password'),
    path('usuarios/toggle_active/', views.toggle_user_active_status, name='toggle_user_active_status'), # <--- AÑADIR ESTA LÍNEA

    # Informes
    path('informes/', views.informes, name='informes'),
    path('informes/generar_zip/', views.generar_informe_zip, name='generar_informe_zip'),
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
]