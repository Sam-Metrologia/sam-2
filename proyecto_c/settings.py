# proyecto_c/proyecto_c/settings.py - VERSION MEJORADA

import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'un_valor_por_defecto_muy_largo_y_aleatorio_para_desarrollo_local_SOLO')

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

# DEBUG se activa si no hay RENDER_EXTERNAL_HOSTNAME, o si DEBUG_VALUE es 'True'
# Temporal: Forzar DEBUG = True para diagnóstico de errores 500
DEBUG = True
# DEBUG = os.environ.get('DEBUG_VALUE', 'False') == 'True'
# if not RENDER_EXTERNAL_HOSTNAME:
#     DEBUG = True

ALLOWED_HOSTS = []

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Si DEBUG es True, añade los hosts locales permitidos
if DEBUG:
    ALLOWED_HOSTS.append('localhost')
    ALLOWED_HOSTS.append('127.0.0.1')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aplicaciones de terceros
    'storages',
    'crispy_forms',
    'crispy_bootstrap5',
    'weasyprint',
    # Mis aplicaciones
    'core',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Añadido para compresión
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'proyecto_c.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'proyecto_c.wsgi.application'

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS CON POOL DE CONEXIONES
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configuración de base de datos para producción (Render)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)
    # Configuración optimizada para PostgreSQL
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',
        'connect_timeout': 10,
    }
    # Pool de conexiones para mejor performance
    DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutos

# ==============================================================================
# CONFIGURACIÓN DE CACHE MEJORADA
# ==============================================================================
if RENDER_EXTERNAL_HOSTNAME:
    # En producción, usar Redis si está disponible
    REDIS_URL = os.environ.get('REDIS_URL')
    if REDIS_URL:
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': REDIS_URL,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'CONNECTION_POOL_KWARGS': {
                        'max_connections': 20,
                        'retry_on_timeout': True,
                    },
                },
                'KEY_PREFIX': 'sam_metrologia',
                'TIMEOUT': 300,  # 5 minutos por defecto
            }
        }
    else:
        # Fallback a cache de base de datos
        CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
                'LOCATION': 'sam_cache_table',
                'TIMEOUT': 300,
                'OPTIONS': {
                    'MAX_ENTRIES': 1000,
                    'CULL_FREQUENCY': 3,
                }
            }
        }
else:
    # En desarrollo, usar cache local
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'sam-dev-cache',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 500,
                'CULL_FREQUENCY': 3,
            }
        }
    }

# ==============================================================================
# CONFIGURACIÓN DE LOGGING ESTRUCTURADO
# ==============================================================================
# Crear directorio de logs si no existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(levelname)s %(asctime)s %(module)s %(funcName)s %(lineno)d %(message)s %(pathname)s %(process)d %(thread)d'
        } if not DEBUG else {
            'format': '{asctime} - {name} - {levelname} - {message}',
            'style': '{',
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'filters': ['require_debug_true'] if DEBUG else [],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file_info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sam_info.log',
            'maxBytes': 10*1024*1024,  # 10MB
            'backupCount': 5,
            'formatter': 'json' if not DEBUG else 'verbose',
            'encoding': 'utf-8',
        },
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sam_errors.log',
            'maxBytes': 10*1024*1024,  # 10MB
            'backupCount': 10,
            'formatter': 'json' if not DEBUG else 'verbose',
            'encoding': 'utf-8',
        },
        'file_security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sam_security.log',
            'maxBytes': 10*1024*1024,  # 10MB
            'backupCount': 10,
            'formatter': 'json' if not DEBUG else 'verbose',
            'encoding': 'utf-8',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'include_html': True,
        } if not DEBUG else {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file_info'],
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file_security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_error', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'core.security': {
            'handlers': ['file_security', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Reducir ruido de AWS en logs
        'botocore': {
            'level': 'WARNING',
            'handlers': ['file_error'],
            'propagate': False,
        },
        's3transfer': {
            'level': 'WARNING',
            'handlers': ['file_error'],
            'propagate': False,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'core/static',
]

# Siempre define STATIC_ROOT, es necesario para collectstatic
STATIC_ROOT = BASE_DIR / 'staticfiles' 

# ==============================================================================
# CONFIGURACIÓN DE ALMACENAMIENTO DE ARCHIVOS EN AWS S3 (MEJORADA Y SEGURA)
# ==============================================================================

# Obtiene las credenciales de AWS desde las variables de entorno
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '').strip()
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '').strip()
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '').strip()
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-2').strip()

# Debug: Imprimir estado de las variables AWS (temporal)
print(f"DEBUG AWS CONFIG:")
print(f"- AWS_ACCESS_KEY_ID: {'SET' if AWS_ACCESS_KEY_ID else 'NOT SET'}")
print(f"- AWS_SECRET_ACCESS_KEY: {'SET' if AWS_SECRET_ACCESS_KEY else 'NOT SET'}")
print(f"- AWS_STORAGE_BUCKET_NAME: {AWS_STORAGE_BUCKET_NAME}")
print(f"- AWS_S3_REGION_NAME: {AWS_S3_REGION_NAME}")

# Configuración S3 mejorada con seguridad
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    AWS_DEFAULT_ACL = None
    AWS_S3_USE_SSL = True
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_ENDPOINT_URL = f'https://s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    
    # Configuraciones de seguridad adicionales
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
        'ServerSideEncryption': 'AES256',  # Encripción en servidor
    }
    
    # Configuración para diferentes tipos de archivos
    AWS_LOCATION = 'media'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'

    # Usar storage personalizado para archivos media
    DEFAULT_FILE_STORAGE = 'proyecto_c.storages.S3MediaStorage'
    
    # Para archivos estáticos, usar S3 solo en producción
    if RENDER_EXTERNAL_HOSTNAME:
        STATICFILES_STORAGE = 'proyecto_c.storages.S3StaticStorage'
        AWS_STATIC_LOCATION = 'static'
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_STATIC_LOCATION}/'
    else:
        STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    
    # Configurar timeout y reintentos para S3
    AWS_S3_MAX_POOL_CONNECTIONS = 10
    AWS_S3_RETRIES = {
        'max_attempts': 3,
        'mode': 'adaptive'
    }
    
else:
    # Configuración local
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    WHITENOISE_MAX_AGE = 3600

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'core:dashboard'
LOGIN_URL = 'core:login'
LOGOUT_REDIRECT_URL = 'core:login'

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# ==============================================================================
# CONFIGURACIÓN DE USUARIO PERSONALIZADO
# ==============================================================================
AUTH_USER_MODEL = 'core.CustomUser'

# ==============================================================================
# CONFIGURACIONES DE SEGURIDAD MEJORADAS
# ==============================================================================

if not DEBUG:
    # Configuraciones de seguridad para producción
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_REFERRER_POLICY = 'same-origin'
    
    # CSP básico (ajustar según necesidades específicas)
    SECURE_CONTENT_SECURITY_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    
    # Configurar HTTPS
    if RENDER_EXTERNAL_HOSTNAME:
        SECURE_SSL_REDIRECT = True
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ==============================================================================
# CONFIGURACIONES DE ARCHIVOS Y UPLOADS
# ==============================================================================

# Límites de archivos
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Tipos de archivos permitidos
ALLOWED_FILE_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.xlsx', '.docx']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# ==============================================================================
# CONFIGURACIONES DE PERFORMANCE
# ==============================================================================

# Configuración de sesiones
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db' if not DEBUG else 'django.contrib.sessions.backends.db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Configuración de cookies de seguridad
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Lax'

# ==============================================================================
# CONFIGURACIÓN DE EMAIL (OPCIONAL)
# ==============================================================================
if not DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@sammetrologia.com')
    
    # Lista de administradores para notificaciones de error
    ADMINS = [
        ('Admin SAM', os.environ.get('ADMIN_EMAIL', 'admin@sammetrologia.com')),
    ]
    MANAGERS = ADMINS
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================================================
# CONFIGURACIÓN DE INTERNACIONALIZACIÓN MEJORADA
# ==============================================================================
USE_L10N = True
DATETIME_FORMAT = 'd/m/Y H:i'
DATE_FORMAT = 'd/m/Y'
TIME_FORMAT = 'H:i'

# ==============================================================================
# CONFIGURACIONES ESPECÍFICAS DE LA APLICACIÓN
# ==============================================================================

# Configuraciones de SAM Metrología
SAM_CONFIG = {
    'DEFAULT_EQUIPMENT_LIMIT': 5,
    'MAX_EQUIPMENT_LIMIT': 1000,
    'DEFAULT_TRIAL_PERIOD_DAYS': 30,
    'MAX_FILE_SIZE_MB': 10,
    'ALLOWED_IMAGE_FORMATS': ['jpg', 'jpeg', 'png'],
    'ALLOWED_DOCUMENT_FORMATS': ['pdf', 'xlsx', 'docx'],
    'CACHE_TIMEOUT_DASHBOARD': 300,  # 5 minutos
    'CACHE_TIMEOUT_REPORTS': 1800,   # 30 minutos
    'PAGINATION_SIZE': 25,
    'MAX_SEARCH_RESULTS': 100,
}

# Configuración de rate limiting
RATE_LIMIT_CONFIG = {
    'LOGIN_ATTEMPTS': {'limit': 5, 'period': 300},  # 5 intentos por 5 minutos
    'UPLOAD_FILES': {'limit': 10, 'period': 300},   # 10 uploads por 5 minutos
    'API_CALLS': {'limit': 100, 'period': 3600},    # 100 llamadas por hora
}

# ==============================================================================
# CONFIGURACIÓN DE MONITOREO Y MÉTRICAS (OPCIONAL)
# ==============================================================================
if RENDER_EXTERNAL_HOSTNAME:
    # Configuración básica para métricas en producción
    METRICS_CONFIG = {
        'ENABLED': True,
        'TRACK_USER_ACTIVITY': True,
        'TRACK_ERROR_RATES': True,
        'TRACK_PERFORMANCE': True,
    }
else:
    METRICS_CONFIG = {
        'ENABLED': False,
    }

# ==============================================================================
# VALIDACIÓN DE CONFIGURACIÓN
# ==============================================================================

# Verificar configuraciones críticas en producción
if not DEBUG and RENDER_EXTERNAL_HOSTNAME:
    required_env_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_STORAGE_BUCKET_NAME',
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        raise Exception(f"Variables de entorno faltantes en producción: {missing_vars}")

# Configuración específica para desarrollo
if DEBUG:
    # Permitir todas las IPs en desarrollo
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    # Configuraciones para debugging
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }

print(f"Configuración cargada - Debug: {DEBUG}, Host: {RENDER_EXTERNAL_HOSTNAME or 'local'}")
print(f"Storage configurado: {globals().get('DEFAULT_FILE_STORAGE', 'NO CONFIGURADO')}")