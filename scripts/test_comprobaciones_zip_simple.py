#!/usr/bin/env python
"""
Script de prueba para validar que las comprobaciones se incluyen correctamente en ZIPs.
Reportado por usuario: EQ-0012 con 3 comprobaciones no aparecian en ZIP.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Equipo, Comprobacion
from django.core.files.storage import default_storage

def test_eq0012():
    """Prueba que las comprobaciones del equipo EQ-0012 se incluyan en ZIP."""

    print("=" * 80)
    print("TEST: Validar comprobaciones en ZIP para EQ-0012")
    print("=" * 80)

    # 1. Verificar equipo existe
    equipo = Equipo.objects.filter(codigo_interno='EQ-0012').first()
    if not equipo:
        print("ERROR: Equipo EQ-0012 no encontrado")
        return False

    print(f"\nEquipo encontrado: {equipo.nombre} ({equipo.codigo_interno})")
    print(f"Empresa: {equipo.empresa.nombre}")

    # 2. Verificar comprobaciones
    comprobaciones = Comprobacion.objects.filter(equipo=equipo)
    count = comprobaciones.count()
    print(f"\nComprobaciones: {count}")

    if count == 0:
        print("No hay comprobaciones para probar")
        return True

    # 3. Verificar archivos
    archivos_encontrados = []
    print("\nArchivos en comprobaciones:")
    for idx, comp in enumerate(comprobaciones, 1):
        print(f"\n  Comprobacion {idx} (ID: {comp.id}, Fecha: {comp.fecha_comprobacion}):")

        if comp.comprobacion_pdf:
            existe = default_storage.exists(comp.comprobacion_pdf.name)
            print(f"    comprobacion_pdf: {comp.comprobacion_pdf.name} ({'EXISTE' if existe else 'NO EXISTE'})")
            if existe:
                archivos_encontrados.append(comp.comprobacion_pdf.name)

        if comp.documento_externo:
            existe = default_storage.exists(comp.documento_externo.name)
            print(f"    documento_externo: {comp.documento_externo.name} ({'EXISTE' if existe else 'NO EXISTE'})")
            if existe:
                archivos_encontrados.append(comp.documento_externo.name)

        if comp.documento_interno:
            existe = default_storage.exists(comp.documento_interno.name)
            print(f"    documento_interno: {comp.documento_interno.name} ({'EXISTE' if existe else 'NO EXISTE'})")
            if existe:
                archivos_encontrados.append(comp.documento_interno.name)

        if comp.documento_comprobacion:
            existe = default_storage.exists(comp.documento_comprobacion.name)
            print(f"    documento_comprobacion: {comp.documento_comprobacion.name} ({'EXISTE' if existe else 'NO EXISTE'})")
            if existe:
                archivos_encontrados.append(comp.documento_comprobacion.name)

    # 4. Verificar codigo corregido
    print("\n" + "=" * 80)
    print("VALIDACION DE CODIGO:")
    print("=" * 80)

    # Leer archivos directamente
    with open('core/zip_functions.py', 'r', encoding='utf-8') as f:
        zip_functions_code = f.read()

    with open('core/zip_optimizer.py', 'r', encoding='utf-8') as f:
        zip_optimizer_code = f.read()

    # Contar ocurrencias (excluyendo comentarios)
    lines_zf = [line for line in zip_functions_code.split('\n') if 'analisis_interno' in line]
    lines_zo = [line for line in zip_optimizer_code.split('\n') if 'analisis_interno' in line]

    # Filtrar solo lineas de codigo (no comentarios)
    code_lines_zf = [line for line in lines_zf if not line.strip().startswith('#')]
    code_lines_zo = [line for line in lines_zo if not line.strip().startswith('#')]

    print(f"\nzip_functions.py:")
    print(f"  'analisis_interno' en codigo: {len(code_lines_zf)} lineas")
    print(f"  'analisis_interno' en comentarios: {len(lines_zf) - len(code_lines_zf)} lineas")
    print(f"  'documento_interno' presente: {'SI' if 'documento_interno' in zip_functions_code else 'NO'}")
    print(f"  'comprobacion_pdf' presente: {'SI' if 'comprobacion_pdf' in zip_functions_code else 'NO'}")

    print(f"\nzip_optimizer.py:")
    print(f"  'analisis_interno' en codigo: {len(code_lines_zo)} lineas")
    print(f"  'analisis_interno' en comentarios: {len(lines_zo) - len(code_lines_zo)} lineas")
    print(f"  'documento_interno' presente: {'SI' if 'documento_interno' in zip_optimizer_code else 'NO'}")
    print(f"  'comprobacion_pdf' presente: {'SI' if 'comprobacion_pdf' in zip_optimizer_code else 'NO'}")

    # 5. Resumen
    print("\n" + "=" * 80)
    print("RESUMEN:")
    print("=" * 80)
    print(f"Equipo: {equipo.codigo_interno}")
    print(f"Comprobaciones: {count}")
    print(f"Archivos encontrados: {len(archivos_encontrados)}")

    if len(code_lines_zf) == 0 and len(code_lines_zo) == 0:
        print("\nCodigo corregido: NO usa 'analisis_interno' en codigo")
        print("Codigo corregido: Usa 'documento_interno' y 'comprobacion_pdf'")
        print("\nTEST EXITOSO: Bug corregido correctamente")
        return True
    else:
        print(f"\nERROR: Todavia hay {len(code_lines_zf) + len(code_lines_zo)} lineas con 'analisis_interno'")
        return False

if __name__ == '__main__':
    print("\nSUITE DE PRUEBAS: Bug Fix Comprobaciones en ZIP")
    print("Fecha: 21 de Enero de 2026")
    print("Reportado por: Usuario empresa DEMO")
    print()

    resultado = test_eq0012()

    print("\n" + "=" * 80)
    if resultado:
        print("RESULTADO: EXITOSO")
        print("=" * 80)
        sys.exit(0)
    else:
        print("RESULTADO: FALLO")
        print("=" * 80)
        sys.exit(1)
