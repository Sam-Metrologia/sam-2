"""
Script para recalcular las fechas de próximas comprobaciones y calibraciones
después de corregir los bugs de ima_comprobacion e ima_calibracion.
"""

import os
import sys
import django

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Equipo

def recalcular_fechas():
    """Recalcula las fechas de próximas actividades para todos los equipos."""
    equipos = Equipo.objects.all()
    total = equipos.count()
    actualizados = 0

    print(f"\n{'='*60}")
    print(f"RECALCULANDO FECHAS DE PROXIMAS ACTIVIDADES")
    print(f"{'='*60}\n")
    print(f"Total de equipos a procesar: {total}\n")

    for i, equipo in enumerate(equipos, 1):
        print(f"[{i}/{total}] Procesando: {equipo.nombre}")

        # Guardar valores anteriores para comparación
        old_comprobacion = equipo.proxima_comprobacion
        old_calibracion = equipo.proxima_calibracion

        # Recalcular fechas
        equipo.calcular_proxima_comprobacion()
        equipo.calcular_proxima_calibracion()

        # Guardar cambios
        equipo.save()

        # Mostrar cambios
        if old_comprobacion != equipo.proxima_comprobacion:
            print(f"  [OK] Proxima Comprobacion: {old_comprobacion} -> {equipo.proxima_comprobacion}")
            actualizados += 1

        if old_calibracion != equipo.proxima_calibracion:
            print(f"  [OK] Proxima Calibracion: {old_calibracion} -> {equipo.proxima_calibracion}")

        print()

    print(f"{'='*60}")
    print(f"RESUMEN")
    print(f"{'='*60}")
    print(f"Total procesados: {total}")
    print(f"Equipos actualizados: {actualizados}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    try:
        recalcular_fechas()
        print("[EXITO] Proceso completado exitosamente!\n")
    except Exception as e:
        print(f"[ERROR] Error durante el proceso: {e}\n")
        import traceback
        traceback.print_exc()
