#!/usr/bin/env python
"""
Test simple para verificar que los formularios se guardan correctamente.
"""

import os
import sys
import django
from datetime import date

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Empresa, CustomUser, Equipo, Calibracion, Mantenimiento, Comprobacion

print("=== TEST SIMPLE GUARDADO DE FORMULARIOS ===")

# Usar datos existentes o crear nuevos
empresa_test, _ = Empresa.objects.get_or_create(
    nombre="Test Empresa Simple",
    defaults={'estado_suscripcion': 'Activo'}
)

usuario_test, _ = CustomUser.objects.get_or_create(
    username='test_simple_user',
    defaults={
        'email': 'testsimple@example.com',
        'first_name': 'Test',
        'last_name': 'Simple',
        'empresa': empresa_test
    }
)

equipo_test, _ = Equipo.objects.get_or_create(
    codigo_interno='EQ-TEST-SIMPLE-001',
    defaults={
        'nombre': 'Equipo Test Simple',
        'empresa': empresa_test,
        'estado': 'Activo'
    }
)

print(f"Empresa: {empresa_test.nombre}")
print(f"Equipo: {equipo_test.nombre}")

# Test Calibracion
try:
    calibracion = Calibracion.objects.create(
        equipo=equipo_test,
        fecha_calibracion=date.today(),
        proveedor='interno',
        nombre_proveedor='Test Proveedor Cal',
        resultado='Satisfactorio',
        numero_certificado='CERT-001',
        observaciones='Test calibracion OK'
    )
    print(f"Calibracion creada: ID {calibracion.pk}")
except Exception as e:
    print(f"Error calibracion: {e}")

# Test Mantenimiento
try:
    mantenimiento = Mantenimiento.objects.create(
        equipo=equipo_test,
        fecha_mantenimiento=date.today(),
        tipo_mantenimiento='Preventivo',
        proveedor='interno',
        nombre_proveedor='Test Proveedor Mant',
        responsable='Test Responsable',
        costo=100000,
        descripcion='Test mantenimiento OK',
        observaciones='Test mantenimiento OK'
    )
    print(f"Mantenimiento creado: ID {mantenimiento.pk}")
except Exception as e:
    print(f"Error mantenimiento: {e}")

# Test Comprobacion
try:
    comprobacion = Comprobacion.objects.create(
        equipo=equipo_test,
        fecha_comprobacion=date.today(),
        proveedor='interno',
        nombre_proveedor='Test Proveedor Comp',
        responsable='Test Responsable Comp',
        resultado='Satisfactorio',
        observaciones='Test comprobacion OK'
    )
    print(f"Comprobacion creada: ID {comprobacion.pk}")
except Exception as e:
    print(f"Error comprobacion: {e}")

# Contar registros
cal_count = Calibracion.objects.filter(equipo=equipo_test).count()
mant_count = Mantenimiento.objects.filter(equipo=equipo_test).count()
comp_count = Comprobacion.objects.filter(equipo=equipo_test).count()

print(f"\nRegistros en BD:")
print(f"Calibraciones: {cal_count}")
print(f"Mantenimientos: {mant_count}")
print(f"Comprobaciones: {comp_count}")

if cal_count > 0 and mant_count > 0 and comp_count > 0:
    print("\nTODOS LOS REGISTROS SE GUARDARON CORRECTAMENTE!")
else:
    print("\nHAY PROBLEMAS CON EL GUARDADO")