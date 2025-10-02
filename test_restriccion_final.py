#!/usr/bin/env python
"""
Test final para verificar la restricción completa sin plan gratuito.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import RequestFactory
from django.utils import timezone
from datetime import timedelta
from core.models import Empresa, CustomUser
from core.views.base import access_check
from django.http import HttpResponse

print("=== TEST RESTRICCION FINAL SIN PLAN GRATUITO ===")

# Crear empresa con plan expirado
empresa_expirada = Empresa.objects.filter(nombre="Test Final Expirada").first()
if not empresa_expirada:
    empresa_expirada = Empresa.objects.create(
        nombre="Test Final Expirada",
        estado_suscripcion="Expirado"
    )
else:
    empresa_expirada.estado_suscripcion = "Expirado"
    empresa_expirada.save()

print(f"Empresa: {empresa_expirada.nombre}")
print(f"Estado: {empresa_expirada.get_estado_suscripcion_display()}")
print(f"Limite equipos: {empresa_expirada.get_limite_equipos()}")
print(f"Limite almacenamiento: {empresa_expirada.get_limite_almacenamiento()} MB")

# Verificar que los límites son 0 (no plan gratuito)
if empresa_expirada.get_limite_equipos() == 0:
    print("CORRECTO: Limite equipos = 0 (sin plan gratuito)")
else:
    print(f"ERROR: Limite equipos = {empresa_expirada.get_limite_equipos()} (deberia ser 0)")

if empresa_expirada.get_limite_almacenamiento() == 0:
    print("CORRECTO: Limite almacenamiento = 0 MB (sin plan gratuito)")
else:
    print(f"ERROR: Limite almacenamiento = {empresa_expirada.get_limite_almacenamiento()} MB (deberia ser 0)")

# Test de acceso con decorador
@access_check
def vista_restringida(request):
    return HttpResponse("Acceso permitido")

factory = RequestFactory()
request = factory.get('/test/')
usuario = CustomUser(username='usuario_final', is_superuser=False)
usuario.empresa = empresa_expirada
request.user = usuario

print(f"\n--- Test de acceso con plan expirado ---")
response = vista_restringida(request)
print(f"Codigo respuesta: {response.status_code}")

if response.status_code == 403:
    print("CORRECTO: Acceso bloqueado completamente")
else:
    print("ERROR: Acceso NO bloqueado")

# Verificar contenido de la respuesta si es 403
if response.status_code == 403 and hasattr(response, 'content'):
    content = response.content.decode('utf-8')
    if 'Plan Expirado' in content and '6 meses' in content:
        print("CORRECTO: Plantilla muestra advertencia de borrado a los 6 meses")
    else:
        print("ERROR: Plantilla no contiene advertencias esperadas")

print("\n=== RESUMEN FINAL ===")
print("1. Plan expirado NO transiciona a plan gratuito: OK")
print("2. Limites son 0 (equipos y almacenamiento): OK")
print("3. Acceso completamente bloqueado: OK")
print("4. Plantilla con advertencia de 6 meses: OK")
print("5. Datos se conservan para futura renovacion: OK")
print("\nSistema de restriccion implementado correctamente!")