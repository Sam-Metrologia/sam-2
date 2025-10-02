#!/usr/bin/env python
"""
Test para verificar que se muestra correctamente la información de baja de equipos.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import timedelta, date
from core.models import Empresa, CustomUser, Equipo, BajaEquipo
from django.urls import reverse

print("=== TEST INFORMACIÓN DE BAJA DE EQUIPOS ===")

# Crear empresa de prueba
empresa_test, _ = Empresa.objects.get_or_create(
    nombre="Test Empresa Baja",
    defaults={'estado_suscripcion': 'Activo'}
)

# Crear usuario de prueba
usuario_test, created = CustomUser.objects.get_or_create(
    username='test_baja_user',
    defaults={
        'email': 'test@example.com',
        'first_name': 'Paula',
        'last_name': 'Montañez',
        'empresa': empresa_test
    }
)

# Crear equipo de prueba
equipo_test, _ = Equipo.objects.get_or_create(
    codigo_interno='EQ-TEST-BAJA-001',
    defaults={
        'nombre': 'Equipo de Prueba Baja',
        'empresa': empresa_test,
        'estado': 'Activo'
    }
)

print(f"Empresa: {empresa_test.nombre}")
print(f"Usuario: {usuario_test.get_full_name() or usuario_test.username}")
print(f"Equipo: {equipo_test.nombre} ({equipo_test.codigo_interno})")
print(f"Estado inicial del equipo: {equipo_test.estado}")

# Crear registro de baja manualmente
baja_test, created = BajaEquipo.objects.get_or_create(
    equipo=equipo_test,
    defaults={
        'fecha_baja': date.today(),
        'razon_baja': 'ererer66666y6y',
        'observaciones': 'ererer',
        'dado_de_baja_por': usuario_test
    }
)

if created:
    print(f"\nRegistro de baja creado:")
    print(f"  - Fecha: {baja_test.fecha_baja}")
    print(f"  - Razón: {baja_test.razon_baja}")
    print(f"  - Observaciones: {baja_test.observaciones}")
    print(f"  - Usuario: {baja_test.dado_de_baja_por.get_full_name()}")

    # Actualizar estado del equipo
    equipo_test.estado = 'De Baja'
    equipo_test.save()
    print(f"  - Estado equipo actualizado: {equipo_test.estado}")
else:
    print(f"\nRegistro de baja ya existía:")
    print(f"  - Fecha: {baja_test.fecha_baja}")
    print(f"  - Razón: {baja_test.razon_baja}")
    print(f"  - Usuario: {baja_test.dado_de_baja_por.get_full_name()}")

# Probar el contexto de la vista detalle_equipo
print(f"\n=== PROBANDO VISTA DETALLE_EQUIPO ===")
from core.views.equipment import detalle_equipo
from django.test import RequestFactory

factory = RequestFactory()
request = factory.get(f'/equipos/{equipo_test.pk}/')
request.user = usuario_test

# Simular la lógica de obtener baja_registro
try:
    baja_registro_desde_equipo = equipo_test.baja_registro
    print(f"baja_registro encontrado: {baja_registro_desde_equipo}")
    print(f"Razón: {baja_registro_desde_equipo.razon_baja}")
    print(f"Fecha: {baja_registro_desde_equipo.fecha_baja}")
    print(f"Usuario: {baja_registro_desde_equipo.dado_de_baja_por.get_full_name()}")
    print(f"Observaciones: {baja_registro_desde_equipo.observaciones}")
    print("✓ La relación baja_registro funciona correctamente")
except Exception as e:
    print(f"✗ Error al acceder a baja_registro: {e}")

print("\n=== RESULTADO ===")
print("La información de baja debería mostrarse correctamente en el detalle del equipo.")
print("Verifica en la interfaz web que aparezca la sección 'Información de Baja' con:")
print("- Razón de Baja: ererer66666y6y")
print(f"- Fecha de Baja: {baja_test.fecha_baja.strftime('%d %b %Y')}")
print(f"- Dado de Baja Por: {usuario_test.get_full_name()}")
print("- Observaciones Adicionales: ererer")