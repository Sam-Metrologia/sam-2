#!/usr/bin/env python
"""
Script para actualizar el contrato en la base de datos con el periodo de 180 días.
Extrae el contenido del archivo terminos_condiciones_v1.0.html y lo carga en la BD.
"""

import os
import sys
import django
from datetime import date

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import TerminosYCondiciones

def extraer_contenido_html():
    """Extrae el contenido HTML del archivo terminos_condiciones_v1.0.html"""
    file_path = 'terminos_condiciones_v1.0.html'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extraer solo el contenido entre <body> y </body>
    start_marker = '<body>'
    end_marker = '</body>'

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("No se encontraron las etiquetas <body> en el archivo")

    # Obtener el contenido del body
    body_content = content[start_idx + len(start_marker):end_idx].strip()

    # Extraer solo el div con class="terminos-condiciones"
    div_start = body_content.find('<div class="terminos-condiciones">')
    div_end = body_content.rfind('</div>')

    if div_start == -1:
        print("[!] No se encontro div con class terminos-condiciones, usando todo el body")
        return body_content

    html_content = body_content[div_start:div_end + 6]  # +6 para incluir </div>

    return html_content

def actualizar_terminos():
    """Actualiza los términos en la base de datos"""

    print("=" * 70)
    print("ACTUALIZANDO TÉRMINOS Y CONDICIONES A 180 DÍAS (6 MESES)")
    print("=" * 70)

    # Extraer HTML del archivo
    print("\n[1/4] Extrayendo contenido HTML...")
    html_content = extraer_contenido_html()
    print(f"      [OK] Contenido extraido ({len(html_content)} caracteres)")

    # Buscar términos versión 1.0
    print("\n[2/4] Buscando terminos version 1.0...")
    try:
        terminos = TerminosYCondiciones.objects.get(version='1.0')
        print(f"      [OK] Encontrados: {terminos.titulo}")
    except TerminosYCondiciones.DoesNotExist:
        print("      [!] No existen terminos v1.0, creando nuevo registro...")
        terminos = TerminosYCondiciones()
        terminos.version = '1.0'
        terminos.fecha_vigencia = date(2025, 10, 1)
        terminos.titulo = 'Contrato de Licencia de Uso y Provision de Servicios SaaS - Plataforma SAM'
        terminos.activo = True

    # Actualizar contenido
    print("\n[3/4] Actualizando contenido HTML...")
    terminos.contenido_html = html_content
    terminos.save()
    print("      [OK] Contenido actualizado en base de datos")

    # Verificar
    print("\n[4/4] Verificando actualizacion...")
    if '180 dias (6 meses)' in terminos.contenido_html or '180 días (6 meses)' in terminos.contenido_html:
        print("      [OK] Contrato actualizado correctamente con periodo de 180 dias")
    else:
        print("      [!] Advertencia: No se encontro '180 dias (6 meses)' en el contenido")

    print("\n" + "=" * 70)
    print("[OK] ACTUALIZACION COMPLETADA")
    print("=" * 70)
    print(f"\nVersion: {terminos.version}")
    print(f"Fecha vigencia: {terminos.fecha_vigencia}")
    print(f"Estado: {'Activo' if terminos.activo else 'Inactivo'}")
    print(f"Longitud HTML: {len(terminos.contenido_html)} caracteres")
    print("\n" + "=" * 70)
    print("[i] Los usuarios veran el contrato actualizado en:")
    print("    https://app.sammetrologia.com/core/mi-aceptacion-terminos/")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    try:
        actualizar_terminos()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
