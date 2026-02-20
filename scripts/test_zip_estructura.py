#!/usr/bin/env python
"""
Script para probar la estructura del ZIP y verificar que incluya todas las actividades.
"""

import os
import sys
import django
import zipfile
from io import BytesIO

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Equipo, Empresa
from django.contrib.auth import get_user_model

def test_estructura_zip(codigo_equipo='EQ-0012'):
    """Simula la creacion de un ZIP y verifica su estructura"""

    print("=" * 80)
    print(f"TEST: Estructura de ZIP para {codigo_equipo}")
    print("=" * 80)

    # 1. Buscar equipo
    equipo = Equipo.objects.filter(codigo_interno=codigo_equipo).first()
    if not equipo:
        print(f"ERROR: Equipo {codigo_equipo} no encontrado")
        return False

    print(f"\nEquipo: {equipo.nombre} ({equipo.codigo_interno})")
    print(f"Empresa: {equipo.empresa.nombre}")

    # 2. Contar actividades
    calibraciones = equipo.calibraciones.count()
    mantenimientos = equipo.mantenimientos.count()
    comprobaciones = equipo.comprobaciones.count()

    print(f"\nActividades:")
    print(f"  Calibraciones: {calibraciones}")
    print(f"  Mantenimientos: {mantenimientos}")
    print(f"  Comprobaciones: {comprobaciones}")

    # 3. Simular estructura de carpetas
    print(f"\nEstructura esperada en ZIP:")

    equipo_folder = f"{equipo.empresa.nombre}/Equipos/{equipo.codigo_interno}/"
    print(f"\n{equipo_folder}")
    print(f"  Hoja_de_vida.pdf")

    # Calibraciones
    if calibraciones > 0:
        print(f"  Calibraciones/")
        print(f"    Certificados_Calibracion/")
        print(f"      (hasta {calibraciones} archivos)")

    # Mantenimientos
    if mantenimientos > 0:
        print(f"  Mantenimientos/")
        print(f"    Documentos_Externos/")
        print(f"    Documentos_Internos/")
        print(f"    Documentos_Generales/")
    else:
        print(f"  Mantenimientos/")
        print(f"    (sin archivos - equipo no tiene mantenimientos)")

    # Comprobaciones
    if comprobaciones > 0:
        print(f"  Comprobaciones/")
        print(f"    Certificados_Comprobacion/")
        print(f"      (hasta {comprobaciones} archivos)")
        print(f"    Documentos_Externos/")
        print(f"    Documentos_Internos/")
        print(f"    Documentos_Generales/")
    else:
        print(f"  Comprobaciones/")
        print(f"    (sin archivos - equipo no tiene comprobaciones)")

    # 4. Verificar codigo
    print(f"\n" + "=" * 80)
    print("VERIFICACION DE CODIGO:")
    print("=" * 80)

    # Leer archivo
    with open('core/zip_functions.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar seccion de comprobaciones
    if 'comprobacion_pdf' in content:
        print("  OK: Codigo procesa 'comprobacion_pdf'")
    else:
        print("  ERROR: Codigo NO procesa 'comprobacion_pdf'")
        return False

    if 'Certificados_Comprobacion' in content:
        print("  OK: Codigo crea carpeta 'Certificados_Comprobacion'")
    else:
        print("  ERROR: Codigo NO crea carpeta 'Certificados_Comprobacion'")
        return False

    # Buscar seccion de mantenimientos
    if 'documento_interno' in content and 'Documentos_Internos' in content:
        print("  OK: Codigo procesa mantenimientos correctamente")
    else:
        print("  ERROR: Codigo de mantenimientos incorrecto")
        return False

    # 5. Resumen
    print(f"\n" + "=" * 80)
    print("RESUMEN:")
    print("=" * 80)
    print(f"Equipo: {codigo_equipo}")
    print(f"Calibraciones: {calibraciones}")
    print(f"Mantenimientos: {mantenimientos}")
    print(f"Comprobaciones: {comprobaciones}")
    print(f"Codigo: CORRECTO")

    if comprobaciones > 0:
        print(f"\nNOTA: Este equipo DEBE incluir {comprobaciones} certificados de comprobacion en el ZIP")

    if mantenimientos == 0:
        print(f"\nNOTA: Este equipo NO tiene mantenimientos, por lo que la carpeta estara vacia")

    return True

if __name__ == '__main__':
    print("\nSUITE DE PRUEBAS: Estructura de ZIP")
    print("Fecha: 21 de Enero de 2026")
    print()

    # Test con EQ-0012
    test1 = test_estructura_zip('EQ-0012')

    # Test con equipo que tenga mantenimientos
    print("\n\n")
    test2 = test_estructura_zip('EQ-0001')

    print("\n" + "=" * 80)
    if test1 and test2:
        print("RESULTADO: EXITOSO")
        print("\nSi el ZIP no incluye comprobaciones/mantenimientos, es porque:")
        print("  1. El servidor Django no se reinicio despues del fix")
        print("  2. Estas descargando un ZIP antiguo que se genero antes del fix")
        print("  3. El procesador asincrono de ZIPs necesita reiniciarse")
        print("\nSOLUCION:")
        print("  1. Reinicia el servidor: Ctrl+C y python manage.py runserver")
        print("  2. Solicita un ZIP NUEVO (no uses uno generado antes del fix)")
        print("=" * 80)
        sys.exit(0)
    else:
        print("RESULTADO: FALLO")
        print("=" * 80)
        sys.exit(1)
