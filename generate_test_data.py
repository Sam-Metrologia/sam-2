#!/usr/bin/env python
# Script para generar datos de prueba sin problemas de migración

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import *
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def create_test_data():
    print("[INICIO] Generando datos de prueba...")

    # 1. Limpiar datos existentes
    print("[LIMPIEZA] Eliminando datos existentes...")
    Empresa.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    print("[LIMPIEZA] Datos eliminados")

    # 2. Crear empresas
    empresas_data = [
        {
            'nombre': 'Certicapital',
            'nit': '900123456-1',
            'direccion': 'Calle 72 #15-45, Bogotá',
            'telefono': '+57 1 3456789',
            'email': 'info@certicapital.co',
            'limite_equipos_empresa': 100,
            'limite_almacenamiento_mb': 5000
        },
        {
            'nombre': 'MetroTech Solutions',
            'nit': '800234567-2',
            'direccion': 'Carrera 50 #25-30, Medellín',
            'telefono': '+57 4 2345678',
            'email': 'ventas@metrotech.co',
            'limite_equipos_empresa': 75,
            'limite_almacenamiento_mb': 3000
        },
        {
            'nombre': 'Instrumentos Precisión Ltda',
            'nit': '900345678-3',
            'direccion': 'Avenida 19 #120-50, Cali',
            'telefono': '+57 2 3456789',
            'email': 'laboratorio@precision.co',
            'limite_equipos_empresa': 60,
            'limite_almacenamiento_mb': 2500
        },
        {
            'nombre': 'Laboratorios Calidad SAS',
            'nit': '800456789-4',
            'direccion': 'Calle 45 #28-15, Bucaramanga',
            'telefono': '+57 7 4567890',
            'email': 'control@calidad.co',
            'limite_equipos_empresa': 80,
            'limite_almacenamiento_mb': 4000
        },
        {
            'nombre': 'Control Metrológico Andino',
            'nit': '900567890-5',
            'direccion': 'Carrera 68 #80-32, Barranquilla',
            'telefono': '+57 5 5678901',
            'email': 'sistemas@andino.co',
            'limite_equipos_empresa': 90,
            'limite_almacenamiento_mb': 3500
        }
    ]

    empresas = []
    for data in empresas_data:
        empresa = Empresa.objects.create(**data)
        empresas.append(empresa)
        print(f"[EMPRESA] {empresa.nombre}")

    # 3. Crear equipos para cada empresa
    tipos_equipos = [
        ('Multímetro Digital', 'FLUKE', ['287', '289', '179', '175', '87V']),
        ('Osciloscopio Digital', 'Tektronix', ['TDS2024C', 'MSO3014', 'DPO4054B']),
        ('Fuente de Voltaje', 'Agilent', ['E3631A', 'E3632A', 'E3633A']),
        ('Termómetro Digital', 'OMEGA', ['HH374', 'HH378', 'HH506RA']),
        ('Balanza Electrónica', 'Ohaus', ['CP323', 'CP423', 'CP523']),
        ('Manómetro Digital', 'FLUKE', ['718Ex', '719Pro', '700G']),
        ('Cronómetro Digital', 'OMEGA', ['HH502', 'HH506', 'HH512']),
        ('Medidor de Presión', 'Keysight', ['34470A', '34461A', 'U1273A']),
        ('Generador de Funciones', 'Tektronix', ['AFG3022C', 'AFG3102C']),
        ('Analizador de Espectro', 'Keysight', ['N9020A', 'E4407B']),
    ]

    ubicaciones = [
        'Laboratorio Principal', 'Laboratorio Secundario', 'Área de Calibración',
        'Sala de Mediciones', 'Laboratorio de Temperatura', 'Área de Mantenimiento'
    ]

    total_equipos = 0
    for empresa_num, empresa in enumerate(empresas, 1):
        print(f"   [EQUIPOS] Generando equipos para {empresa.nombre}...")

        # Crear 50 equipos por empresa
        for i in range(50):
            tipo, marca, modelos = random.choice(tipos_equipos)
            modelo = random.choice(modelos)

            # Fechas realistas
            fecha_adquisicion = timezone.now() - timedelta(days=random.randint(30, 1825))

            # Programar fechas futuras (algunas vencidas para testing)
            dias_calibracion = random.randint(-30, 365)
            dias_mantenimiento = random.randint(-15, 180)
            dias_comprobacion = random.randint(-10, 90)

            equipo = Equipo.objects.create(
                empresa=empresa,
                codigo_interno=f'{empresa_num:02d}-{i+1:03d}',
                nombre=f'{tipo} {marca} {modelo}',
                marca=marca,
                modelo=modelo,
                numero_serie=f'SN{empresa_num:02d}{i+1:06d}',
                fecha_adquisicion=fecha_adquisicion,
                estado=random.choices(
                    ['Activo', 'En Mantenimiento', 'En Calibración', 'En Comprobación'],
                    weights=[85, 5, 5, 5]
                )[0],
                ubicacion=random.choice(ubicaciones),
                proxima_calibracion=timezone.now() + timedelta(days=dias_calibracion) if dias_calibracion > 0 else timezone.now() + timedelta(days=random.randint(1, 365)),
                proximo_mantenimiento=timezone.now() + timedelta(days=dias_mantenimiento) if dias_mantenimiento > 0 else timezone.now() + timedelta(days=random.randint(1, 180)),
                proxima_comprobacion=timezone.now() + timedelta(days=dias_comprobacion) if dias_comprobacion > 0 else timezone.now() + timedelta(days=random.randint(1, 90)),
            )
            total_equipos += 1

        print(f"   [EQUIPOS] 50 equipos creados para {empresa.nombre}")

        # Crear proveedores para cada empresa
        proveedores_data = [
            {
                'nombre_empresa': 'FLUKE Corporation',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'John Smith',
                'numero_contacto': '+1 425-347-6100',
                'correo_electronico': 'info@fluke.com',
                'empresa': empresa
            },
            {
                'nombre_empresa': 'Keysight Technologies',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'Maria Garcia',
                'numero_contacto': '+1 800-829-4444',
                'correo_electronico': 'contact@keysight.com',
                'empresa': empresa
            }
        ]

        for prov_data in proveedores_data:
            Proveedor.objects.create(**prov_data)

        print(f"   [PROVEEDORES] 2 proveedores creados para {empresa.nombre}")

        # Crear procedimientos básicos
        procedimientos = []
        try:
            for i, codigo in enumerate(['PC-001', 'PC-002', 'PC-003', 'PC-004']):
                proc = Procedimiento.objects.create(
                    codigo=codigo,
                    empresa=empresa
                )
                procedimientos.append(proc)
            print(f"   [PROCEDIMIENTOS] 4 procedimientos creados para {empresa.nombre}")
        except Exception as e:
            print(f"   [PROCEDIMIENTOS] Error creando procedimientos: {e}")
            # Crear procedimientos mínimos si hay error
            for i in range(2):
                try:
                    proc = Procedimiento.objects.create(codigo=f'PC-{i+1:03d}', empresa=empresa)
                    procedimientos.append(proc)
                except:
                    pass

        # Crear algunas calibraciones, mantenimientos y comprobaciones
        equipos_empresa = list(empresa.equipos.all())

        # Calibraciones
        for equipo in random.sample(equipos_empresa, min(20, len(equipos_empresa))):
            for i in range(random.randint(1, 3)):
                fecha_cal = timezone.now() - timedelta(days=random.randint(30, 365))
                Calibracion.objects.create(
                    equipo=equipo,
                    fecha_calibracion=fecha_cal,
                    procedimiento=random.choice(procedimientos),
                    resultado=random.choice(['Conforme', 'Conforme con observaciones']),
                    observaciones='Calibración exitosa, equipo dentro de especificaciones.'
                )

        # Mantenimientos
        for equipo in random.sample(equipos_empresa, min(15, len(equipos_empresa))):
            fecha_mant = timezone.now() - timedelta(days=random.randint(15, 300))
            Mantenimiento.objects.create(
                equipo=equipo,
                fecha_mantenimiento=fecha_mant,
                tipo_mantenimiento=random.choice(['Preventivo', 'Correctivo']),
                descripcion='Limpieza general y verificación de funcionamiento.',
                observaciones='Mantenimiento completado satisfactoriamente.'
            )

        # Comprobaciones
        for equipo in random.sample(equipos_empresa, min(10, len(equipos_empresa))):
            fecha_comp = timezone.now() - timedelta(days=random.randint(10, 180))
            Comprobacion.objects.create(
                equipo=equipo,
                fecha_comprobacion=fecha_comp,
                resultado='Satisfactorio',
                observaciones='Comprobación intermedia exitosa.'
            )

        print(f"   [ACTIVIDADES] Calibraciones, mantenimientos y comprobaciones creados")
        print("")

    print(f"[COMPLETADO] Datos de prueba creados exitosamente")
    print(f"Resumen:")
    print(f"   • {len(empresas)} empresas")
    print(f"   • {total_equipos} equipos")
    print(f"   • {Proveedor.objects.count()} proveedores")
    print(f"   • {Procedimiento.objects.count()} procedimientos")
    print(f"   • {Calibracion.objects.count()} calibraciones")
    print(f"   • {Mantenimiento.objects.count()} mantenimientos")
    print(f"   • {Comprobacion.objects.count()} comprobaciones")

    print("\n[INFO] Empresas creadas:")
    for empresa in empresas:
        equipos_count = empresa.equipos.count()
        print(f"   • {empresa.nombre}: {equipos_count} equipos")

if __name__ == "__main__":
    create_test_data()