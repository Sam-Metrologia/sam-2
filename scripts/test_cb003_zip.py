#!/usr/bin/env python
"""
Script de prueba para diagnosticar por qué CB-003 no incluye comprobaciones en ZIP
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

from core.models import Equipo, Comprobacion, Mantenimiento
from django.core.files.storage import default_storage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cb003():
    print("=" * 80)
    print("TEST: Diagnostico CB-003 - Por que comprobaciones no se incluyen en ZIP")
    print("=" * 80)

    # 1. Obtener equipo
    equipo = Equipo.objects.filter(codigo_interno='CB-003').first()
    if not equipo:
        print("ERROR: Equipo CB-003 no encontrado")
        return

    print(f"\nEquipo: {equipo.nombre} ({equipo.codigo_interno})")
    print(f"Empresa: {equipo.empresa.nombre}")

    # 2. Verificar comprobaciones
    comprobaciones = equipo.comprobaciones.all()
    print(f"\nComprobaciones totales: {comprobaciones.count()}")

    for comp in comprobaciones:
        print(f"\n--- Comprobacion ID {comp.id} ---")
        print(f"Fecha: {comp.fecha_comprobacion}")
        print(f"comprobacion_pdf: {comp.comprobacion_pdf.name if comp.comprobacion_pdf else 'None'}")

        if comp.comprobacion_pdf:
            exists = default_storage.exists(comp.comprobacion_pdf.name)
            print(f"Archivo existe en storage: {exists}")

            if exists:
                try:
                    # Intentar abrir como hace el codigo de ZIP
                    with default_storage.open(comp.comprobacion_pdf.name, 'rb') as f:
                        content = f.read()
                        print(f"Archivo leido exitosamente: {len(content)} bytes")

                        # Simular inclusion en ZIP
                        zip_buffer = BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                            empresa_nombre = equipo.empresa.nombre
                            equipo_folder = f"{empresa_nombre}/Equipos/{equipo.codigo_interno}"
                            filename = f"comp_1.pdf"
                            zip_path = f"{equipo_folder}/Comprobaciones/Certificados_Comprobacion/{filename}"

                            print(f"Intentando escribir en ZIP: {zip_path}")
                            zf.writestr(zip_path, content)
                            print(f"Escrito en ZIP exitosamente")

                        # Verificar contenido del ZIP
                        zip_buffer.seek(0)
                        with zipfile.ZipFile(zip_buffer, 'r') as zf:
                            files_in_zip = zf.namelist()
                            print(f"\nArchivos en ZIP de prueba:")
                            for file in files_in_zip:
                                print(f"  - {file}")

                        print("\nCONCLUSION: El archivo PUEDE ser incluido en ZIP sin problemas")

                except Exception as e:
                    print(f"ERROR al procesar archivo: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("ERROR: Archivo NO existe en storage pero campo tiene valor")
        else:
            print("Sin archivo comprobacion_pdf")

    # 3. Verificar mantenimientos para comparar
    mantenimientos = equipo.mantenimientos.all()
    print(f"\n\n--- MANTENIMIENTOS (para comparar) ---")
    print(f"Mantenimientos totales: {mantenimientos.count()}")

    for mant in mantenimientos:
        print(f"\nMantenimiento ID {mant.id}")
        print(f"Fecha: {mant.fecha_mantenimiento}")
        print(f"documento_mantenimiento: {mant.documento_mantenimiento.name if mant.documento_mantenimiento else 'None'}")

        if mant.documento_mantenimiento:
            exists = default_storage.exists(mant.documento_mantenimiento.name)
            print(f"Archivo existe: {exists}")

    # 4. Verificar si hay diferencias en el codigo de procesamiento
    print("\n" + "=" * 80)
    print("ANALISIS DEL CODIGO:")
    print("=" * 80)

    with open('core/zip_functions.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar lineas relevantes
    import re

    # Buscar procesamiento de mantenimientos
    mant_match = re.search(r'# Mantenimientos.*?# Comprobaciones', content, re.DOTALL)
    if mant_match:
        mant_code = mant_match.group(0)
        print("\nCodigo de Mantenimientos:")
        print("  - Procesa documento_mantenimiento: {}".format("SI" if "documento_mantenimiento" in mant_code else "NO"))
        print("  - Usa default_storage.exists: {}".format("SI" if "default_storage.exists" in mant_code else "NO"))
        print("  - Usa writestr: {}".format("SI" if "writestr" in mant_code else "NO"))

    # Buscar procesamiento de comprobaciones
    comp_match = re.search(r'# Comprobaciones.*?# Documentos del equipo', content, re.DOTALL)
    if comp_match:
        comp_code = comp_match.group(0)
        print("\nCodigo de Comprobaciones:")
        print("  - Procesa comprobacion_pdf: {}".format("SI" if "comprobacion_pdf" in comp_code else "NO"))
        print("  - Usa default_storage.exists: {}".format("SI" if "default_storage.exists" in comp_code else "NO"))
        print("  - Usa writestr: {}".format("SI" if "writestr" in comp_code else "NO"))

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)

    if comprobaciones.exists():
        comp = comprobaciones.first()
        if comp.comprobacion_pdf and default_storage.exists(comp.comprobacion_pdf.name):
            print("El archivo de comprobacion EXISTE y PUEDE ser incluido en ZIP")
            print("\nPosibles causas de que no aparezca:")
            print("  1. Servidor Django no se reinicio correctamente")
            print("  2. Codigo de ZIP usa version en memoria sin cambios")
            print("  3. Estas descargando un ZIP generado ANTES del fix")
            print("  4. Hay un error silencioso que se captura en except")
            print("\nSUGERENCIA:")
            print("  1. Detener COMPLETAMENTE el servidor Django")
            print("  2. Verificar que NO hay procesos de Django corriendo")
            print("  3. Iniciar servidor de nuevo")
            print("  4. Generar ZIP NUEVO y verificar")
        else:
            print("ERROR: Archivo de comprobacion NO existe en storage")
    else:
        print("Sin comprobaciones para verificar")

if __name__ == '__main__':
    test_cb003()
