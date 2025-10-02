#!/usr/bin/env python3
"""
Script para crear datos de demostración para SAM Metrología
Ejecutar con: python crear_datos_demo.py
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import (
    Empresa, CustomUser, Equipo, Proveedor,
    Calibracion, Mantenimiento, Comprobacion,
    Ubicacion
)

User = get_user_model()

def crear_datos_demo():
    print("DEMO Creando datos para demostración de SAM Metrología...")

    # 1. Crear empresa de demo
    print("\n📢 1. Creando empresa de demostración...")
    empresa_demo, created = Empresa.objects.get_or_create(
        nombre="CALIBRACIONES TÉCNICAS LTDA",
        defaults={
            'email': 'demo@calibraciones.com',
            'telefono': '+57 1 234-5678',
            'ciudad': 'Bogotá',
            'pais': 'Colombia',
            'direccion': 'Calle 100 #15-30, Zona Industrial',
            'nit': '900123456-7',
            'es_periodo_prueba': True,
            'duracion_prueba_dias': 30,
            'limite_equipos_empresa': 50,
            'limite_almacenamiento_mb': 5000,
            'fecha_inicio_plan': date.today(),
        }
    )
    print(f"✅ Empresa: {empresa_demo.nombre} {'(creada)' if created else '(ya existía)'}")

    # 2. Crear usuario de demo
    print("\n👤 2. Creando usuario de demostración...")
    usuario_demo, created = User.objects.get_or_create(
        username='demouser',
        defaults={
            'email': 'demo@calibraciones.com',
            'first_name': 'Juan Carlos',
            'last_name': 'Pérez',
            'empresa': empresa_demo,
            'is_staff': False,
            'is_active': True,
        }
    )

    if created:
        usuario_demo.set_password('demo123')
        usuario_demo.save()
        print(f"✅ Usuario: {usuario_demo.username} (creado)")
        print(f"   Password: demo123")
    else:
        print(f"✅ Usuario: {usuario_demo.username} (ya existía)")

    # 3. Crear ubicaciones
    print("\n📍 3. Creando ubicaciones...")
    ubicaciones = [
        'Laboratorio Principal', 'Área de Calibración', 'Sala de Balanzas',
        'Laboratorio de Temperatura', 'Área de Presión', 'Almacén de Equipos'
    ]

    for ubicacion_nombre in ubicaciones:
        ubicacion, created = Ubicacion.objects.get_or_create(
            nombre=ubicacion_nombre,
            empresa=empresa_demo,
            defaults={'descripcion': f'Ubicación para equipos en {ubicacion_nombre}'}
        )
        print(f"   {'➕' if created else '✅'} {ubicacion.nombre}")

    # 4. Crear proveedores
    print("\n🏭 4. Creando proveedores...")
    proveedores_data = [
        {
            'nombre': 'SERVICIOS METROLÓGICOS S.A.S',
            'tipo': 'Calibración',
            'email': 'servicios@metrologia.com',
            'telefono': '+57 1 345-6789'
        },
        {
            'nombre': 'MANTENIMIENTO TÉCNICO LTDA',
            'tipo': 'Mantenimiento',
            'email': 'soporte@mantecnico.com',
            'telefono': '+57 1 456-7890'
        },
        {
            'nombre': 'VERIFICACIONES ESPECIALIZADAS',
            'tipo': 'Comprobación',
            'email': 'info@verificaciones.com',
            'telefono': '+57 1 567-8901'
        }
    ]

    for prov_data in proveedores_data:
        proveedor, created = Proveedor.objects.get_or_create(
            nombre_empresa=prov_data['nombre'],
            empresa=empresa_demo,
            defaults={
                'tipo_servicio': prov_data['tipo'],
                'email': prov_data['email'],
                'telefono': prov_data['telefono'],
                'contacto_principal': 'Gerente Técnico',
                'activo': True
            }
        )
        print(f"   {'➕' if created else '✅'} {proveedor.nombre_empresa}")

    # 5. Crear equipos de demostración
    print("\n⚖️ 5. Creando equipos de demostración...")
    equipos_data = [
        {
            'codigo': 'BAL-001',
            'nombre': 'Balanza Analítica Digital',
            'marca': 'OHAUS',
            'modelo': 'Explorer EX224',
            'serie': '2024001234',
            'tipo': 'Balanza Analítica',
            'ubicacion': 'Sala de Balanzas',
            'frecuencia_cal': 12,
            'frecuencia_mant': 6,
            'frecuencia_comp': 3
        },
        {
            'codigo': 'CAL-001',
            'nombre': 'Calibrador de Presión Digital',
            'marca': 'FLUKE',
            'modelo': '719Pro',
            'serie': '2024002468',
            'tipo': 'Calibrador de Presión',
            'ubicacion': 'Área de Presión',
            'frecuencia_cal': 12,
            'frecuencia_mant': 12,
            'frecuencia_comp': 6
        },
        {
            'codigo': 'MUL-001',
            'nombre': 'Multímetro Digital de Precisión',
            'marca': 'KEYSIGHT',
            'modelo': '34461A',
            'serie': '2024003579',
            'tipo': 'Multímetro Digital',
            'ubicacion': 'Laboratorio Principal',
            'frecuencia_cal': 12,
            'frecuencia_mant': 24,
            'frecuencia_comp': 6
        }
    ]

    for equipo_data in equipos_data:
        ubicacion = Ubicacion.objects.get(nombre=equipo_data['ubicacion'], empresa=empresa_demo)

        equipo, created = Equipo.objects.get_or_create(
            codigo_interno=equipo_data['codigo'],
            empresa=empresa_demo,
            defaults={
                'nombre': equipo_data['nombre'],
                'marca': equipo_data['marca'],
                'modelo': equipo_data['modelo'],
                'numero_serie': equipo_data['serie'],
                'tipo_equipo': equipo_data['tipo'],  # Como string
                'ubicacion': ubicacion,
                'estado': 'Activo',
                'fecha_adquisicion': date.today() - timedelta(days=365),
                'frecuencia_calibracion_meses': equipo_data['frecuencia_cal'],
                'frecuencia_mantenimiento_meses': equipo_data['frecuencia_mant'],
                'frecuencia_comprobacion_meses': equipo_data['frecuencia_comp'],
                'valor_compra': Decimal('5500000.00'),
                'observaciones': f'Equipo {equipo_data["nombre"]} para mediciones de precisión'
            }
        )
        print(f"   {'➕' if created else '✅'} {equipo.codigo_interno} - {equipo.nombre}")

    # 6. Crear algunas actividades de ejemplo
    print("\n📋 6. Creando actividades de ejemplo...")

    # Obtener equipos y proveedores
    balanza = Equipo.objects.get(codigo_interno='BAL-001', empresa=empresa_demo)
    calibrador = Equipo.objects.get(codigo_interno='CAL-001', empresa=empresa_demo)

    prov_cal = Proveedor.objects.get(nombre_empresa='SERVICIOS METROLÓGICOS S.A.S', empresa=empresa_demo)
    prov_mant = Proveedor.objects.get(nombre_empresa='MANTENIMIENTO TÉCNICO LTDA', empresa=empresa_demo)
    prov_comp = Proveedor.objects.get(nombre_empresa='VERIFICACIONES ESPECIALIZADAS', empresa=empresa_demo)

    # Calibración reciente
    cal, created = Calibracion.objects.get_or_create(
        equipo=balanza,
        fecha_calibracion=date.today() - timedelta(days=15),
        defaults={
            'proveedor': prov_cal,
            'resultado': 'Aprobado',
            'numero_certificado': 'CAL-2024-001234',
            'observaciones': 'Calibración exitosa dentro de tolerancias especificadas',
        }
    )
    if created:
        print(f"   ➕ Calibración: {cal.equipo.codigo_interno} - {cal.fecha_calibracion}")

    # Mantenimiento preventivo
    mant, created = Mantenimiento.objects.get_or_create(
        equipo=calibrador,
        fecha_mantenimiento=date.today() - timedelta(days=30),
        defaults={
            'tipo_mantenimiento': 'Preventivo',
            'proveedor': prov_mant,
            'responsable': 'Técnico Especializado',
            'descripcion': 'Mantenimiento preventivo programado - Limpieza y calibración interna',
            'costo': Decimal('450000.00'),
        }
    )
    if created:
        print(f"   ➕ Mantenimiento: {mant.equipo.codigo_interno} - {mant.fecha_mantenimiento}")

    # Comprobación
    comp, created = Comprobacion.objects.get_or_create(
        equipo=balanza,
        fecha_comprobacion=date.today() - timedelta(days=7),
        defaults={
            'proveedor': prov_comp,
            'tipo_comprobacion': 'Verificación intermedia',
            'resultado': 'Conforme',
            'observaciones': 'Verificación intermedia satisfactoria',
        }
    )
    if created:
        print(f"   ➕ Comprobación: {comp.equipo.codigo_interno} - {comp.fecha_comprobacion}")

    print(f"\n🎉 ¡Datos de demostración creados exitosamente!")
    print(f"\n📊 RESUMEN:")
    print(f"   🏢 Empresa: {empresa_demo.nombre}")
    print(f"   👤 Usuario: {usuario_demo.username} / demo123")
    print(f"   ⚙️ Equipos: {Equipo.objects.filter(empresa=empresa_demo).count()}")
    print(f"   🏭 Proveedores: {Proveedor.objects.filter(empresa=empresa_demo).count()}")
    print(f"   📋 Calibraciones: {Calibracion.objects.filter(equipo__empresa=empresa_demo).count()}")
    print(f"   🔧 Mantenimientos: {Mantenimiento.objects.filter(equipo__empresa=empresa_demo).count()}")
    print(f"   ✅ Comprobaciones: {Comprobacion.objects.filter(equipo__empresa=empresa_demo).count()}")

    print(f"\n🌐 URLs para el demo:")
    print(f"   🔐 Login: http://127.0.0.1:8000/core/login/")
    print(f"   📊 Dashboard: http://127.0.0.1:8000/core/dashboard/")
    print(f"   ⚙️ Equipos: http://127.0.0.1:8000/core/")
    print(f"   👤 Admin: http://127.0.0.1:8000/admin/")

if __name__ == "__main__":
    try:
        crear_datos_demo()
    except Exception as e:
        print(f"❌ Error creando datos de demo: {e}")
        import traceback
        traceback.print_exc()