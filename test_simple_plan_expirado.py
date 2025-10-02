#!/usr/bin/env python
"""
Test simple y directo para el sistema de plan expirado.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import timedelta
from core.models import Empresa, CustomUser
from core.views.base import access_check
from django.http import HttpResponse

print("=== TEST DE RESTRICCION DE ACCESO POR PLAN EXPIRADO ===")

# Crear empresa con plan ya expirado (manualmente)
empresa_test = Empresa.objects.filter(nombre="Test Empresa Manual").first()
if not empresa_test:
    empresa_test = Empresa.objects.create(
        nombre="Test Empresa Manual",
        estado_suscripcion="Expirado"  # Forzar estado expirado directamente
    )
else:
    # Actualizar directamente el estado
    empresa_test.estado_suscripcion = "Expirado"
    empresa_test.save()

print(f"Empresa creada: {empresa_test.nombre}")
print(f"Estado: {empresa_test.get_estado_suscripcion_display()}")

# Crear vista de prueba
@access_check
def vista_prueba(request):
    return HttpResponse("Acceso permitido")

# Crear usuario normal
factory = RequestFactory()
request = factory.get('/test/')
usuario_normal = CustomUser(username='test_normal', is_superuser=False)
usuario_normal.empresa = empresa_test
request.user = usuario_normal

print(f"\n--- Probando usuario normal con plan expirado ---")
print(f"Usuario: {usuario_normal.username}")
print(f"Es superuser: {usuario_normal.is_superuser}")
print(f"Empresa: {usuario_normal.empresa.nombre if usuario_normal.empresa else 'Sin empresa'}")
print(f"Estado plan: {usuario_normal.empresa.get_estado_suscripcion_display() if usuario_normal.empresa else 'N/A'}")

# Probar acceso
response = vista_prueba(request)
print(f"Código de respuesta: {response.status_code}")
if response.status_code == 403:
    print("RESULTADO: BLOQUEADO CORRECTAMENTE")
else:
    print("RESULTADO: NO BLOQUEADO - HAY UN PROBLEMA")

# Probar con superusuario
print(f"\n--- Probando superusuario con plan expirado ---")
usuario_admin = CustomUser(username='test_admin', is_superuser=True)
usuario_admin.empresa = empresa_test
request.user = usuario_admin

print(f"Usuario: {usuario_admin.username}")
print(f"Es superuser: {usuario_admin.is_superuser}")

response_admin = vista_prueba(request)
print(f"Código de respuesta: {response_admin.status_code}")
if response_admin.status_code == 200:
    print("RESULTADO: ACCESO PERMITIDO CORRECTAMENTE")
else:
    print("RESULTADO: BLOQUEADO - PROBLEMA CON SUPERUSUARIOS")

print("\n=== FIN DEL TEST ===")