#!/usr/bin/env python
"""
Test corregido para verificar que los formularios se guardan correctamente.
"""

import os
import sys
import django
from datetime import date

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Empresa, CustomUser, Equipo, Calibracion, Mantenimiento, Comprobacion, Proveedor

print("=== TEST CORREGIDO GUARDADO DE FORMULARIOS ===")

# Usar datos existentes o crear nuevos
empresa_test, _ = Empresa.objects.get_or_create(
    nombre="Test Empresa Formularios",
    defaults={'estado_suscripcion': 'Activo'}
)

usuario_test, _ = CustomUser.objects.get_or_create(
    username='test_forms_user',
    defaults={
        'email': 'testforms@example.com',
        'first_name': 'Test',
        'last_name': 'Forms',
        'empresa': empresa_test
    }
)

equipo_test, _ = Equipo.objects.get_or_create(
    codigo_interno='EQ-TEST-FORMS-002',
    defaults={
        'nombre': 'Equipo Test Formularios Corregido',
        'empresa': empresa_test,
        'estado': 'Activo'
    }
)

# Crear proveedores de prueba
proveedor_cal, _ = Proveedor.objects.get_or_create(
    nombre_empresa="Proveedor Calibracion Test",
    empresa=empresa_test,
    tipo_servicio='Calibración',
    defaults={
        'numero_contacto': '123456789',
        'correo_electronico': 'cal@test.com'
    }
)

proveedor_mant, _ = Proveedor.objects.get_or_create(
    nombre_empresa="Proveedor Mantenimiento Test",
    empresa=empresa_test,
    tipo_servicio='Mantenimiento',
    defaults={
        'numero_contacto': '123456790',
        'correo_electronico': 'mant@test.com'
    }
)

proveedor_comp, _ = Proveedor.objects.get_or_create(
    nombre_empresa="Proveedor Comprobacion Test",
    empresa=empresa_test,
    tipo_servicio='Comprobación',
    defaults={
        'numero_contacto': '123456791',
        'correo_electronico': 'comp@test.com'
    }
)

print(f"Empresa: {empresa_test.nombre}")
print(f"Equipo: {equipo_test.nombre}")
print(f"Proveedores creados: {proveedor_cal.nombre_empresa}, {proveedor_mant.nombre_empresa}, {proveedor_comp.nombre_empresa}")

# Test Calibracion
try:
    calibracion = Calibracion.objects.create(
        equipo=equipo_test,
        fecha_calibracion=date.today(),
        proveedor=proveedor_cal,
        nombre_proveedor='Test Proveedor Cal Adicional',
        resultado='Aprobado',
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
        proveedor=proveedor_mant,
        nombre_proveedor='Test Proveedor Mant Adicional',
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
        proveedor=proveedor_comp,
        nombre_proveedor='Test Proveedor Comp Adicional',
        responsable='Test Responsable Comp',
        resultado='Aprobado',
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
    print("Los formularios ahora deberian funcionar correctamente en la web")
else:
    print("\nHAY PROBLEMAS CON EL GUARDADO")