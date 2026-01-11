# core/constants.py
"""
Constantes centralizadas para SAM Metrología

Este archivo contiene todas las constantes utilizadas en la aplicación
para evitar valores hardcodeados dispersos en el código.

Creado: 11 de Enero 2026
Día 3 del Plan Consolidado
"""

# ============================================================================
# ESTADOS DE EQUIPOS
# ============================================================================

ESTADO_ACTIVO = 'Activo'
ESTADO_INACTIVO = 'Inactivo'
ESTADO_EN_CALIBRACION = 'En Calibración'
ESTADO_EN_MANTENIMIENTO = 'En Mantenimiento'
ESTADO_DE_BAJA = 'De Baja'
ESTADO_EN_PRESTAMO = 'En Préstamo'

EQUIPO_ESTADO_CHOICES = [
    (ESTADO_ACTIVO, 'Activo'),
    (ESTADO_INACTIVO, 'Inactivo'),
    (ESTADO_EN_CALIBRACION, 'En Calibración'),
    (ESTADO_EN_MANTENIMIENTO, 'En Mantenimiento'),
    (ESTADO_DE_BAJA, 'De Baja'),
    (ESTADO_EN_PRESTAMO, 'En Préstamo'),
]

# ============================================================================
# TIPOS DE EQUIPOS
# ============================================================================

TIPO_EQUIPO_MEDICION = 'Medición'
TIPO_EQUIPO_ENSAYO = 'Ensayo'
TIPO_EQUIPO_PATRON = 'Patrón'
TIPO_EQUIPO_AUXILIAR = 'Auxiliar'

TIPO_EQUIPO_CHOICES = [
    (TIPO_EQUIPO_MEDICION, 'Medición'),
    (TIPO_EQUIPO_ENSAYO, 'Ensayo'),
    (TIPO_EQUIPO_PATRON, 'Patrón'),
    (TIPO_EQUIPO_AUXILIAR, 'Auxiliar'),
]

# ============================================================================
# TIPOS DE SERVICIOS
# ============================================================================

SERVICIO_CALIBRACION = 'Calibración'
SERVICIO_VERIFICACION = 'Verificación'
SERVICIO_ENSAYO = 'Ensayo'
SERVICIO_OTRO = 'Otro'

TIPO_SERVICIO_CHOICES = [
    (SERVICIO_CALIBRACION, 'Calibración'),
    (SERVICIO_VERIFICACION, 'Verificación'),
    (SERVICIO_ENSAYO, 'Ensayo'),
    (SERVICIO_OTRO, 'Otro'),
]

# ============================================================================
# TIPOS DE MANTENIMIENTO
# ============================================================================

MANTENIMIENTO_PREVENTIVO = 'Preventivo'
MANTENIMIENTO_CORRECTIVO = 'Correctivo'
MANTENIMIENTO_PREDICTIVO = 'Predictivo'

TIPO_MANTENIMIENTO_CHOICES = [
    (MANTENIMIENTO_PREVENTIVO, 'Preventivo'),
    (MANTENIMIENTO_CORRECTIVO, 'Correctivo'),
    (MANTENIMIENTO_PREDICTIVO, 'Predictivo'),
]

# ============================================================================
# ESTADOS DE PRÉSTAMOS
# ============================================================================

PRESTAMO_ACTIVO = 'ACTIVO'
PRESTAMO_DEVUELTO = 'DEVUELTO'
PRESTAMO_VENCIDO = 'VENCIDO'
PRESTAMO_CANCELADO = 'CANCELADO'

PRESTAMO_ESTADO_CHOICES = [
    (PRESTAMO_ACTIVO, 'En Préstamo'),
    (PRESTAMO_DEVUELTO, 'Devuelto'),
    (PRESTAMO_VENCIDO, 'Vencido (no devuelto a tiempo)'),
    (PRESTAMO_CANCELADO, 'Cancelado'),
]

# ============================================================================
# ROLES DE USUARIOS
# ============================================================================

ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
ROLE_VIEWER = 'viewer'

ROLE_CHOICES = [
    (ROLE_ADMIN, 'Administrador'),
    (ROLE_USER, 'Usuario'),
    (ROLE_VIEWER, 'Observador'),
]

# ============================================================================
# MODALIDADES DE PAGO (EMPRESAS)
# ============================================================================

MODALIDAD_GRATIS = 'gratis'
MODALIDAD_PRUEBA = 'trial'
MODALIDAD_PAGO = 'pago'

MODALIDAD_PAGO_CHOICES = [
    (MODALIDAD_GRATIS, 'Gratis'),
    (MODALIDAD_PRUEBA, 'Período de Prueba'),
    (MODALIDAD_PAGO, 'Plan de Pago'),
]

# ============================================================================
# ESTADOS DE TAREAS DE MANTENIMIENTO
# ============================================================================

TASK_STATUS_PENDING = 'pending'
TASK_STATUS_RUNNING = 'running'
TASK_STATUS_COMPLETED = 'completed'
TASK_STATUS_FAILED = 'failed'
TASK_STATUS_CANCELLED = 'cancelled'

TASK_STATUS_CHOICES = [
    (TASK_STATUS_PENDING, 'Pendiente'),
    (TASK_STATUS_RUNNING, 'En Ejecución'),
    (TASK_STATUS_COMPLETED, 'Completada'),
    (TASK_STATUS_FAILED, 'Fallida'),
    (TASK_STATUS_CANCELLED, 'Cancelada'),
]

# ============================================================================
# TIPOS DE TAREAS
# ============================================================================

TASK_TYPE_BACKUP = 'backup'
TASK_TYPE_CLEANUP = 'cleanup'
TASK_TYPE_UPDATE = 'update'
TASK_TYPE_CUSTOM = 'custom'

TASK_TIPO_CHOICES = [
    (TASK_TYPE_BACKUP, 'Backup'),
    (TASK_TYPE_CLEANUP, 'Limpieza'),
    (TASK_TYPE_UPDATE, 'Actualización'),
    (TASK_TYPE_CUSTOM, 'Personalizada'),
]

# ============================================================================
# ESTADOS DE NOTIFICACIONES
# ============================================================================

NOTIFICATION_STATUS_UNREAD = 'unread'
NOTIFICATION_STATUS_READ = 'read'
NOTIFICATION_STATUS_ARCHIVED = 'archived'

NOTIFICATION_STATUS_CHOICES = [
    (NOTIFICATION_STATUS_UNREAD, 'No Leída'),
    (NOTIFICATION_STATUS_READ, 'Leída'),
    (NOTIFICATION_STATUS_ARCHIVED, 'Archivada'),
]

# ============================================================================
# TIPOS DE NOTIFICACIONES
# ============================================================================

NOTIFICATION_TYPE_INFO = 'info'
NOTIFICATION_TYPE_SUCCESS = 'success'
NOTIFICATION_TYPE_WARNING = 'warning'
NOTIFICATION_TYPE_ERROR = 'error'

NOTIFICATION_TIPO_CHOICES = [
    (NOTIFICATION_TYPE_INFO, 'Información'),
    (NOTIFICATION_TYPE_SUCCESS, 'Éxito'),
    (NOTIFICATION_TYPE_WARNING, 'Advertencia'),
    (NOTIFICATION_TYPE_ERROR, 'Error'),
]

# ============================================================================
# ESTADOS DE SALUD DEL SISTEMA
# ============================================================================

HEALTH_STATUS_HEALTHY = 'healthy'
HEALTH_STATUS_WARNING = 'warning'
HEALTH_STATUS_CRITICAL = 'critical'
HEALTH_STATUS_UNKNOWN = 'unknown'

HEALTH_STATUS_CHOICES = [
    (HEALTH_STATUS_HEALTHY, 'Saludable'),
    (HEALTH_STATUS_WARNING, 'Advertencia'),
    (HEALTH_STATUS_CRITICAL, 'Crítico'),
    (HEALTH_STATUS_UNKNOWN, 'Desconocido'),
]

# ============================================================================
# CONFIGURACIÓN DE LÍMITES
# ============================================================================

# Equipos
DEFAULT_EQUIPMENT_LIMIT = 5
MAX_EQUIPMENT_LIMIT = 1000
FREE_PLAN_EQUIPMENT_LIMIT = 5
TRIAL_PLAN_EQUIPMENT_LIMIT = 20

# Almacenamiento (en MB)
DEFAULT_STORAGE_LIMIT_MB = 100
MAX_STORAGE_LIMIT_MB = 10240  # 10 GB
FREE_PLAN_STORAGE_MB = 100
TRIAL_PLAN_STORAGE_MB = 500

# Archivos
MAX_FILE_SIZE_MB = 10
MAX_LOGO_SIZE_MB = 2

# Días de prueba
TRIAL_DURATION_DAYS = 30
TRIAL_WARNING_DAYS = 7  # Advertir 7 días antes de expirar

# ============================================================================
# FORMATOS DE ARCHIVO PERMITIDOS
# ============================================================================

ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif']
ALLOWED_DOCUMENT_FORMATS = ['pdf', 'xlsx', 'docx', 'doc', 'xls']
ALLOWED_CERTIFICATE_FORMATS = ['pdf']

# MIME types
ALLOWED_IMAGE_MIMES = ['image/jpeg', 'image/png', 'image/gif']
ALLOWED_DOCUMENT_MIMES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/vnd.ms-excel',
]

# ============================================================================
# PAGINACIÓN
# ============================================================================

PAGINATION_SIZE = 25
PAGINATION_SIZE_LARGE = 50
PAGINATION_SIZE_SMALL = 10

# ============================================================================
# CACHE TTL (en segundos)
# ============================================================================

CACHE_TTL_SHORT = 60  # 1 minuto
CACHE_TTL_MEDIUM = 300  # 5 minutos
CACHE_TTL_LONG = 3600  # 1 hora
CACHE_TTL_DASHBOARD = 300  # 5 minutos (dashboard)

# ============================================================================
# NOTIFICACIONES Y RECORDATORIOS
# ============================================================================

# Días antes de vencimiento para enviar notificaciones
NOTIFICATION_DAYS_BEFORE = [30, 15, 7, 3, 1]

# Días para considerar algo "próximo a vencer"
PROXIMAS_DIAS = 30

# ============================================================================
# COLORES PARA ESTADOS (Bootstrap classes)
# ============================================================================

STATUS_COLORS = {
    'success': 'success',
    'warning': 'warning',
    'danger': 'danger',
    'info': 'info',
    'primary': 'primary',
    'secondary': 'secondary',
}

EQUIPO_ESTADO_COLORS = {
    ESTADO_ACTIVO: 'success',
    ESTADO_INACTIVO: 'secondary',
    ESTADO_EN_CALIBRACION: 'info',
    ESTADO_EN_MANTENIMIENTO: 'warning',
    ESTADO_DE_BAJA: 'danger',
    ESTADO_EN_PRESTAMO: 'primary',
}

# ============================================================================
# MENSAJES DEL SISTEMA
# ============================================================================

MSG_EQUIPO_CREADO = "Equipo creado exitosamente"
MSG_EQUIPO_ACTUALIZADO = "Equipo actualizado exitosamente"
MSG_EQUIPO_ELIMINADO = "Equipo eliminado exitosamente"

MSG_CALIBRACION_CREADA = "Calibración registrada exitosamente"
MSG_MANTENIMIENTO_CREADO = "Mantenimiento registrado exitosamente"
MSG_COMPROBACION_CREADA = "Comprobación registrada exitosamente"

MSG_PRESTAMO_CREADO = "Préstamo registrado exitosamente"
MSG_PRESTAMO_DEVUELTO = "Equipo devuelto exitosamente"

MSG_ERROR_PERMISOS = "No tienes permisos para realizar esta acción"
MSG_ERROR_LIMITE_EQUIPOS = "Has alcanzado el límite de equipos para tu plan"
MSG_ERROR_LIMITE_ALMACENAMIENTO = "Has alcanzado el límite de almacenamiento"

# ============================================================================
# URLS EXTERNAS
# ============================================================================

URL_DOCUMENTACION = "https://docs.sammetrologia.com"
URL_SOPORTE = "https://soporte.sammetrologia.com"
URL_GITHUB = "https://github.com/Sam-Metrologia/sam-2"

# ============================================================================
# INFORMACIÓN DE VERSIÓN
# ============================================================================

APP_VERSION = "2.0.0"
APP_NAME = "SAM Metrología"
APP_DESCRIPTION = "Sistema de Administración Metrológica"
