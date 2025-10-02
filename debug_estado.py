#!/usr/bin/env python
"""
Debug del estado de suscripción para verificar valores exactos.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Empresa

# Obtener empresa de prueba
empresa = Empresa.objects.filter(nombre="Test Final Expirada").first()
if empresa:
    print(f"Empresa: {empresa.nombre}")
    print(f"estado_suscripcion (campo): '{empresa.estado_suscripcion}'")
    print(f"get_estado_suscripcion_display(): '{empresa.get_estado_suscripcion_display()}'")
    print(f"es_periodo_prueba: {empresa.es_periodo_prueba}")
    print(f"fecha_inicio_plan: {empresa.fecha_inicio_plan}")
    print(f"duracion_suscripcion_meses: {empresa.duracion_suscripcion_meses}")

    # Verificar las condiciones exactas
    estado = empresa.get_estado_suscripcion_display()
    print(f"\nComparaciones:")
    print(f"estado == 'Expirado': {estado == 'Expirado'}")
    print(f"estado == 'Plan Expirado': {estado == 'Plan Expirado'}")
    print(f"estado in ['Plan Expirado', 'Período de Prueba Expirado']: {estado in ['Plan Expirado', 'Período de Prueba Expirado']}")
    print(f"estado in ['Plan Expirado', 'Período de Prueba Expirado', 'Expirado']: {estado in ['Plan Expirado', 'Período de Prueba Expirado', 'Expirado']}")
else:
    print("Empresa no encontrada")