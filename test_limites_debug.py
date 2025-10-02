#!/usr/bin/env python
"""
Debug de los métodos de límites para ver qué está devolviendo.
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
    estado = empresa.get_estado_suscripcion_display()
    print(f"Estado: '{estado}'")

    # Test manual de la lógica de get_limite_equipos
    print(f"\n=== Debug get_limite_equipos ===")
    print(f"acceso_manual_activo: {empresa.acceso_manual_activo}")

    if empresa.acceso_manual_activo:
        print("Resultado: float('inf') (acceso manual)")
    else:
        print(f"Evaluando estado_plan: '{estado}'")
        if estado == "Período de Prueba Activo":
            print(f"Resultado: {empresa.TRIAL_EQUIPOS} (trial)")
        elif estado in ["Plan Expirado", "Período de Prueba Expirado"]:
            print("Resultado: 0 (plan expirado - sin Expirado)")
        elif estado in ["Plan Expirado", "Período de Prueba Expirado", "Expirado"]:
            print("Resultado: 0 (plan expirado - con Expirado)")
        else:
            print(f"Resultado: {empresa.limite_equipos_empresa} (plan activo)")

    # Llamar al método real
    limite_real = empresa.get_limite_equipos()
    print(f"Limite real devuelto: {limite_real}")

    print(f"\n=== Debug get_limite_almacenamiento ===")
    limite_almacenamiento_real = empresa.get_limite_almacenamiento()
    print(f"Limite almacenamiento real: {limite_almacenamiento_real}")

else:
    print("Empresa no encontrada")