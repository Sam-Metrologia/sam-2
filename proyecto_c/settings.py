# your_project_name/your_project_name/settings.py

import os
import dj_database_url
from pathlib import Path
from django.contrib.messages import constants as messages

from storages.backends.s3boto3 import S3Boto3Storage 

import logging
logging.getLogger('botocore').setLevel(logging.DEBUG)
logging.getLogger('s3transfer').setLevel(logging.DEBUG)


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'un_valor_por_defecto_muy_largo_y_aleatorio_para_desarrollo_local_SOLO')

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true' 

# Configuración de ALLOWED_HOSTS
ALLOWED_HOSTS = []
# Obtener ALLOWED_HOSTS de variable de entorno y dividir por comas
allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
for host in allowed_hosts_env:
    if host: # Asegurarse de que no esté vacío
        ALLOWED_HOSTS.append(host.strip()) # strip() para eliminar espacios en blanco

# Si estamos en Render, añadimos el hostname externo
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Si DEBUG es True (generalmente en desarrollo local), permitimos hosts locales
if DEBUG:
    if 'localhost' not in ALLOWED_HOSTS: ALLOWED_HOSTS.append('localhost')
    if '127.0.0.1' not in ALLOWED_HOSTS: ALLOWED_HOSTS.append('127.0.0.1')


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aplicaciones de terceros
    'whitenoise.runserver_nostatic', # Mover aquí. Importante para que WhiteNoise se comporte bien en runserver
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
    'whitenoise.middleware.WhiteNoiseMiddleware', # Debe ir después de SecurityMiddleware
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
                # Asegúrate de añadir tu context processor personalizado si lo tienes
                # por ejemplo: 'core.context_processors.company_context', 
            ],
        },
    },
]

WSGI_APPLICATION = 'proyecto_c.wsgi.application' 

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==============================================================================
# Usa DATABASE_URL que Render proveerá para PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
else:
    # Configuración de SQLite para desarrollo local si no hay DATABASE_URL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
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


# Configuración de archivos estáticos
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # Directorio donde 'collectstatic' reunirá los archivos para producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    BASE_DIR / 'core/static', # Si tienes archivos estáticos directamente en core/static
]

# =============================================================================
# CONFIGURACIÓN DE ALMACENAMIENTO DE ARCHIVOS EN AWS S3
# =============================================================================
if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1') 
    
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/' 
    
    AWS_S3_USE_SSL = True 
    
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'} 
    
    AWS_QUERYSTRING_AUTH = False 
    AWS_S3_SIGNATURE_VERSION = 's3v4' 
    AWS_LOCATION = 'media' 
    
    AWS_S3_FILE_OVERWRITE = False
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media' 
    print("WARNING: AWS S3 environment variables not found. Using local media storage.")


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

AUTH_USER_MODEL = 'core.CustomUser'

# ==============================================================================
# SEGURIDAD ADICIONAL PARA PRODUCCIÓN
# ==============================================================================
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true' 
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true' 
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True').lower() == 'true' 

# CAMBIADO: Generar CSRF_TRUSTED_ORIGINS con 'https://' explícitamente si se usa RENDER_EXTERNAL_HOSTNAME
# Y usar una variable de entorno específica para los orígenes de confianza.
_csrf_trusted_origins_list = []
_csrf_trusted_origins_env = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
for origin in _csrf_trusted_origins_env:
    if origin and not origin.startswith(('http://', 'https://')):
        _csrf_trusted_origins_list.append(f'https://{origin.strip()}')
    elif origin:
        _csrf_trusted_origins_list.append(origin.strip())

if RENDER_EXTERNAL_HOSTNAME and f'https://{RENDER_EXTERNAL_HOSTNAME}' not in _csrf_trusted_origins_list:
    _csrf_trusted_origins_list.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins_list

X_FRAME_OPTIONS = 'DENY' 