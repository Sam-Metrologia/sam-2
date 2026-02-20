# -*- coding: utf-8 -*-
import os
import sys
import django

# Force UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Equipo
from django.core.files.storage import default_storage

# Buscar equipos EQ-001
try:
    equipos = Equipo.objects.filter(codigo_interno='EQ-001')
    print(f"[INFO] Encontrados {equipos.count()} equipos con codigo EQ-001\n")

    for equipo in equipos:
        print("="*60)
        print(f"EQUIPO ID {equipo.id}")
        print(f"Codigo: {equipo.codigo_interno} - {equipo.nombre}")
        print(f"Empresa: {equipo.empresa.nombre if equipo.empresa else 'N/A'}")
        print(f"Estado: {equipo.estado}")
        print()

        # Revisar MANTENIMIENTOS
        mantenimientos = equipo.mantenimientos.all()
        print(f"MANTENIMIENTOS: {mantenimientos.count()} registros")

        docs_mant = 0
        for idx, mant in enumerate(mantenimientos, 1):
            print(f"\n   Mantenimiento #{idx}:")
            print(f"   - Fecha: {mant.fecha_mantenimiento}")
            print(f"   - Tipo: {mant.get_tipo_mantenimiento_display()}")

            # Documento Externo
            if mant.documento_externo:
                file_path = mant.documento_externo.name
                exists = default_storage.exists(file_path)
                print(f"   - documento_externo: {file_path}")
                print(f"     EXISTS: {exists}")
                if exists:
                    docs_mant += 1
            else:
                print(f"   - documento_externo: NULL")

            # Análisis Interno
            if mant.analisis_interno:
                file_path = mant.analisis_interno.name
                exists = default_storage.exists(file_path)
                print(f"   - analisis_interno: {file_path}")
                print(f"     EXISTS: {exists}")
                if exists:
                    docs_mant += 1
            else:
                print(f"   - analisis_interno: NULL")

            # Documento General
            if mant.documento_mantenimiento:
                file_path = mant.documento_mantenimiento.name
                exists = default_storage.exists(file_path)
                print(f"   - documento_mantenimiento: {file_path}")
                print(f"     EXISTS: {exists}")
                if exists:
                    docs_mant += 1
            else:
                print(f"   - documento_mantenimiento: NULL")

        print("\n" + "-"*60)

        # Revisar COMPROBACIONES
        comprobaciones = equipo.comprobaciones.all()
        print(f"\nCOMPROBACIONES: {comprobaciones.count()} registros")

        docs_comp = 0
        for idx, comp in enumerate(comprobaciones, 1):
            print(f"\n   Comprobacion #{idx}:")
            print(f"   - Fecha: {comp.fecha_comprobacion}")
            print(f"   - Resultado: {comp.resultado}")

            # Documento Externo
            if comp.documento_externo:
                file_path = comp.documento_externo.name
                exists = default_storage.exists(file_path)
                print(f"   - documento_externo: {file_path}")
                print(f"     EXISTS: {exists}")
                if exists:
                    docs_comp += 1
            else:
                print(f"   - documento_externo: NULL")

            # Análisis Interno
            if comp.analisis_interno:
                file_path = comp.analisis_interno.name
                exists = default_storage.exists(file_path)
                print(f"   - analisis_interno: {file_path}")
                print(f"     EXISTS: {exists}")
                if exists:
                    docs_comp += 1
            else:
                print(f"   - analisis_interno: NULL")

            # Documento General
            if comp.documento_comprobacion:
                file_path = comp.documento_comprobacion.name
                exists = default_storage.exists(file_path)
                print(f"   - documento_comprobacion: {file_path}")
                print(f"     EXISTS: {exists}")
                if exists:
                    docs_comp += 1
            else:
                print(f"   - documento_comprobacion: NULL")

        print("\n" + "-"*60)
        print(f"\nRESUMEN EQUIPO ID {equipo.id}:")
        print(f"   - Documentos de mantenimientos existentes: {docs_mant}")
        print(f"   - Documentos de comprobaciones existentes: {docs_comp}")
        print(f"   - TOTAL: {docs_mant + docs_comp} documentos que deberian estar en ZIP")
        print("="*60 + "\n")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
