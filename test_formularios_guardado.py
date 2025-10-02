#!/usr/bin/env python
"""
Test para verificar que los formularios de calibracion, mantenimiento y comprobacion se guardan correctamente.
"""

import os
import sys
import django
from datetime import date, datetime

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Empresa, CustomUser, Equipo, Calibracion, Mantenimiento, Comprobacion
from core.forms import CalibracionForm, MantenimientoForm, ComprobacionForm

print("=== TEST GUARDADO DE FORMULARIOS ===")

# Crear datos de prueba
empresa_test, _ = Empresa.objects.get_or_create(
    nombre="Test Empresa Formularios",
    defaults={'estado_suscripcion': 'Activo'}
)

usuario_test, _ = CustomUser.objects.get_or_create(
    username='test_forms_user',
    defaults={
        'email': 'testforms@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'empresa': empresa_test
    }
)

equipo_test, _ = Equipo.objects.get_or_create(
    codigo_interno='EQ-TEST-FORMS-001',
    defaults={
        'nombre': 'Equipo Test Formularios',
        'empresa': empresa_test,
        'estado': 'Activo'
    }
)

print(f"Empresa: {empresa_test.nombre}")
print(f"Usuario: {usuario_test.get_full_name() or usuario_test.username}")
print(f"Equipo: {equipo_test.nombre} ({equipo_test.codigo_interno})")

# Test 1: Formulario de Calibración
print(f"\n=== TEST 1: CALIBRACIÓN ===")
form_data = {
    'fecha_calibracion': date.today(),
    'proveedor': 'interno',
    'nombre_proveedor': 'Test Proveedor Calibración',
    'resultado': 'Satisfactorio',
    'numero_certificado': 'CERT-CAL-001',
    'observaciones': 'Test de calibración funcionando'
}

form = CalibracionForm(data=form_data)
if form.is_valid():
    try:
        calibracion = Calibracion(
            equipo=equipo_test,
            fecha_calibracion=form.cleaned_data['fecha_calibracion'],
            proveedor=form.cleaned_data['proveedor'],
            nombre_proveedor=form.cleaned_data['nombre_proveedor'],
            resultado=form.cleaned_data['resultado'],
            numero_certificado=form.cleaned_data['numero_certificado'],
            observaciones=form.cleaned_data['observaciones'],
        )
        calibracion.save()
        print(f"✓ Calibración creada con ID: {calibracion.pk}")
        print(f"  - Fecha: {calibracion.fecha_calibracion}")
        print(f"  - Proveedor: {calibracion.nombre_proveedor}")
        print(f"  - Resultado: {calibracion.resultado}")
    except Exception as e:
        print(f"✗ Error creando calibración: {e}")
else:
    print(f"✗ Formulario de calibración inválido: {form.errors}")

# Test 2: Formulario de Mantenimiento
print(f"\n=== TEST 2: MANTENIMIENTO ===")
form_data = {
    'fecha_mantenimiento': date.today(),
    'tipo_mantenimiento': 'Preventivo',
    'proveedor': 'externo',
    'nombre_proveedor': 'Test Proveedor Mantenimiento',
    'responsable': 'Test Responsable',
    'costo': 150000,
    'descripcion': 'Test de mantenimiento preventivo',
    'observaciones': 'Test de mantenimiento funcionando'
}

form = MantenimientoForm(data=form_data)
if form.is_valid():
    try:
        mantenimiento = Mantenimiento(
            equipo=equipo_test,
            fecha_mantenimiento=form.cleaned_data['fecha_mantenimiento'],
            tipo_mantenimiento=form.cleaned_data['tipo_mantenimiento'],
            proveedor=form.cleaned_data['proveedor'],
            nombre_proveedor=form.cleaned_data['nombre_proveedor'],
            responsable=form.cleaned_data['responsable'],
            costo=form.cleaned_data['costo'],
            descripcion=form.cleaned_data['descripcion'],
            observaciones=form.cleaned_data['observaciones'],
        )
        mantenimiento.save()
        print(f"✓ Mantenimiento creado con ID: {mantenimiento.pk}")
        print(f"  - Fecha: {mantenimiento.fecha_mantenimiento}")
        print(f"  - Tipo: {mantenimiento.tipo_mantenimiento}")
        print(f"  - Proveedor: {mantenimiento.nombre_proveedor}")
        print(f"  - Costo: ${mantenimiento.costo:,}")
    except Exception as e:
        print(f"✗ Error creando mantenimiento: {e}")
else:
    print(f"✗ Formulario de mantenimiento inválido: {form.errors}")

# Test 3: Formulario de Comprobación
print(f"\n=== TEST 3: COMPROBACIÓN ===")
form_data = {
    'fecha_comprobacion': date.today(),
    'proveedor': 'interno',
    'nombre_proveedor': 'Test Proveedor Comprobación',
    'responsable': 'Test Responsable Comprobación',
    'resultado': 'Satisfactorio',
    'observaciones': 'Test de comprobación funcionando'
}

form = ComprobacionForm(data=form_data)
if form.is_valid():
    try:
        comprobacion = Comprobacion(
            equipo=equipo_test,
            fecha_comprobacion=form.cleaned_data['fecha_comprobacion'],
            proveedor=form.cleaned_data['proveedor'],
            nombre_proveedor=form.cleaned_data['nombre_proveedor'],
            responsable=form.cleaned_data['responsable'],
            resultado=form.cleaned_data['resultado'],
            observaciones=form.cleaned_data['observaciones'],
        )
        comprobacion.save()
        print(f"✓ Comprobación creada con ID: {comprobacion.pk}")
        print(f"  - Fecha: {comprobacion.fecha_comprobacion}")
        print(f"  - Proveedor: {comprobacion.nombre_proveedor}")
        print(f"  - Resultado: {comprobacion.resultado}")
    except Exception as e:
        print(f"✗ Error creando comprobación: {e}")
else:
    print(f"✗ Formulario de comprobación inválido: {form.errors}")

# Verificar que los registros están en la base de datos
print(f"\n=== VERIFICACIÓN EN BASE DE DATOS ===")
calibraciones_count = Calibracion.objects.filter(equipo=equipo_test).count()
mantenimientos_count = Mantenimiento.objects.filter(equipo=equipo_test).count()
comprobaciones_count = Comprobacion.objects.filter(equipo=equipo_test).count()

print(f"Calibraciones en BD: {calibraciones_count}")
print(f"Mantenimientos en BD: {mantenimientos_count}")
print(f"Comprobaciones en BD: {comprobaciones_count}")

print(f"\n=== RESULTADO ===")
if calibraciones_count > 0 and mantenimientos_count > 0 and comprobaciones_count > 0:
    print("✓ TODOS LOS FORMULARIOS SE ESTÁN GUARDANDO CORRECTAMENTE")
else:
    print("✗ HAY PROBLEMAS CON EL GUARDADO DE ALGUNOS FORMULARIOS")