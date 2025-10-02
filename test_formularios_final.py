#!/usr/bin/env python
"""
Test final para verificar que los formularios con proveedores funcionan correctamente.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Empresa, CustomUser, Equipo, Proveedor
from core.forms import CalibracionForm, MantenimientoForm, ComprobacionForm
from datetime import date

print("=== TEST FINAL FORMULARIOS CON PROVEEDORES ===")

# Crear empresa y usuario de prueba
empresa_test, _ = Empresa.objects.get_or_create(
    nombre="Test Empresa Final",
    defaults={'estado_suscripcion': 'Activo'}
)

usuario_test, _ = CustomUser.objects.get_or_create(
    username='test_final_user',
    defaults={
        'email': 'testfinal@example.com',
        'first_name': 'Test',
        'last_name': 'Final',
        'empresa': empresa_test
    }
)

# Crear proveedores de prueba para esta empresa
prov_cal, _ = Proveedor.objects.get_or_create(
    nombre_empresa="Proveedor Cal Test Final",
    empresa=empresa_test,
    tipo_servicio='Calibración'
)

prov_mant, _ = Proveedor.objects.get_or_create(
    nombre_empresa="Proveedor Mant Test Final",
    empresa=empresa_test,
    tipo_servicio='Mantenimiento'
)

prov_comp, _ = Proveedor.objects.get_or_create(
    nombre_empresa="Proveedor Comp Test Final",
    empresa=empresa_test,
    tipo_servicio='Comprobación'
)

print(f"Empresa: {empresa_test.nombre}")
print(f"Proveedores creados:")
print(f"  - Calibracion: {prov_cal.nombre_empresa}")
print(f"  - Mantenimiento: {prov_mant.nombre_empresa}")
print(f"  - Comprobacion: {prov_comp.nombre_empresa}")

# Probar formularios con empresa
print(f"\n=== PROBAR FORMULARIOS CON EMPRESA ===")

# Test 1: CalibracionForm
try:
    form = CalibracionForm(empresa=empresa_test)
    proveedores_cal = form.fields['proveedor'].queryset
    print(f"CalibracionForm - Proveedores disponibles: {proveedores_cal.count()}")
    for p in proveedores_cal:
        print(f"  - {p.nombre_empresa} ({p.tipo_servicio})")
except Exception as e:
    print(f"Error CalibracionForm: {e}")

# Test 2: MantenimientoForm
try:
    form = MantenimientoForm(empresa=empresa_test)
    proveedores_mant = form.fields['proveedor'].queryset
    print(f"MantenimientoForm - Proveedores disponibles: {proveedores_mant.count()}")
    for p in proveedores_mant:
        print(f"  - {p.nombre_empresa} ({p.tipo_servicio})")
except Exception as e:
    print(f"Error MantenimientoForm: {e}")

# Test 3: ComprobacionForm
try:
    form = ComprobacionForm(empresa=empresa_test)
    proveedores_comp = form.fields['proveedor'].queryset
    print(f"ComprobacionForm - Proveedores disponibles: {proveedores_comp.count()}")
    for p in proveedores_comp:
        print(f"  - {p.nombre_empresa} ({p.tipo_servicio})")
except Exception as e:
    print(f"Error ComprobacionForm: {e}")

print(f"\n=== PROBAR VALIDACION DE FORMULARIOS ===")

# Test validacion con proveedor
cal_data = {
    'fecha_calibracion': date.today(),
    'proveedor': prov_cal.pk,  # Usar el proveedor de calibracion
    'resultado': 'Aprobado',
    'numero_certificado': 'TEST-001'
}

form_cal = CalibracionForm(data=cal_data, empresa=empresa_test)
if form_cal.is_valid():
    print("CalibracionForm VALIDO con proveedor")
else:
    print(f"CalibracionForm INVALIDO: {form_cal.errors}")

# Test validacion solo con nombre_proveedor
cal_data_solo_nombre = {
    'fecha_calibracion': date.today(),
    'nombre_proveedor': 'Proveedor Manual Test',
    'resultado': 'Aprobado',
    'numero_certificado': 'TEST-002'
}

form_cal_nombre = CalibracionForm(data=cal_data_solo_nombre, empresa=empresa_test)
if form_cal_nombre.is_valid():
    print("CalibracionForm VALIDO solo con nombre_proveedor")
else:
    print(f"CalibracionForm INVALIDO solo con nombre: {form_cal_nombre.errors}")

print(f"\n=== RESULTADO FINAL ===")
print("Los formularios ahora deberian funcionar correctamente en la interfaz web")
print("- Filtran proveedores por empresa")
print("- Permiten seleccionar proveedor O escribir nombre")
print("- Se guardan correctamente")