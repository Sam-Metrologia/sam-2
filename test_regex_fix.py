#!/usr/bin/env python
"""
Test para verificar que el regex de sanitize_filename está corregido.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.views.equipment import sanitize_filename

print("=== TEST REGEX CORREGIDO ===")

# Test casos que causaban el error
test_cases = [
    "archivo de prueba.pdf",
    "equipo-test.doc",
    "nombre con espacios.jpg",
    "archivo_con_simbolos!@#.txt",
    "prueba-final.docx"
]

print("Probando sanitize_filename con diferentes casos:")
for i, test_case in enumerate(test_cases, 1):
    try:
        result = sanitize_filename(test_case)
        print(f"  {i}. '{test_case}' -> '{result}' OK")
    except Exception as e:
        print(f"  {i}. '{test_case}' -> ERROR: {e}")

print("\n=== RESULTADO ===")
print("Si todos los casos muestran 'OK', el regex está corregido correctamente.")