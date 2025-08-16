# your_project_name/your_project_name/settings.py

import os
import dj_database_url
from pathlib import Path
from django.contrib.messages import constants as messages

# Importa S3Boto3Storage de django-storages para la configuración de S3
# Aunque no se usa directamente en el código de settings.py, es buena práctica tener la importación si se hace referencia a la clase.
from storages.backends.s3boto3 import S3Boto3Storage 

# ==============================================================================
# CONFIGURACIÓN DE LOS LOGS PARA AWS S3 (AJUSTADO PARA DEPURACIÓN MÁS VERBOSA)
# ==============================================================================
import logging
# Para obtener logs detallados de la comunicación con AWS
logging.getLogger('botocore').setLevel(logging.DEBUG)
logging.getLogger('s3transfer').setLevel(logging.DEBUG)
# ==============================================================================


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'un_valor_por_defecto_muy_largo_y_aleatorio_para_desarrollo_local_SOLO')

# Render External Hostname es el dominio que Render asigna a tu app
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

# Determinar si estamos en modo DEBUG
# Es más robusto usar una variable de entorno DEBUG para controlar esto explícitamente.
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true' # CAMBIADO: Usar DJANGO_DEBUG

# Configuración de ALLOWED_HOSTS
ALLOWED_HOSTS = []
if RENDER_EXTERNAL_HOSTNAME:
    # Si estamos en Render, añadimos el hostname externo
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if DEBUG:
    # Si DEBUG es True (generalmente en desarrollo local), permitimos hosts locales
    ALLOWED_HOSTS.append('localhost')
    ALLOWED_HOSTS.append('127.0.0.1')
    # Puedes añadir otros hosts locales o IPs si los usas para testing
    # ALLOWED_HOSTS.append('0.0.0.0') # Si usas docker o IPs en red local
else:
    # En producción (DEBUG es False), aseguramos que solo se permitan los hosts de Render
    # Esto ya está cubierto por la lógica superior, pero es un recordatorio de que DEBUG = False
    # debe ser la condición principal para el despliegue.
    pass


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

ROOT_URLCONF = 'proyecto_c.urls' # Asegúrate que 'proyecto_c' es el nombre de tu proyecto principal

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

WSGI_APPLICATION = 'proyecto_c.wsgi.application' # Asegúrate que 'proyecto_c' es el nombre de tu proyecto principal

# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS (AJUSTADA)
# ==============================================================================
# Usa DATABASE_URL que Render proveerá para PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
    # dj_database_url.parse ya maneja sslmode='require' si la URL lo especifica,
    # pero ssl_require=True asegura que siempre lo pida si no está explícito en la URL.
else:
    # Configuración de SQLite para desarrollo local si no hay DATABASE_URL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# ==============================================================================


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
# CONFIGURACIÓN DE ALMACENAMIENTO DE ARCHIVOS EN AWS S3 (AJUSTADA)
# =============================================================================

# Verifica si las variables de entorno de S3 están configuradas
# Es crucial que estas variables estén definidas en Render para que S3 funcione
if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1') 
    
    # Construye el dominio personalizado de S3 para acceder a los archivos
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    
    # MEDIA_URL debe apuntar a tu bucket S3 para los archivos de medios
    # La ruta completa será https://<bucket-name>.s3.<region>.amazonaws.com/media/
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/' 
    
    AWS_S3_USE_SSL = True # Usar SSL para las conexiones a S3
    
    # Parámetros adicionales para los objetos de S3 (ej. Cache-Control)
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'} 
    
    # Importante: No añadir la autenticación como parámetro de consulta en la URL de los archivos
    AWS_QUERYSTRING_AUTH = False 
    AWS_S3_SIGNATURE_VERSION = 's3v4' # Versión de firma recomendada
    AWS_LOCATION = 'media' # Prefijo (carpeta) dentro de tu bucket S3 para los archivos de medios
    
    # Evitar sobrescribir archivos con el mismo nombre si ya existen
    AWS_S3_FILE_OVERWRITE = False
else:
    # Configuración local de archivos de medios si no hay variables de entorno S3
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

# ==============================================================================
# CONFIGURACIÓN DE USUARIO PERSONALIZADO (Asegúrate de que esta línea esté presente)
# ==============================================================================
AUTH_USER_MODEL = 'core.CustomUser'
# ==============================================================================

# ==============================================================================
# SEGURIDAD ADICIONAL PARA PRODUCCIÓN
# ==============================================================================
# Para permitir que Render se comunique de forma segura
# Render automáticamente establece HTTP_X_FORWARDED_PROTO a 'https' para las solicitudes.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true' # CAMBIADO: Valor por defecto a True
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true' # CAMBIADO: Valor por defecto a True
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True').lower() == 'true' # CAMBIADO: Valor por defecto a True
# Orígenes de confianza para CSRF. Render inyectará tu hostname en esta variable.
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
X_FRAME_OPTIONS = 'DENY' # Recomendado para protección contra clickjacking. Cambia a 'SAMEORIGIN' si necesitas iframes de tu propio dominio.

