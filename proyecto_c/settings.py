# proyecto_c/proyecto_c/settings.py

import os
from pathlib import Path
from django.contrib.messages import constants as messages
import dj_database_url # Añadido para la configuración de la base de datos

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
DEBUG = os.environ.get('DEBUG_VALUE', 'False') == 'True'

ALLOWED_HOSTS = [] # Inicializa como lista vacía
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME') # Obtiene el hostname de Render
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME) # Añade el hostname de Render

# Para desarrollo local, si necesitas acceder por localhost
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
    'core', # ¡MUY IMPORTANTE! Añade tu aplicación 'core' aquí
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

# Configuración de base de datos para PostgreSQL en Render
DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600 # Opcional: para reusar conexiones y evitar cuellos de botella
    )
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
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media' # Directorio para archivos subidos por los usuarios

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
# Prueba de modificacion settings
