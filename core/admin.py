# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _ # Importar para las traducciones de fieldsets
from .models import (
    CustomUser, Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    BajaEquipo, Ubicacion, Procedimiento, Proveedor, ZipRequest, MetricasEficienciaMetrologica # Solo importar el modelo Proveedor general
)
from .forms import CustomUserCreationForm, CustomUserChangeForm

# Admin para CustomUser
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'empresa', 'rol_usuario']
    list_filter = ['is_staff', 'is_superuser', 'empresa', 'rol_usuario']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'empresa__nombre']
    ordering = ['username']

    # Definir fieldsets explícitamente para incluir 'empresa' sin duplicar 'groups'
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "empresa", "rol_usuario")}), # Añadido 'empresa' y 'rol_usuario' aquí
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password", "password2"),
            },
        ),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "empresa", "rol_usuario")}), # Añadido 'empresa' y 'rol_usuario' aquí
        (
            _("Permissions"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
    )

admin.site.register(CustomUser, CustomUserAdmin)


# Admin para Empresa
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nit', 'telefono', 'email', 'formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa'] # Añadidos nuevos campos
    search_fields = ['nombre', 'nit', 'email']
    list_filter = ['nombre']
    ordering = ['nombre']
    fieldsets = (
        (None, {
            'fields': ('nombre', 'nit', 'direccion', 'telefono', 'email', 'logo_empresa')
        }),
        ('Información de Formato', { # Nuevo fieldset para los campos de formato
            'fields': ('formato_version_empresa', 'formato_fecha_version_empresa', 'formato_codificacion_empresa'),
            'classes': ('collapse',), # Opcional: hacer que este fieldset sea colapsable
        }),
    )

# Admin para Equipo
@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo_interno', 'nombre', 'empresa', 'tipo_equipo', 'ubicacion',
        'estado', 'proxima_calibracion', 'proximo_mantenimiento',
        'proxima_comprobacion', 'responsable', 'error_maximo_permisible' 
    ]
    list_filter = [
        'empresa', 'estado', 'tipo_equipo',
        'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'
    ]
    search_fields = [
        'codigo_interno', 'nombre', 'marca', 'modelo', 'numero_serie',
        'empresa__nombre', 'ubicacion', 'responsable'
    ]
    raw_id_fields = ['empresa']
    date_hierarchy = 'fecha_registro'
    fieldsets = (
        ('Información General', {
            'fields': ('codigo_interno', 'nombre', 'empresa', 'tipo_equipo', 'marca', 'modelo', 'numero_serie', 'ubicacion', 'responsable', 'estado', 'fecha_adquisicion', 'observaciones', 'imagen_equipo')
        }),
        ('Especificaciones Técnicas', {
            'fields': ('rango_medida', 'resolucion', 'error_maximo_permisible')
        }),
        ('Documentos Adjuntos', {
            'fields': ('archivo_compra_pdf', 'ficha_tecnica_pdf', 'manual_pdf', 'otros_documentos_pdf')
        }),
        ('Control de Actividades y Frecuencias', { 
            'fields': (
                'fecha_ultima_calibracion', 'frecuencia_calibracion_meses',
                'fecha_ultimo_mantenimiento', 'frecuencia_mantenimiento_meses',
                'fecha_ultima_comprobacion', 'frecuencia_comprobacion_meses',
            )
        }),
        ('Fechas Calculadas y Formato', {
            'fields': ('fecha_registro', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion', 'version_formato', 'fecha_version_formato', 'codificacion_formato'),
            'classes': ('collapse',), 
        }),
    )
    readonly_fields = ['fecha_registro', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion']


# Admin para Calibracion
@admin.register(Calibracion)
class CalibracionAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'fecha_calibracion', 'nombre_proveedor', 'resultado', 'numero_certificado']
    list_filter = ['fecha_calibracion', 'resultado', 'equipo__empresa'] 
    search_fields = ['equipo__nombre', 'equipo__codigo_interno', 'nombre_proveedor', 'numero_certificado', 'observaciones'] 
    raw_id_fields = ['equipo']
    date_hierarchy = 'fecha_calibracion'
    ordering = ['-fecha_calibracion']
    fieldsets = (
        (None, {
            'fields': ('equipo', 'fecha_calibracion', 'nombre_proveedor', 'resultado', 'numero_certificado', 'observaciones')
        }),
        ('Documentos', {
            'fields': ('documento_calibracion', 'confirmacion_metrologica_pdf', 'intervalos_calibracion_pdf') # Añadido intervalos_calibracion_pdf
        }),
    )

# Admin para Mantenimiento
@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'fecha_mantenimiento', 'tipo_mantenimiento', 'nombre_proveedor', 'responsable']
    list_filter = ['tipo_mantenimiento', 'fecha_mantenimiento', 'equipo__empresa']
    search_fields = ['equipo__nombre', 'equipo__codigo_interno', 'nombre_proveedor', 'responsable', 'descripcion']
    raw_id_fields = ['equipo']
    date_hierarchy = 'fecha_mantenimiento'
    ordering = ['-fecha_mantenimiento']
    fieldsets = (
        (None, {
            'fields': ('equipo', 'fecha_mantenimiento', 'tipo_mantenimiento', 'nombre_proveedor', 'responsable', 'costo', 'descripcion')
        }),
        ('Documentos', {
            'fields': ('documento_mantenimiento',)
        }),
    )

# Admin para Comprobacion
@admin.register(Comprobacion)
class ComprobacionAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'fecha_comprobacion', 'nombre_proveedor', 'responsable', 'resultado']
    list_filter = ['resultado', 'fecha_comprobacion', 'equipo__empresa']
    search_fields = ['equipo__nombre', 'equipo__codigo_interno', 'nombre_proveedor', 'responsable', 'observaciones']
    raw_id_fields = ['equipo']
    date_hierarchy = 'fecha_comprobacion'
    ordering = ['-fecha_comprobacion']
    fieldsets = (
        (None, {
            'fields': ('equipo', 'fecha_comprobacion', 'nombre_proveedor', 'responsable', 'resultado', 'observaciones')
        }),
        ('Documentos', {
            'fields': ('documento_comprobacion',)
        }),
    )

# Admin para BajaEquipo
@admin.register(BajaEquipo)
class BajaEquipoAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'razon_baja', 'fecha_baja', 'dado_de_baja_por']
    list_filter = ['razon_baja', 'fecha_baja', 'dado_de_baja_por']
    search_fields = ['equipo__codigo_interno', 'equipo__nombre', 'razon_baja', 'observaciones']
    raw_id_fields = ['equipo', 'dado_de_baja_por']
    date_hierarchy = 'fecha_baja'
    readonly_fields = ['fecha_baja', 'dado_de_baja_por']


# Admin para Ubicacion
@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']

# Admin para Procedimiento
@admin.register(Procedimiento)
class ProcedimientoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'codigo', 'version', 'fecha_emision']
    list_filter = ['fecha_emision']
    search_fields = ['nombre', 'codigo']
    date_hierarchy = 'fecha_emision'
    ordering = ['nombre']

# NUEVO ADMIN: Proveedor General (los ProveedorCalibracion, Mantenimiento, Comprobacion ya no son necesarios)
@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['nombre_empresa', 'empresa', 'tipo_servicio', 'nombre_contacto', 'numero_contacto', 'correo_electronico']
    list_filter = ['tipo_servicio', 'empresa']
    search_fields = ['nombre_empresa', 'nombre_contacto', 'correo_electronico', 'alcance', 'servicio_prestado', 'empresa__nombre']
    ordering = ['nombre_empresa']
    raw_id_fields = ['empresa']
    fieldsets = (
        (None, {
            'fields': ('empresa', 'tipo_servicio', 'nombre_empresa', 'nombre_contacto', 'numero_contacto', 'correo_electronico', 'pagina_web')
        }),
        ('Detalles del Servicio', {
            'fields': ('alcance', 'servicio_prestado')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filtrar por la empresa del usuario actual si no es superusuario
        return qs.filter(empresa=request.user.empresa)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa" and not request.user.is_superuser:
            kwargs["queryset"] = Empresa.objects.filter(pk=request.user.empresa.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.empresa = request.user.empresa # Asegurar que se asigne la empresa del usuario actual
        super().save_model(request, obj, form, change)


# ================================
# ADMIN PARA SISTEMA DE COLA ZIP
# ================================

@admin.register(ZipRequest)
class ZipRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'empresa', 'status', 'position_in_queue', 'parte_numero', 'created_at', 'file_size_mb')
    list_filter = ('status', 'empresa', 'created_at', 'parte_numero')
    search_fields = ('user__username', 'user__email', 'empresa__nombre')
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'file_size_mb', 'current_position', 'estimated_wait_time')
    ordering = ('-created_at',)

    fieldsets = (
        ('Información Básica', {
            'fields': ('user', 'empresa', 'status', 'parte_numero')
        }),
        ('Cola y Timing', {
            'fields': ('position_in_queue', 'current_position', 'estimated_wait_time', 'created_at', 'started_at', 'completed_at')
        }),
        ('Archivo Generado', {
            'fields': ('file_path', 'file_size', 'file_size_mb', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def file_size_mb(self, obj):
        """Mostrar tamaño del archivo en MB."""
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "-"
    file_size_mb.short_description = "Tamaño (MB)"

    def current_position(self, obj):
        """Mostrar posición actual en la cola."""
        return obj.get_current_position()
    current_position.short_description = "Posición Actual"

    def estimated_wait_time(self, obj):
        """Mostrar tiempo estimado de espera."""
        wait_time = obj.get_estimated_wait_time()
        if wait_time > 0:
            return f"{wait_time} minutos"
        return "-"
    estimated_wait_time.short_description = "Tiempo Estimado"

    def get_queryset(self, request):
        """Filtrar por empresa para usuarios no superuser."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser and hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs

    def has_add_permission(self, request):
        """Solo superusuarios pueden agregar solicitudes manualmente."""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Solo superusuarios pueden modificar solicitudes."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Solo superusuarios pueden eliminar solicitudes."""
        return request.user.is_superuser
# Registro del modelo de Métricas de Eficiencia
admin.site.register(MetricasEficienciaMetrologica)

# Registro del modelo de Notificaciones de Vencimiento
from .models import NotificacionVencimiento

@admin.register(NotificacionVencimiento)
class NotificacionVencimientoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'tipo_actividad', 'fecha_vencimiento', 'numero_recordatorio', 'actividad_completada', 'fecha_notificacion')
    list_filter = ('tipo_actividad', 'actividad_completada', 'numero_recordatorio', 'fecha_notificacion')
    search_fields = ('equipo__codigo_interno', 'equipo__nombre')
    date_hierarchy = 'fecha_notificacion'
    readonly_fields = ('fecha_notificacion',)
    ordering = ('-fecha_notificacion',)
