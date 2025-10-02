#!/usr/bin/env python3
"""
Script para crear actividades de demostración (Calibraciones, Mantenimientos, Comprobaciones)
para SAM Metrología
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Configuración Django
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, CustomUser, Equipo, Proveedor, Calibracion, Mantenimiento, Comprobacion

User = get_user_model()

def crear_actividades_demo():
    print("CREANDO ACTIVIDADES DE DEMO SAM METROLOGIA...")

    # Obtener empresa y equipos demo
    try:
        empresa_demo = Empresa.objects.get(nombre="CALIBRACIONES TÉCNICAS LTDA")
    except Empresa.DoesNotExist:
        print("ERROR: No se encontro la empresa de demo. Ejecute crear_datos_demo_simple.py primero.")
        return

    equipos = Equipo.objects.filter(empresa=empresa_demo)
    if not equipos.exists():
        print("ERROR: No se encontraron equipos de demo.")
        return

    # Obtener proveedores
    try:
        prov_cal = Proveedor.objects.get(nombre_empresa='SERVICIOS METROLÓGICOS S.A.S', empresa=empresa_demo)
        prov_mant = Proveedor.objects.get(nombre_empresa='MANTENIMIENTO TÉCNICO LTDA', empresa=empresa_demo)
        prov_comp = Proveedor.objects.get(nombre_empresa='VERIFICACIONES ESPECIALIZADAS', empresa=empresa_demo)
    except Proveedor.DoesNotExist:
        print("ERROR: No se encontraron proveedores de demo.")
        return

    print("[OK] Datos base encontrados")

    # 1. CALIBRACIONES
    print("\n1. Creando calibraciones...")
    calibraciones_data = [
        {
            'equipo_codigo': 'BAL-001',
            'fecha': date.today() - timedelta(days=15),
            'resultado': 'Aprobado',
            'certificado': 'CAL-2024-001234',
            'observaciones': 'Calibracion exitosa dentro de tolerancias especificadas'
        },
        {
            'equipo_codigo': 'CAL-001',
            'fecha': date.today() - timedelta(days=45),
            'resultado': 'Aprobado',
            'certificado': 'CAL-2024-001235',
            'observaciones': 'Calibracion de presion conforme a especificaciones'
        },
        {
            'equipo_codigo': 'MUL-001',
            'fecha': date.today() - timedelta(days=30),
            'resultado': 'Condicional',
            'certificado': 'CAL-2024-001236',
            'observaciones': 'Calibracion con observaciones menores - revisar en 3 meses'
        }
    ]

    for cal_data in calibraciones_data:
        equipo = Equipo.objects.get(codigo_interno=cal_data['equipo_codigo'], empresa=empresa_demo)
        calibracion, created = Calibracion.objects.get_or_create(
            equipo=equipo,
            fecha_calibracion=cal_data['fecha'],
            defaults={
                'proveedor': prov_cal,
                'resultado': cal_data['resultado'],
                'numero_certificado': cal_data['certificado'],
                'observaciones': cal_data['observaciones'],
            }
        )
        print(f"   {'[NUEVO]' if created else '[EXISTE]'} Calibracion: {equipo.codigo_interno} - {cal_data['fecha']}")

    # 2. MANTENIMIENTOS
    print("\n2. Creando mantenimientos...")
    mantenimientos_data = [
        {
            'equipo_codigo': 'BAL-001',
            'fecha': date.today() - timedelta(days=60),
            'tipo': 'Preventivo',
            'descripcion': 'Limpieza general y calibracion interna de la balanza',
            'responsable': 'Tecnico Juan Perez',
            'costo': Decimal('350000.00')
        },
        {
            'equipo_codigo': 'CAL-001',
            'fecha': date.today() - timedelta(days=90),
            'tipo': 'Correctivo',
            'descripcion': 'Reemplazo de sensor de presion y actualizacion de firmware',
            'responsable': 'Tecnico Maria Garcia',
            'costo': Decimal('850000.00')
        },
        {
            'equipo_codigo': 'MUL-001',
            'fecha': date.today() - timedelta(days=120),
            'tipo': 'Preventivo',
            'descripcion': 'Revision general y limpieza de contactos internos',
            'responsable': 'Tecnico Carlos Rodriguez',
            'costo': Decimal('450000.00')
        }
    ]

    for mant_data in mantenimientos_data:
        equipo = Equipo.objects.get(codigo_interno=mant_data['equipo_codigo'], empresa=empresa_demo)
        mantenimiento, created = Mantenimiento.objects.get_or_create(
            equipo=equipo,
            fecha_mantenimiento=mant_data['fecha'],
            defaults={
                'tipo_mantenimiento': mant_data['tipo'],
                'proveedor': prov_mant,
                'responsable': mant_data['responsable'],
                'descripcion': mant_data['descripcion'],
                'costo': mant_data['costo'],
            }
        )
        print(f"   {'[NUEVO]' if created else '[EXISTE]'} Mantenimiento: {equipo.codigo_interno} - {mant_data['fecha']}")

    # 3. COMPROBACIONES
    print("\n3. Creando comprobaciones...")
    comprobaciones_data = [
        {
            'equipo_codigo': 'BAL-001',
            'fecha': date.today() - timedelta(days=7),
            'resultado': 'Aprobado',
            'observaciones': 'Verificacion intermedia satisfactoria - equipo en condiciones optimas',
            'responsable': 'Verificador Juan Martinez'
        },
        {
            'equipo_codigo': 'CAL-001',
            'fecha': date.today() - timedelta(days=14),
            'resultado': 'Aprobado',
            'observaciones': 'Comprobacion funcional exitosa - todos los parametros dentro de especificaciones',
            'responsable': 'Verificador Ana Gutierrez'
        },
        {
            'equipo_codigo': 'MUL-001',
            'fecha': date.today() - timedelta(days=21),
            'resultado': 'No Aprobado',
            'observaciones': 'Deriva detectada en rango de 10V - requiere calibracion inmediata',
            'responsable': 'Verificador Carlos Mendez'
        }
    ]

    for comp_data in comprobaciones_data:
        equipo = Equipo.objects.get(codigo_interno=comp_data['equipo_codigo'], empresa=empresa_demo)
        comprobacion, created = Comprobacion.objects.get_or_create(
            equipo=equipo,
            fecha_comprobacion=comp_data['fecha'],
            defaults={
                'proveedor': prov_comp,
                'responsable': comp_data['responsable'],
                'resultado': comp_data['resultado'],
                'observaciones': comp_data['observaciones'],
            }
        )
        print(f"   {'[NUEVO]' if created else '[EXISTE]'} Comprobacion: {equipo.codigo_interno} - {comp_data['fecha']}")

    print(f"\n[DEMO] Actividades creadas exitosamente!")
    print(f"\nRESUMEN:")
    print(f"   Calibraciones: {Calibracion.objects.filter(equipo__empresa=empresa_demo).count()}")
    print(f"   Mantenimientos: {Mantenimiento.objects.filter(equipo__empresa=empresa_demo).count()}")
    print(f"   Comprobaciones: {Comprobacion.objects.filter(equipo__empresa=empresa_demo).count()}")

if __name__ == "__main__":
    try:
        crear_actividades_demo()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()