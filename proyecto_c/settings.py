# proyecto_c/proyecto_c/settings.py

import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url
from storages.backends.s3boto3 import S3Boto3Storage
import cloudinary
import cloudinary.uploader
import cloudinary.api

# ==============================================================================
# CONFIGURACIÓN BÁSICA DEL PROYECTO
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Lee la clave secreta desde una variable de entorno.
SECRET_KEY = os.environ.get('SECRET_KEY', 'un_valor_por_defecto_para_desarrollo_local')

# Permite que Render establezca DEBUG en False en producción.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
DEBUG = 'RENDER' not in RENDER_EXTERNAL_HOSTNAME if RENDER_EXTERNAL_HOSTNAME else True

# Lista de hosts permitidos.
ALLOWED_HOSTS = []
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if DEBUG:
    ALLOWED_HOSTS.append('localhost')
    ALLOWED_HOSTS.append('127.0.0.1')

# CSRF_TRUSTED_ORIGINS para producción y desarrollo.
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
else:
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'storages',  # Añadido para AWS S3
    'cloudinary', # Añadido para Cloudinary
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Añadido para servir archivos estáticos
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
# CONFIGURACIÓN DE BASE DE DATOS
# ==============================================================================
# Lee la URL de la base de datos de la variable de entorno.
# `conn_max_age` asegura conexiones persistentes.
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600
        )
    }
else:
    # Configuración local para desarrollo
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ==============================================================================
# AUTENTICACIÓN Y MENSAJES
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

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

LOGIN_REDIRECT_URL = 'core:dashboard'
LOGIN_URL = 'core:login'
LOGOUT_REDIRECT_URL = 'core:login'

MESSAGE_TAGS = {
    messages.DEBUG: 'bg-blue-100 border-blue-500 text-blue-700',
    messages.INFO: 'bg-indigo-100 border-indigo-500 text-indigo-700',
    messages.SUCCESS: 'bg-green-100 border-green-500 text-green-700',
    messages.WARNING: 'bg-yellow-100 border-yellow-500 text-yellow-700',
    messages.ERROR: 'bg-red-100 border-red-500 text-red-700',
}

# ==============================================================================
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS Y DE MEDIA
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configuración de Cloudinary para imágenes (si usas AWS S3, ignora esta sección)
#cloudinary.config(
#    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
#    api_key=os.environ.get('CLOUDINARY_API_KEY'),
#    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
#)

# Configuración de Media con S3 o local
# Lee las credenciales de AWS desde variables de entorno
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')

if all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME]):
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'