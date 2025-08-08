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
    'import_export',
    # Mis aplicaciones
    'core',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

DATABASES = {
    'default': dj_database_url.config(default=os.environ.get('DATABASE_URL'))
}


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

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [
    BASE_DIR / 'core/static',
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

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

# =============================================================================
# CONFIGURACIÓN DE ALMACENAMIENTO DE ARCHIVOS EN AWS S3
# =============================================================================

# Verifica si las variables de entorno de S3 están configuradas
if os.environ.get('AWS_STORAGE_BUCKET_NAME'):
    # LÍNEA CORREGIDA/AJUSTADA
    # Define la clase de almacenamiento para usar S3
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Obtiene las credenciales de AWS desde las variables de entorno
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
    # Agrega esta línea para asegurar que boto3 esté configurado y usa SSL
    AWS_S3_USE_SSL = True

    # LÍNEAS AÑADIDAS/AJUSTADAS
    # La clave para hacer que los archivos sean públicos es especificar el ACL
    # durante la subida. AWS_S3_OBJECT_PARAMETERS lo hace de manera efectiva.
    # El public-read hace que el archivo sea accesible por la URL sin autenticación.
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400', 'ACL': 'public-read'}

    # También puedes intentar con estas líneas, aunque la de arriba es la más segura
    # AWS_DEFAULT_ACL = 'public-read' 
    # AWS_ACL_ENABLE = True

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


# =============================================================================
# AÑADE CUALQUIER OTRA CONFIGURACIÓN AQUÍ SI ES NECESARIO
# =============================================================================

# Esto es lo que se usa para especificar el modelo de usuario, pero no es necesario para tu problema actual.
# AUTH_USER_MODEL = 'core.CustomUser'

