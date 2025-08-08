# proyecto_c/proyecto_c/settings.py

import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url
# Importa S3Boto3Storage de django-storages para la configuración de S3
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

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

DEBUG = os.environ.get('DEBUG_VALUE', 'False') == 'True'
if not RENDER_EXTERNAL_HOSTNAME:
    DEBUG = True

ALLOWED_HOSTS = []

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ==============================================================================
# INSTALLED APPS
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'core',
    'storages',  # Se mantiene para la configuración de S3
    'weasyprint',
    'django_cleanup.apps.CleanupConfig'
]
# ==============================================================================


# ==============================================================================
# MIDDLEWARE
# Se ha añadido WhiteNoiseMiddleware para el manejo de archivos estáticos en Render
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Añadido para WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
# ==============================================================================


ROOT_URLCONF = 'proyecto_c.urls'

# ==============================================================================
# TEMPLATES
# ==============================================================================
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
                'core.context_processors.company_data',
                'core.context_processors.unread_messages_count',
            ],
        },
    },
]
# ==============================================================================

WSGI_APPLICATION = 'proyecto_c.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configuración para PostgreSQL en Render
# Verifica si la variable de entorno DATABASE_URL existe
DB_FROM_ENV = dj_database_url.config(conn_max_age=600)
if DB_FROM_ENV:
    DATABASES['default'] = DB_FROM_ENV


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True


# ==============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# Se han ajustado las configuraciones para que Render sirva los archivos estáticos
# ==============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Configuración para usar WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# ==============================================================================


# ==============================================================================
# DEFAULT_FILE_STORAGE: Si se usa S3, cambiaremos esto. Si no, usa el local.
# ==============================================================================

if all(os.environ.get(k) for k in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_STORAGE_BUCKET_NAME', 'AWS_S3_REGION_NAME']):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    
    # Se agrega esta línea para asegurar que boto3 esté configurado y usa SSL
    AWS_S3_USE_SSL = True

    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
    # Esta línea es vital para que los archivos subidos sean públicamente accesibles
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400', 'ACL': 'public-read'}

    # No añade el parámetro de autenticación como una cadena de consulta, para URLs más limpias
    AWS_QUERYSTRING_AUTH = False 
    AWS_S3_SIGNATURE_VERSION = 's3v4' # Especifica la versión de firma S3 (generalmente s3v4)
    AWS_LOCATION = 'media' # Subirá todos los archivos a una subcarpeta 'media' en el bucket
    
    # Asegúrate de que los archivos nuevos no sobrescriban los viejos con el mismo nombre.
    AWS_S3_FILE_OVERWRITE = False
else:
    # Si las variables de entorno de S3 no están, usa la configuración local
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    print("WARNING: AWS S3 environment variables not found. Using local media storage.")


# ==============================================================================

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

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

