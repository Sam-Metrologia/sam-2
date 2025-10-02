#!/usr/bin/env python3
"""
Script simplificado para crear datos de demostración para SAM Metrología
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
from core.models import Empresa, CustomUser, Equipo, Proveedor, Calibracion, Mantenimiento, Comprobacion, Ubicacion

User = get_user_model()

def crear_datos_demo():
    print("CREANDO DATOS PARA DEMO SAM METROLOGIA...")

    # 1. Empresa demo
    empresa_demo, created = Empresa.objects.get_or_create(
        nombre="CALIBRACIONES TÉCNICAS LTDA",
        defaults={
            'email': 'demo@calibraciones.com',
            'telefono': '+57 1 234-5678',
            'direccion': 'Calle 100 #15-30, Bogotá, Colombia',
            'nit': '900123456-7',
            'es_periodo_prueba': True,
            'duracion_prueba_dias': 30,
            'limite_equipos_empresa': 50,
            'limite_almacenamiento_mb': 5000,
            'fecha_inicio_plan': date.today(),
        }
    )
    print(f"[OK] Empresa: {empresa_demo.nombre}")

    # 2. Usuario demo
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
    print(f"[OK] Usuario: {usuario_demo.username} / demo123")

    # 3. Ubicaciones
    ubicaciones = ['Laboratorio Principal', 'Área de Calibración', 'Sala de Balanzas']
    for ubicacion_nombre in ubicaciones:
        ubicacion, created = Ubicacion.objects.get_or_create(
            nombre=ubicacion_nombre,
            empresa=empresa_demo,
            defaults={'descripcion': f'Ubicación {ubicacion_nombre}'}
        )
        print(f"[OK] Ubicación: {ubicacion.nombre}")

    # 4. Proveedores
    proveedores = [
        ('SERVICIOS METROLÓGICOS S.A.S', 'Calibración'),
        ('MANTENIMIENTO TÉCNICO LTDA', 'Mantenimiento'),
        ('VERIFICACIONES ESPECIALIZADAS', 'Comprobación')
    ]

    for nombre, tipo in proveedores:
        proveedor, created = Proveedor.objects.get_or_create(
            nombre_empresa=nombre,
            empresa=empresa_demo,
            defaults={
                'tipo_servicio': tipo,
                'correo_electronico': f'contacto@{nombre.lower().replace(" ", "")}.com',
                'numero_contacto': '+57 1 123-4567',
                'nombre_contacto': 'Gerente Tecnico'
            }
        )
        print(f"[OK] Proveedor: {proveedor.nombre_empresa}")

    # 5. Equipos
    equipos = [
        ('BAL-001', 'Balanza Analítica Digital', 'OHAUS', 'EX224', '2024001234'),
        ('CAL-001', 'Calibrador de Presión', 'FLUKE', '719Pro', '2024002468'),
        ('MUL-001', 'Multímetro Digital', 'KEYSIGHT', '34461A', '2024003579')
    ]

    for codigo, nombre, marca, modelo, serie in equipos:
        ubicacion_nombre = 'Laboratorio Principal'  # Usar nombre de ubicación como string

        equipo, created = Equipo.objects.get_or_create(
            codigo_interno=codigo,
            empresa=empresa_demo,
            defaults={
                'nombre': nombre,
                'marca': marca,
                'modelo': modelo,
                'numero_serie': serie,
                'tipo_equipo': 'Equipo de Medición',  # Usar valor válido del CHOICES
                'ubicacion': ubicacion_nombre,
                'estado': 'Activo',
                'fecha_adquisicion': date.today() - timedelta(days=365),
                'frecuencia_calibracion_meses': Decimal('12.00'),
                'frecuencia_mantenimiento_meses': Decimal('6.00'),
                'frecuencia_comprobacion_meses': Decimal('3.00'),
                'observaciones': f'Equipo {nombre} para mediciones de precisión'
            }
        )
        print(f"[OK] Equipo: {equipo.codigo_interno} - {equipo.nombre}")

    print("\n[DEMO] Datos creados exitosamente!")
    print(f"Usuario: demouser")
    print(f"Password: demo123")
    print(f"URL Login: http://127.0.0.1:8000/core/login/")
    print(f"URL Dashboard: http://127.0.0.1:8000/core/dashboard/")

if __name__ == "__main__":
    try:
        crear_datos_demo()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()