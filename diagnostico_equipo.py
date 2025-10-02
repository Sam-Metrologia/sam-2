#!/usr/bin/env python
"""
Diagnóstico de fechas de actividades para un equipo específico
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import Equipo
from datetime import date

# Equipo a diagnosticar
CODIGO_EQUIPO = 'MT-CD-003'

try:
    equipo = Equipo.objects.get(codigo_interno=CODIGO_EQUIPO)
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO EQUIPO: {equipo.codigo_interno} - {equipo.nombre}")
    print(f"{'='*80}\n")

    print(f"Estado: {equipo.estado}")
    print(f"Fecha Registro: {equipo.fecha_registro}")
    print(f"Fecha Adquisición: {equipo.fecha_adquisicion}")

    print(f"\n{'='*80}")
    print("CALIBRACIONES")
    print(f"{'='*80}")
    print(f"Frecuencia: {equipo.frecuencia_calibracion_meses} meses")
    print(f"Fecha Última Calibración (campo): {equipo.fecha_ultima_calibracion}")
    print(f"Próxima Calibración (campo DB): {equipo.proxima_calibracion}")

    # Obtener última calibración del historial
    ultima_cal = equipo.calibraciones.order_by('-fecha_calibracion').first()
    if ultima_cal:
        print(f"\nÚltima calibración en historial:")
        print(f"  - Fecha: {ultima_cal.fecha_calibracion}")
        print(f"  - ID: {ultima_cal.id}")

        # Calcular manualmente
        if equipo.frecuencia_calibracion_meses:
            from dateutil.relativedelta import relativedelta
            proxima_calculada = ultima_cal.fecha_calibracion + relativedelta(months=int(equipo.frecuencia_calibracion_meses))
            print(f"  - Próxima (calculada manualmente): {proxima_calculada}")
            print(f"  - ¿Coincide con DB?: {'SÍ' if proxima_calculada == equipo.proxima_calibracion else 'NO ❌'}")
    else:
        print("\nNo hay calibraciones en el historial")

    print(f"\n{'='*80}")
    print("MANTENIMIENTOS")
    print(f"{'='*80}")
    print(f"Frecuencia: {equipo.frecuencia_mantenimiento_meses} meses")
    print(f"Fecha Último Mantenimiento (campo): {equipo.fecha_ultimo_mantenimiento}")
    print(f"Próximo Mantenimiento (campo DB): {equipo.proximo_mantenimiento}")

    # Obtener último mantenimiento del historial
    ultimo_mant = equipo.mantenimientos.order_by('-fecha_mantenimiento').first()
    if ultimo_mant:
        print(f"\nÚltimo mantenimiento en historial:")
        print(f"  - Fecha: {ultimo_mant.fecha_mantenimiento}")
        print(f"  - ID: {ultimo_mant.id}")

        # Calcular manualmente
        if equipo.frecuencia_mantenimiento_meses:
            from dateutil.relativedelta import relativedelta
            proximo_calculado = ultimo_mant.fecha_mantenimiento + relativedelta(months=int(equipo.frecuencia_mantenimiento_meses))
            print(f"  - Próximo (calculado manualmente): {proximo_calculado}")
            print(f"  - ¿Coincide con DB?: {'SÍ' if proximo_calculado == equipo.proximo_mantenimiento else 'NO ❌'}")
    else:
        print("\nNo hay mantenimientos en el historial")

    print(f"\n{'='*80}")
    print("COMPROBACIONES")
    print(f"{'='*80}")
    print(f"Frecuencia: {equipo.frecuencia_comprobacion_meses} meses")
    print(f"Fecha Última Comprobación (campo): {equipo.fecha_ultima_comprobacion}")
    print(f"Próxima Comprobación (campo DB): {equipo.proxima_comprobacion}")

    # Obtener última comprobación del historial
    ultima_comp = equipo.comprobaciones.order_by('-fecha_comprobacion').first()
    if ultima_comp:
        print(f"\nÚltima comprobación en historial:")
        print(f"  - Fecha: {ultima_comp.fecha_comprobacion}")
        print(f"  - ID: {ultima_comp.id}")

        # Calcular manualmente
        if equipo.frecuencia_comprobacion_meses:
            from dateutil.relativedelta import relativedelta
            proxima_calculada = ultima_comp.fecha_comprobacion + relativedelta(months=int(equipo.frecuencia_comprobacion_meses))
            print(f"  - Próxima (calculada manualmente): {proxima_calculada}")
            print(f"  - ¿Coincide con DB?: {'SÍ' if proxima_calculada == equipo.proxima_comprobacion else 'NO ❌'}")
    else:
        print("\nNo hay comprobaciones en el historial")

    print(f"\n{'='*80}")
    print("RECALCULAR FECHAS")
    print(f"{'='*80}")
    respuesta = input("\n¿Deseas recalcular las fechas próximas para corregir inconsistencias? (s/n): ")
    if respuesta.lower() == 's':
        equipo.calcular_proxima_calibracion()
        equipo.calcular_proximo_mantenimiento()
        equipo.calcular_proxima_comprobacion()
        equipo.save(update_fields=['proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])
        print("\n✅ Fechas recalculadas y guardadas")
        print(f"Próxima Calibración: {equipo.proxima_calibracion}")
        print(f"Próximo Mantenimiento: {equipo.proximo_mantenimiento}")
        print(f"Próxima Comprobación: {equipo.proxima_comprobacion}")
    else:
        print("\nNo se realizaron cambios")

except Equipo.DoesNotExist:
    print(f"\n❌ ERROR: No se encontró el equipo con código '{CODIGO_EQUIPO}'")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
