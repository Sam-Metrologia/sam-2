"""
WSGI config for proyecto_c project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
# from dotenv import load_dotenv # <--- ESTA LÍNEA SE HA ELIMINADO/COMENTADO

from django.core.wsgi import get_wsgi_application

# load_dotenv() # <--- ESTA LÍNEA SE HA ELIMINADO/COMENTADO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')

application = get_wsgi_application()
# Este es otro cambio de prueba
