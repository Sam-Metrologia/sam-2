# proyecto_c/proyecto_c/settings.py

import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url # Importado para configurar la base de datos
# Importa S3Boto3Storage de django-storages para la configuración de S3
# from storages.backends.s3boto3 import S3Boto3Storage # No es necesario importar la clase directamente aquí, ya que se referencia por cadena

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

# DEBUG se activa si no hay RENDER_EXTERNAL_HOSTNAME, o si DEBUG_VALUE es 'True'
DEBUG = os.environ.get('DEBUG_VALUE', 'False') == 'True'
if not RENDER_EXTERNAL_HOSTNAME:
    DEBUG = True

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
    'storages', # Asegúrate de que 'storages' esté en tus INSTALLED_APPS
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
# CONFIGURACIÓN DE BASE DE DATOS (AJUSTADA)
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configuración de base de datos para producción (Render)
# Si la variable de entorno DATABASE_URL está presente, úsala para PostgreSQL.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)
    # Para PostgreSQL en Render, asegurar conexiones SSL
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',
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


STATIC_URL = 'static/'
# STATIC_ROOT y STATICFILES_STORAGE se definirán condicionalmente más abajo si se usa S3
STATICFILES_DIRS = [
    BASE_DIR / 'core/static',
]

# ==============================================================================
# CONFIGURACIÓN DE ALMACENAMIENTO DE ARCHIVOS EN AWS S3 (AJUSTADA Y SEGURA)
# ==============================================================================

# Obtiene las credenciales de AWS desde las variables de entorno
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-2') # Puedes definir un valor por defecto si lo deseas

# Define STATIC_ROOT globalmente, es necesario para collectstatic
# Cuando se usa S3 para estáticos, collectstatic los sube a S3.
# Cuando se usa Whitenoise, collectstatic los recolecta en STATIC_ROOT local.
STATIC_ROOT = BASE_DIR / 'staticfiles' # Siempre define STATIC_ROOT

# Determina si usar S3 o almacenamiento local
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage' # Si también para archivos estáticos
    
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = None
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    AWS_S3_USE_SSL = True
    AWS_QUERYSTRING_AUTH = False
    AWS_LOCATION = 'media'
    AWS_S3_FILE_OVERWRITE = False
    print("INFO: AWS S3 storage configured.")
else:
    # Si las variables de entorno de S3 no están, usa la configuración local
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media' # Carpeta local donde se guardarán los archivos
    # Para STATICFILES_STORAGE, si no usas S3 para estáticos, Whitenoise es la opción por defecto.
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    # STATIC_ROOT ya está definido arriba, no lo redefinas aquí

    print("WARNING: AWS S3 environment variables not found. Using local media storage.")


# =============================================================================


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
