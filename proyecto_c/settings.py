# proyecto_c/proyecto_c/settings.py

import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url # Añadido para la configuración de la base de datos

# Importamos la configuración para AWS S3
from storages.backends.s3boto3 import S3Boto3Storage

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# ¡IMPORTANTE! Genera una clave secreta segura y cámbiala antes de ir a producción.
# Puedes generar una ejecutando en tu terminal de Python:
# from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())
# SECRET_KEY (LEE DESDE VARIABLE DE ENTORNO)
# Render inyectará la SECRET_KEY que configuraste en sus variables de entorno
SECRET_KEY = os.environ.get('SECRET_KEY', 'un_valor_por_defecto_muy_largo_y_aleatorio_para_desarrollo_local_SOLO')

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG (LEE DESDE VARIABLE DE ENTORNO)
# En Render, DEBUG_VALUE debe ser 'False'
# Para desarrollo local, si RENDER_EXTERNAL_HOSTNAME no está presente, forzamos DEBUG a True
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

# Si no estamos en Render, asumimos que es desarrollo local y forzamos DEBUG a True
# De lo contrario, leemos de la variable de entorno (para Render)
DEBUG = os.environ.get('DEBUG_VALUE', 'False') == 'True'
if not RENDER_EXTERNAL_HOSTNAME:
    DEBUG = True # Forzar DEBUG a True en desarrollo local si no hay hostname de Render

ALLOWED_HOSTS = [] # Inicializa como lista vacía

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME) # Añade el hostname de Render

# Para desarrollo local, si DEBUG es True, permite localhost y 127.0.0.1
if DEBUG:
    ALLOWED_HOSTS.append('localhost')
    ALLOWED_HOSTS.append('127.0.0.1')
    # Puedes añadir tu IP local si necesitas acceder desde otros dispositivos en tu red
    # ALLOWED_HOSTS.append('tu_ip_local') # Ejemplo: '192.168.1.100'

# --- CONFIGURACIÓN PARA CORREGIR EL ERROR CSRF EN RENDER ---
# Django necesita confiar en el dominio de Render para aceptar el token CSRF.
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
else:
    # Para desarrollo local, confía en localhost
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']
# --- FIN DE LA CONFIGURACIÓN ---


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core', # ¡MUY IMPORTANTE! Añade tu aplicación 'core' aquí
    'storages', # <--- ¡IMPORTANTE! Añade la app de storages
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # ¡Añadido para servir archivos estáticos en producción!
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
        'DIRS': [BASE_DIR / 'templates'], # Añade esta línea para un directorio global de templates
        'APP_DIRS': True, # Esto es crucial para que Django busque en las carpetas 'templates' de cada app
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

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# --- CONFIGURACIÓN CORREGIDA PARA LA BASE DE DATOS EN RENDER Y LOCAL ---
# Obtenemos la URL de la base de datos de la variable de entorno
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Si la variable existe, usamos la configuración de Render
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600
        )
    }
else:
    # Si no existe (estamos en desarrollo local), usamos SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# --- FIN DE LA CONFIGURACIÓN CORREGIDA ---


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

LANGUAGE_CODE = 'es-es' # Cambia a español (Colombia)
TIME_ZONE = 'America/Bogota' # Zona horaria de Bogotá
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # Directorio para archivos estáticos recolectados en producción
# Configuración adicional para Whitenoise en producción
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user uploaded files)
# NOTA: Comentamos la configuración local de Media para usar la de AWS S3
# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media' # Directorio para archivos subidos por los usuarios

# ==============================================================================
# CONFIGURACIÓN DE ARCHIVOS DE MEDIA (AWS S3)
# ==============================================================================
# Esta configuración permite a Django guardar y servir archivos de media
# (como PDFs, imágenes, etc.) en un servicio de almacenamiento en la nube,
# lo cual es necesario en entornos de producción como Render.

# Lee las credenciales de AWS desde variables de entorno
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')

# Si las credenciales de AWS existen, configuramos S3
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
else:
    # Si no hay credenciales, usamos la configuración local (para desarrollo)
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
# ==============================================================================


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Configuración de URLs de autenticación ---
# Redirige a 'dashboard' después de iniciar sesión
LOGIN_REDIRECT_URL = 'core:dashboard'
# URL para el inicio de sesión
LOGIN_URL = 'core:login'
# Redirige a 'login' después de cerrar sesión
LOGOUT_REDIRECT_URL = 'core:login'

# --- Configuración de mensajes de Django (para estilizado con Tailwind) ---
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-error',
}

# ¡MUY IMPORTANTE! Le dice a Django que use nuestro modelo CustomUser
AUTH_USER_MODEL = 'core.CustomUser'
